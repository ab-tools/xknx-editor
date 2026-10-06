"""Exceptions raised while downloading data into a KNX device."""

from __future__ import annotations


class DownloadError(Exception):
    """Base class for all download errors."""


class LoadStateError(DownloadError):
    """A Load State Machine did not reach the expected state."""


class VerificationError(DownloadError):
    """Data read back from the device does not match the data written."""


# Error a rejected write to a protected or non-existing resource is reported as
# (ETS HAWK_E_RESOURCE_WRITE_PROTECTED). A device answers such a write with a
# 0-element response; a Load Procedure can map this error to success with an
# LdCtrlMapError bracket. See .references/ets_map.md for provenance.
RESOURCE_WRITE_PROTECTED_ERROR = 3221498632


class PropertyAccessRejected(VerificationError):
    """A property write was rejected by the device (0 elements written).

    A device answers a property write to a protected or non-existing resource
    (e.g. an absent interface object) with a 0-element response. A Load Procedure
    can bracket such an access with ``LdCtrlMapError`` to tolerate it, so this is a
    distinct, catchable subtype rather than a bare verification failure. The
    ``error_code`` is the value the rejection maps to, matched against a procedure's
    armed error mappings.
    """

    def __init__(
        self, message: str, *, error_code: int = RESOURCE_WRITE_PROTECTED_ERROR
    ) -> None:
        """Record the error value the rejection corresponds to."""
        super().__init__(message)
        self.error_code = error_code


class UnsupportedProcedureError(DownloadError):
    """The Load Procedure contains a step that is not supported."""


class ImageError(DownloadError):
    """The download image could not be assembled from the application data."""
