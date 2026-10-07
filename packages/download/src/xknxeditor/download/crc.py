"""Segment CRC used by the Memory Control Block (MCB) table.

Per KNX Standard v3.0.0, Chapter 3/5/1 "Resources", section 4.2.27
"PID_MCB_TABLE (PID = 27)", each loaded segment referenced by the Memory Control
Block Table is protected by a 16 bit CRC over the segment's data; the device computes that CRC on the transition to Loaded. The client can
calculate the expected value for offline validation.

That section specifies the CRC as CRC-16/CCITT with truncated polynomial
``0x1021``, input and output not reflected and no final xor, and gives the check
value ``0xE5CC`` for the string ``"123456789"``. That check value corresponds to
the initial value ``0x1D0F`` (the augmented CCITT variant) used here - the "FFFFh"
initial value quoted in the prose does not reproduce the specified check value.
"""

from __future__ import annotations

from collections.abc import Iterable

from .errors import ImageError

_POLYNOMIAL = 0x1021
_INITIAL = 0x1D0F


def segment_crc(data: Iterable[int]) -> int:
    """Return the 16 bit MCB CRC over ``data`` (an iterable of octets)."""
    crc = _INITIAL
    for octet in data:
        crc ^= (octet & 0xFF) << 8
        for _ in range(8):
            crc = (
                ((crc << 1) ^ _POLYNOMIAL) & 0xFFFF
                if crc & 0x8000
                else (crc << 1) & 0xFFFF
            )
    return crc


_MCB_ENTRY_SIZE = 8
_MCB_CRC_PROTECTED_OCTET = 4
_MCB_CRC_OFFSET = 6


def expected_mcb_table(data: bytes, segment: bytes) -> bytes:
    """Compute expected final CRCs for offline validation, never for a write.

    MCB sizes are four-byte big-endian values. The device owns CRC calculation
    at LOAD_COMPLETE; this helper only predicts the resulting protected entries.
    """
    out = bytearray(data)
    starts = list(range(0, len(out) - _MCB_ENTRY_SIZE + 1, _MCB_ENTRY_SIZE))
    sizes = [int.from_bytes(out[s : s + 4], "big") for s in starts]
    if not sizes or sum(sizes) != len(segment):
        raise ImageError("MCB sizes do not tile the object image")
    offset = 0
    for start, size in zip(starts, sizes, strict=True):
        sub_segment = segment[offset : offset + size]
        offset += size
        if out[start + _MCB_CRC_PROTECTED_OCTET] & 1:
            continue
        crc = segment_crc(sub_segment)
        out[start + _MCB_CRC_OFFSET] = (crc >> 8) & 0xFF
        out[start + _MCB_CRC_OFFSET + 1] = crc & 0xFF
    return bytes(out)
