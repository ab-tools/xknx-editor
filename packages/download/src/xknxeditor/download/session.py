"""Management sessions to one device: connection-oriented or connectionless, plain or secured."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from xknx.exceptions import ManagementConnectionError

if TYPE_CHECKING:
    from xknx import XKNX
    from xknx.telegram.address import IndividualAddress

    from .data_secure import DeviceSecurity
    from .programmer import BusConnection, ConnectionManager


class XknxConnectionManager:
    """Open/close point-to-point connections to one device via ``xknx``."""

    def __init__(self, xknx: XKNX, address: IndividualAddress) -> None:
        """Initialize for a target individual address."""
        self._xknx = xknx
        self._address = address
        self._connection: BusConnection | None = None

    async def open(self) -> BusConnection:
        """Open a fresh connection to the device."""
        self._connection = await self._xknx.management.connect(self._address)
        return self._connection

    async def close(self) -> None:
        """Close the current connection, tolerating a peer that already dropped it."""
        if self._connection is None:
            return
        self._connection = None
        with contextlib.suppress(ManagementConnectionError):
            await self._xknx.management.disconnect(self._address)


def management_session(
    xknx: XKNX,
    address: IndividualAddress,
    security: DeviceSecurity | None,
    *,
    connectionless: bool = False,
) -> ConnectionManager:
    """A connection manager for ``address``, secured with the Tool Key when ``security`` is set."""
    from .connectionless import ConnectionlessManager

    transport: ConnectionManager | None = (
        ConnectionlessManager(xknx, address) if connectionless else None
    )
    if security is None:
        return transport or XknxConnectionManager(xknx, address)
    from .data_secure import SecureProgrammingError
    from .secure_session import SecureConnectionManager

    if security.address != address:
        raise SecureProgrammingError(
            f"security material is for {security.address}, not the download "
            f"target {address}"
        )
    return SecureConnectionManager(xknx, address, security, transport=transport)


def apdu_overhead(security: DeviceSecurity | None) -> int:
    """Wire APDU overhead a secure session adds around each plaintext APDU."""
    if security is None:
        return 0
    from .data_secure import SECURE_APDU_OVERHEAD

    return SECURE_APDU_OVERHEAD
