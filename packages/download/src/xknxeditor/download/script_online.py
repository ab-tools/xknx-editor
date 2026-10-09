"""The ``online`` object passed to online Button handlers."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
from typing import TYPE_CHECKING, Any, cast

from xknxeditor.prod.script.errors import (
    COR_E_INVALIDOPERATION,
    E_NOTIMPL,
    E_POINTER,
    AbortRequested,
    HostError,
)
from xknxeditor.prod.script.texts import COAP_NOT_SUPPORTED, NOT_CONNECTED, dotnet_text

from .programmer import (
    DEFAULT_MAX_APDU_LENGTH,
    MAX_COMMUNICATION_APDU_LENGTH,
    DeviceProgrammer,
)
from .session import apdu_overhead, management_session

if TYPE_CHECKING:
    from xknx import XKNX
    from xknx.telegram import IndividualAddress

    from xknxeditor.prod.script.sandbox import AbortToken, HostFunction

    from .data_secure import DeviceSecurity
    from .programmer import ConnectionManager

# APDU length reported before connect(): the length every KNX device supports.
INTERFACE_MAX_APDU_LENGTH = DEFAULT_MAX_APDU_LENGTH
DEVICE_MISMATCH = "The device does not match: mask version {0:04X} instead of {1:04X}."


class OnlineSession:
    """Management session of one handler run; ``connect()`` will open the transport
    (with Data Secure sync for a Tool Key), identify the device and negotiate the APDU length
    as the minimum of the device's, the interface's and the communication limit."""

    def __init__(
        self,
        xknx: XKNX,
        address: IndividualAddress,
        *,
        security: DeviceSecurity | None = None,
        connectionless: bool = False,
        mask_version: int | None = None,
        interface_max_apdu_length: int | None = None,
        locale: str | None = None,
    ) -> None:
        self._xknx = xknx
        self._address = address
        self._security = security
        self._connectionless = connectionless
        self._mask_version = mask_version
        self._interface_max = interface_max_apdu_length
        self._locale = locale
        self._descriptor: int | None = None
        self._manager: ConnectionManager | None = None
        self._programmer: DeviceProgrammer | None = None

    @property
    def connected(self) -> bool:
        return self._programmer is not None

    @property
    def programmer(self) -> DeviceProgrammer:
        if self._programmer is None:
            raise HostError(NOT_CONNECTED, number=COR_E_INVALIDOPERATION)
        return self._programmer

    def device_descriptor(self) -> int:
        """The device descriptor read by ``connect()``."""
        if self._descriptor is None:
            raise HostError(
                dotnet_text("null_reference", self._locale), number=E_POINTER
            )
        return self._descriptor

    async def connect(self) -> None:
        if self._programmer is not None:
            return
        manager = management_session(
            self._xknx,
            self._address,
            self._security,
            connectionless=self._connectionless,
        )
        self._manager = manager
        try:
            connection = await manager.open()
            programmer = DeviceProgrammer(
                connection, apdu_overhead=apdu_overhead(self._security)
            )
            descriptor = await programmer.read_device_descriptor()
            if self._mask_version is not None and descriptor != self._mask_version:
                raise HostError(DEVICE_MISMATCH.format(descriptor, self._mask_version))
            limit = MAX_COMMUNICATION_APDU_LENGTH
            if self._interface_max is not None:
                limit = min(limit, self._interface_max)
            device_max = await programmer.read_max_apdu_length()
            programmer.max_apdu_length = max(
                DEFAULT_MAX_APDU_LENGTH, min(device_max, limit)
            )
        except BaseException:
            await self.disconnect()
            raise
        self._programmer = programmer
        self._descriptor = descriptor

    async def disconnect(self) -> None:
        manager, self._manager, self._programmer = self._manager, None, None
        self._descriptor = None
        if manager is not None:
            await manager.close()

    def max_apdu_length(self) -> int:
        if self._programmer is not None:
            return self._programmer.max_apdu_length
        if self._interface_max is not None:
            return self._interface_max
        return INTERFACE_MAX_APDU_LENGTH

    async def restart(self) -> None:
        await self.programmer.restart()
        await self.disconnect()


def _bytes(data: Any) -> bytes:
    if isinstance(data, str):
        return data.encode("latin-1")
    values = cast("list[Any]", data or [])
    return bytes(int(v) & 0xFF for v in values)


class OnlineHost:
    """Host functions of the ``online`` object. ``run`` schedules a coroutine on the xknx event
    loop; calls block the script until it completes and stay abortable."""

    def __init__(
        self,
        session: OnlineSession,
        run: Callable[[Coroutine[Any, Any, Any]], Future[Any]],
        abort: AbortToken,
    ) -> None:
        self._session = session
        self._run = run
        self._abort = abort

    def _wait[T](self, coro: Coroutine[Any, Any, T]) -> T:
        future: Future[T] = self._run(coro)
        while True:
            try:
                return future.result(timeout=0.1)
            except FutureTimeout:
                if self._abort.requested:
                    future.cancel()
                    raise AbortRequested() from None

    def connect(self) -> None:
        self._wait(self._session.connect())

    def disconnect(self) -> None:
        self._wait(self._session.disconnect())

    def read_device_descriptor0(self) -> int:
        return self._session.device_descriptor()

    def get_max_apdu_length(self) -> int:
        return self._session.max_apdu_length()

    def locate_interface_object(self, object_type: Any, occurrence: Any = 0) -> int:
        programmer = self._session.programmer
        return self._wait(
            programmer.locate_object(int(object_type), int(occurrence or 0))
        )

    def read_function_property(self, obj: Any, pid: Any) -> list[int]:
        programmer = self._session.programmer
        return list(
            self._wait(programmer.function_property_raw(int(obj), int(pid), None))
        )

    def invoke_function_property(self, obj: Any, pid: Any, data: Any) -> list[int]:
        programmer = self._session.programmer
        return list(
            self._wait(
                programmer.function_property_raw(int(obj), int(pid), _bytes(data))
            )
        )

    def read_property(
        self, obj: Any, pid: Any, _type: Any = None, start: Any = 1, count: Any = 1
    ) -> list[int]:
        programmer = self._session.programmer
        return list(
            self._wait(
                programmer.read_property(
                    int(obj), int(pid), count=int(count), start_index=int(start)
                )
            )
        )

    def write_property(
        self,
        obj: Any,
        pid: Any,
        _type: Any = None,
        start: Any = 1,
        count: Any = 1,
        data: Any = None,
        verify: Any = False,
    ) -> list[int]:
        programmer = self._session.programmer
        return list(
            self._wait(
                programmer.write_property(
                    int(obj),
                    int(pid),
                    _bytes(data),
                    count=int(count),
                    start_index=int(start),
                    verify=bool(verify),
                )
            )
        )

    def read_memory(self, address: Any, size: Any) -> list[int]:
        programmer = self._session.programmer
        return list(self._wait(programmer.read_memory(int(address), int(size))))

    def write_memory(self, address: Any, data: Any, verify: Any = False) -> None:
        programmer = self._session.programmer
        self._wait(
            programmer.write_memory(int(address), _bytes(data), verify=bool(verify))
        )

    def read_user_memory(self, address: Any, size: Any) -> list[int]:
        programmer = self._session.programmer
        return list(self._wait(programmer.read_user_memory(int(address), int(size))))

    def write_user_memory(self, address: Any, data: Any, verify: Any = False) -> None:
        programmer = self._session.programmer
        self._wait(
            programmer.write_user_memory(
                int(address), _bytes(data), verify=bool(verify)
            )
        )

    def restart(self) -> None:
        self._wait(self._session.restart())

    def coap(self, *_args: Any) -> None:
        raise HostError(COAP_NOT_SUPPORTED, number=E_NOTIMPL)

    def functions(self) -> dict[str, HostFunction]:
        return {
            "o.connect": self.connect,
            "o.disconnect": self.disconnect,
            "o.readDeviceDescriptor0": self.read_device_descriptor0,
            "o.getMaxApduLength": self.get_max_apdu_length,
            "o.locateInterfaceObject": self.locate_interface_object,
            "o.readFunctionProperty": self.read_function_property,
            "o.invokeFunctionProperty": self.invoke_function_property,
            "o.readProperty": self.read_property,
            "o.writeProperty": self.write_property,
            "o.readMemory": self.read_memory,
            "o.writeMemory": self.write_memory,
            "o.readUserMemory": self.read_user_memory,
            "o.writeUserMemory": self.write_user_memory,
            "o.restart": self.restart,
            "o.coapReadCollection": self.coap,
            "o.coapGet": self.coap,
            "o.coapPut": self.coap,
            "o.coapPost": self.coap,
        }
