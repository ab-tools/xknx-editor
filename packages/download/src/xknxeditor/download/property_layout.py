"""Fixed property element widths used by load controls (KNX Resources)."""

from __future__ import annotations

from xknxeditor.namespaces.intermediate.prop_type_t import PropType

from .errors import UnsupportedProcedureError

# PID5 has asymmetric read/write widths; never infer its write size from a read.
STANDARD_WRITE_WIDTHS = {1: 2, 5: 10, 13: 5, 14: 1, 27: 8, 56: 2}
_BASIC_WIDTHS = (10, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4, 8, 10, 3, 5, 8)


def property_width(data_type: PropType | int) -> int:
    """Resolve a declared PDT or the type octet in A_PropertyDescription_Response."""
    if isinstance(data_type, PropType):
        name = data_type.value
        if name.startswith("PDT_GENERIC_"):
            return int(name.rsplit("_", 1)[1])
        names = list(PropType)
        index = names.index(data_type)
        if index < len(_BASIC_WIDTHS):
            return _BASIC_WIDTHS[index]
        extra = {
            "PDT_VERSION": 3,
            "PDT_ALARM_INFO": 6,
            "PDT_BINARY_INFORMATION": 1,
            "PDT_BITSET8": 1,
            "PDT_BITSET16": 2,
            "PDT_ENUM8": 1,
            "PDT_SCALING": 1,
        }
        if name in extra:
            return extra[name]
    else:
        code = data_type & 0x3F
        if code < len(_BASIC_WIDTHS):
            return _BASIC_WIDTHS[code]
        if 17 <= code <= 36:
            return code - 16
        extra_codes = {48: 3, 49: 6, 50: 1, 51: 1, 52: 2, 53: 1, 54: 1}
        if code in extra_codes:
            return extra_codes[code]
    raise UnsupportedProcedureError(f"unsupported property element type {data_type}")
