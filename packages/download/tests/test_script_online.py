"""Connectionless channel and the ``online`` object of button scripts."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine, Iterator
from concurrent.futures import Future
from typing import Any

import pytest
from xknx.telegram import IndividualAddress, Telegram
from xknx.telegram.apci import (
    APCI,
    DeviceDescriptorRead,
    DeviceDescriptorResponse,
    PropertyValueRead,
)
from xknx.telegram.tpci import TConnect, TDataIndividual

from xknxeditor.download import script_online
from xknxeditor.download.connectionless import ConnectionlessManager
from xknxeditor.download.script_online import OnlineHost, OnlineSession
from xknxeditor.prod.script import AbortToken
from xknxeditor.prod.script.errors import AbortRequested, HostError

from .conftest import FakeDevice

DEVICE = IndividualAddress("1.1.5")


class _Management:
    def __init__(self) -> None:
        self.unhandled: list[Telegram] = []

    def process(self, telegram: Telegram) -> None:
        self.unhandled.append(telegram)


class _CemiHandler:
    def __init__(self, xknx: _Xknx) -> None:
        self._xknx = xknx
        self.sent: list[Telegram] = []

    async def send_telegram(self, telegram: Telegram) -> None:
        self.sent.append(telegram)
        if isinstance(telegram.payload, DeviceDescriptorRead):
            reply = Telegram(
                destination_address=IndividualAddress("0.0.1"),
                source_address=DEVICE,
                tpci=TDataIndividual(),
                payload=DeviceDescriptorResponse(descriptor=0, value=0x07B0),
            )
            asyncio.get_running_loop().call_soon(self._xknx.management.process, reply)


class _Xknx:
    def __init__(self) -> None:
        self.management = _Management()
        self.cemi_handler = _CemiHandler(self)


def test_connectionless_request_uses_individual_data() -> None:
    xknx = _Xknx()

    async def run() -> int:
        manager = ConnectionlessManager(xknx, DEVICE)  # type: ignore[arg-type]
        connection = await manager.open()
        telegram = await connection.request(
            DeviceDescriptorRead(descriptor=0), DeviceDescriptorResponse
        )
        await manager.close()
        assert isinstance(telegram.payload, DeviceDescriptorResponse)
        return telegram.payload.value

    assert asyncio.run(run()) == 0x07B0
    assert all(isinstance(t.tpci, TDataIndividual) for t in xknx.cemi_handler.sent)
    assert not any(isinstance(t.tpci, TConnect) for t in xknx.cemi_handler.sent)
    assert "process" not in vars(xknx.management)
    other = Telegram(destination_address=DEVICE, payload=DeviceDescriptorRead())
    xknx.management.process(other)
    assert xknx.management.unhandled == [other]


class _Manager:
    def __init__(self, device: FakeDevice) -> None:
        self.device = device
        self.opened = 0
        self.closed = 0

    async def open(self) -> FakeDevice:
        self.opened += 1
        return self.device

    async def close(self) -> None:
        self.closed += 1


@pytest.fixture
def loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join()
    loop.close()


def _host(
    loop: asyncio.AbstractEventLoop,
    monkeypatch: pytest.MonkeyPatch,
    device: FakeDevice,
    abort: AbortToken | None = None,
    mask: int = 0x07B0,
) -> tuple[OnlineHost, _Manager]:
    manager = _Manager(device)
    monkeypatch.setattr(script_online, "management_session", lambda *a, **k: manager)
    session = OnlineSession(None, DEVICE, mask_version=mask)  # type: ignore[arg-type]

    def run(coro: Coroutine[Any, Any, Any]) -> Future[Any]:
        return asyncio.run_coroutine_threadsafe(coro, loop)

    return OnlineHost(session, run, abort or AbortToken()), manager


def test_calls_need_connect(
    loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, _ = _host(loop, monkeypatch, FakeDevice(descriptor=0x07B0))
    with pytest.raises(HostError):
        host.invoke_function_property(160, 3, [1])
    assert host.get_max_apdu_length() == 15


def test_function_property_keeps_status_byte(
    loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = FakeDevice(descriptor=0x07B0)
    device.function_property_return_code = 2
    host, manager = _host(loop, monkeypatch, device)
    host.connect()
    assert host.invoke_function_property(160, 3, [7, 8]) == [2, 7, 8]
    assert host.read_device_descriptor0() == 0x07B0
    host.disconnect()
    assert (manager.opened, manager.closed) == (1, 1)


def test_connect_identifies_the_device(
    loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, manager = _host(loop, monkeypatch, FakeDevice(descriptor=0x0705))
    with pytest.raises(HostError, match="mask version"):
        host.connect()
    assert manager.closed == 1


def test_coap_is_not_implemented(
    loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    host, _ = _host(loop, monkeypatch, FakeDevice(descriptor=0x07B0))
    with pytest.raises(HostError) as err:
        host.coap("x")
    assert err.value.number == -2147467263


class _SlowDevice(FakeDevice):
    async def request(self, payload: APCI, expected: type[APCI] | None) -> Telegram:
        if isinstance(payload, PropertyValueRead) and self.slow:
            await asyncio.sleep(60)
        return await super().request(payload, expected)


def test_abort_interrupts_a_waiting_call(
    loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = _SlowDevice(descriptor=0x07B0)
    device.slow = False
    abort = AbortToken()
    host, _ = _host(loop, monkeypatch, device, abort)
    host.connect()
    device.slow = True
    threading.Timer(0.2, abort.request).start()
    with pytest.raises(AbortRequested):
        host.read_property(0, 56, 0, 1, 1)


def test_connect_negotiates_apdu_without_authorize(
    loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = FakeDevice(descriptor=0x07B0)
    device.properties[(0, 56)] = (254).to_bytes(2, "big")
    host, _ = _host(loop, monkeypatch, device)
    host.connect()
    assert host.get_max_apdu_length() == 239
    assert device.authorize_keys == []


def test_interface_limit_applies(
    loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = FakeDevice(descriptor=0x07B0)
    device.properties[(0, 56)] = (254).to_bytes(2, "big")
    manager = _Manager(device)
    monkeypatch.setattr(script_online, "management_session", lambda *a, **k: manager)
    session = OnlineSession(
        None,  # type: ignore[arg-type]
        DEVICE,
        mask_version=0x07B0,
        interface_max_apdu_length=200,
    )
    host = OnlineHost(
        session, lambda c: asyncio.run_coroutine_threadsafe(c, loop), AbortToken()
    )
    assert host.get_max_apdu_length() == 200
    host.connect()
    assert host.get_max_apdu_length() == 200


def test_connect_is_idempotent_and_caches_the_descriptor(
    loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = FakeDevice(descriptor=0x07B0)
    host, manager = _host(loop, monkeypatch, device)
    with pytest.raises(HostError) as err:
        host.read_device_descriptor0()
    assert err.value.number == -2147467261
    with pytest.raises(HostError) as err:
        host.read_property(0, 56, 0, 1, 1)
    assert (err.value.message, err.value.number) == ("Not connected", -2146233079)
    host.connect()
    sent = len(device.sent)
    host.connect()
    assert manager.opened == 1
    assert host.read_device_descriptor0() == 0x07B0
    assert len(device.sent) == sent
    host.disconnect()
    with pytest.raises(HostError):
        host.read_device_descriptor0()


def test_locate_uses_declared_objects_then_scans(
    loop: asyncio.AbstractEventLoop, monkeypatch: pytest.MonkeyPatch
) -> None:
    device = FakeDevice(object_types={0: 0, 1: 1, 6: 4}, descriptor=0x07B0)
    manager = _Manager(device)
    monkeypatch.setattr(script_online, "management_session", lambda *a, **k: manager)
    session = OnlineSession(
        None,  # type: ignore[arg-type]
        DEVICE,
        object_types={0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 6},
        locale="de-DE",
    )
    host = OnlineHost(
        session, lambda c: asyncio.run_coroutine_threadsafe(c, loop), AbortToken()
    )
    host.connect()
    sent = len(device.sent)
    assert host.locate_interface_object(4, 1) == 4
    assert len(device.sent) == sent
    assert host.locate_interface_object(4, 2) == 6
    with pytest.raises(HostError) as err:
        host.locate_interface_object(0, 0)
    assert (
        err.value.message
        == "Die ausgewählte Geräte-Ressource ist zurzeit nicht verfügbar."
    )
    with pytest.raises(HostError) as err:
        host.read_property(99, 1, 0, 1, 1)
    assert err.value.message.endswith(
        "Lesen von Property(99/1, 1, 1) fehlgeschlagen: Empty response"
    )
    with pytest.raises(HostError) as err:
        host.read_function_property(255, 255, 0)
    assert err.value.number == -2147467262
    assert "System.Int32" in err.value.message
