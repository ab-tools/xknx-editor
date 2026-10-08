from __future__ import annotations

import base64
import binascii
import datetime
import ipaddress
import math
import re

from xknxeditor.namespaces.intermediate.parameter_type_t_type_color import (
    ParameterTypeTypeColor,
)
from xknxeditor.namespaces.intermediate.parameter_type_t_type_date import (
    ParameterTypeTypeDate,
)
from xknxeditor.namespaces.intermediate.parameter_type_t_type_float import (
    ParameterTypeTypeFloat,
)
from xknxeditor.namespaces.intermediate.parameter_type_t_type_ipaddress import (
    ParameterTypeTypeIpaddress,
)
from xknxeditor.namespaces.intermediate.parameter_type_t_type_ipaddress_version import (
    ParameterTypeTypeIpaddressVersion,
)
from xknxeditor.namespaces.intermediate.parameter_type_t_type_number import (
    ParameterTypeTypeNumber,
)
from xknxeditor.namespaces.intermediate.parameter_type_t_type_raw_data import (
    ParameterTypeTypeRawData,
)
from xknxeditor.namespaces.intermediate.parameter_type_t_type_restriction import (
    ParameterTypeTypeRestriction,
)
from xknxeditor.namespaces.intermediate.parameter_type_t_type_text import (
    ParameterTypeTypeText,
)
from xknxeditor.namespaces.intermediate.parameter_type_t_type_time import (
    ParameterTypeTypeTime,
)

JsValue = int | float | str | bool | None

_INTEGER_TYPES = (
    ParameterTypeTypeNumber,
    ParameterTypeTypeRestriction,
    ParameterTypeTypeTime,
)
_STRING_TYPES = (
    ParameterTypeTypeText,
    ParameterTypeTypeDate,
    ParameterTypeTypeIpaddress,
    ParameterTypeTypeColor,
    ParameterTypeTypeRawData,
)
_INT_LITERAL = re.compile(r"^\s*[+-]?\d+\s*$")
_COLOR = re.compile(r"^#?[0-9A-Fa-f]{6}$")


def is_numeric(tc: object) -> bool:
    return isinstance(tc, (*_INTEGER_TYPES, ParameterTypeTypeFloat))


def has_value(tc: object) -> bool:
    return is_numeric(tc) or isinstance(tc, _STRING_TYPES)


def _parse_int(value: str) -> int:
    v = value.strip()
    if v[:2].lower() == "0x":
        return int(v, 16)
    return int(v)


def to_js(value: str | None, tc: object) -> JsValue:
    """Stored value string to the JS value a script sees."""
    if value is None or not has_value(tc):
        return None
    if isinstance(tc, _INTEGER_TYPES):
        try:
            return _parse_int(value)
        except ValueError:
            return value
    if isinstance(tc, ParameterTypeTypeFloat):
        try:
            f = float(value)
        except ValueError:
            return value
        return int(f) if f.is_integer() and abs(f) < 2**53 else f
    return value


def dotnet_number_to_string(x: float) -> str:
    """Invariant ``Double.ToString()`` of .NET Framework (15 significant digits)."""
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0:
        return "0"
    return format(x, ".15G")


def from_js(js: object, tc: object) -> str:
    """Coerce a value written by a script to the stored value string."""
    if not has_value(tc):
        raise ValueError("parameter has no value")
    if isinstance(tc, _INTEGER_TYPES):
        if isinstance(js, bool):
            return "1" if js else "0"
        if isinstance(js, int):
            return str(js)
        if isinstance(js, float):
            if not math.isfinite(js):
                raise ValueError(f"value {js!r} is not a number")
            return str(round(js))
        if isinstance(js, str) and _INT_LITERAL.match(js):
            return str(int(js))
        raise ValueError(f"value {js!r} is not an integer")
    if isinstance(tc, ParameterTypeTypeFloat):
        if isinstance(js, bool):
            return "1" if js else "0"
        if isinstance(js, (int, float)):
            f = float(js)
        elif isinstance(js, str):
            try:
                f = float(js)
            except ValueError as exc:
                raise ValueError(f"value {js!r} is not a number") from exc
        else:
            raise ValueError(f"value {js!r} is not a number")
        if not math.isfinite(f):
            raise ValueError(f"value {js!r} is not a number")
        return str(int(f)) if f.is_integer() else repr(f)
    if js is None:
        return ""
    if isinstance(js, bool):
        return "True" if js else "False"
    if isinstance(js, int):
        return str(js)
    if isinstance(js, float):
        return dotnet_number_to_string(js)
    return str(js)


def check_value(value: str, tc: object, *, text_encoding: str = "latin-1") -> str:
    """Strict validation of a value against its parameter type; returns the normalized value."""
    if isinstance(tc, ParameterTypeTypeNumber):
        n = _int_or_raise(value)
        _check_range(n, tc.min_inclusive, tc.max_inclusive, value)
        return str(n)
    if isinstance(tc, ParameterTypeTypeTime):
        n = _int_or_raise(value)
        _check_range(n, tc.min_inclusive, tc.max_inclusive, value)
        return str(n)
    if isinstance(tc, ParameterTypeTypeRestriction):
        n = _int_or_raise(value)
        if all(e.value != n for e in tc.enumeration):
            raise ValueError(f"value {value!r} is not a valid option")
        return str(n)
    if isinstance(tc, ParameterTypeTypeFloat):
        try:
            f = float(value)
        except ValueError as exc:
            raise ValueError(f"value {value!r} is not a number") from exc
        if not math.isfinite(f):
            raise ValueError(f"value {value!r} is not a number")
        if not tc.min_inclusive <= f <= tc.max_inclusive:
            raise ValueError(
                f"value {value!r} outside {tc.min_inclusive}..{tc.max_inclusive}"
            )
        return value
    if isinstance(tc, ParameterTypeTypeText):
        if tc.pattern and re.search(tc.pattern, value) is None:
            raise ValueError(f"value {value!r} does not match the required format")
        size = len(value.encode(text_encoding, errors="replace"))
        if size > tc.size_in_bit // 8:
            raise ValueError(f"text longer than {tc.size_in_bit // 8} characters")
        return value
    if isinstance(tc, ParameterTypeTypeDate):
        try:
            datetime.date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"value {value!r} is not a date") from exc
        return value
    if isinstance(tc, ParameterTypeTypeIpaddress):
        try:
            addr = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ValueError(f"value {value!r} is not an IP address") from exc
        want = 6 if tc.version == ParameterTypeTypeIpaddressVersion.IPV6 else 4
        if addr.version != want:
            raise ValueError(f"value {value!r} is not an IPv{want} address")
        return value
    if isinstance(tc, ParameterTypeTypeColor):
        if not _COLOR.match(value):
            raise ValueError(f"value {value!r} is not a color")
        return value
    if isinstance(tc, ParameterTypeTypeRawData):
        try:
            data = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"value {value!r} is not valid data") from exc
        if len(data) > tc.max_size:
            raise ValueError(f"data longer than {tc.max_size} bytes")
        return value
    raise ValueError("parameter has no value")


def _int_or_raise(value: str) -> int:
    try:
        return _parse_int(value)
    except ValueError as exc:
        raise ValueError(f"value {value!r} is not an integer") from exc


def _check_range(n: int, lo: int, hi: int, raw: str) -> None:
    if not lo <= n <= hi:
        raise ValueError(f"value {raw!r} outside {lo}..{hi}")
