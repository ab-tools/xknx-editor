"""Display and input of float parameter values.

A value is shown with the parameter type's ``DisplayFormat`` (a custom numeric format such as
``0.000``, ``#,##0.00`` or ``0.00E+00``), otherwise with up to 15 significant digits, after
applying the type's display factor and offset.
"""

from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_FORMAT = re.compile(
    r"(?P<int>[#,]*[0,]+)(?:\.(?P<dec>0*))?(?:(?P<e>[eE])(?P<sign>[+-]?)(?P<exp>0+))?"
)


def format_float(
    stored: str,
    display_format: str | None = None,
    display_factor: float | None = None,
    display_offset: float | None = None,
) -> str:
    """The stored value as shown; text that is not a number is returned unchanged."""
    try:
        value = float(stored)
    except ValueError:
        return stored
    if not math.isfinite(value):
        return stored
    value = value * (display_factor or 1.0) + (display_offset or 0.0)
    match = _FORMAT.fullmatch(display_format) if display_format else None
    if match is None:
        return _general(value)
    return _custom(value, match)


def parse_float(
    text: str,
    minimum: float | None = None,
    maximum: float | None = None,
    display_factor: float | None = None,
    display_offset: float | None = None,
) -> str | None:
    """The value to store for ``text`` as entered, clamped to the range; None if not a number."""
    cleaned = text.strip().replace(" ", "")
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        shown = float(cleaned)
    except ValueError:
        return None
    if not math.isfinite(shown):
        return None
    value = (shown - (display_offset or 0.0)) / (display_factor or 1.0)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return _general(value)


def step_float(
    stored: str,
    steps: int,
    increment: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> str | None:
    """The stored value moved by ``steps`` increments, clamped to the range."""
    try:
        value = float(stored)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    value += steps * (increment or 1.0)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return _general(value)


def _general(value: float) -> str:
    text = format(value, ".15g").replace("e", "E")
    return "0" if text == "-0" else text


def _custom(value: float, match: re.Match[str]) -> str:
    int_part = match["int"]
    trailing_commas = len(int_part) - len(int_part.rstrip(","))
    digits = int_part.rstrip(",")
    grouping = "," in digits
    min_int = digits.count("0")
    decimals = len(match["dec"] or "")
    number = Decimal(format(value, ".15g")) / Decimal(1000) ** trailing_commas
    if match["e"]:
        return _scientific(number, max(min_int, 1), decimals, match)
    rounded = number.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    negative = rounded < 0
    whole, _, fraction = f"{abs(rounded):f}".partition(".")
    whole = whole.lstrip("0").rjust(min_int, "0")
    if grouping:
        whole = f"{int(whole or '0'):,}" if whole else ""
        whole = whole.rjust(min_int, "0")
    text = whole + ("." + fraction if decimals else "")
    return f"-{text}" if negative and rounded != 0 else text


def _scientific(
    number: Decimal, int_digits: int, decimals: int, match: re.Match[str]
) -> str:
    if number == 0:
        exponent = 0
        mantissa = Decimal(0)
    else:
        exponent = number.copy_abs().adjusted() - (int_digits - 1)
        mantissa = number.scaleb(-exponent)
        rounded = mantissa.quantize(
            Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP
        )
        if rounded.copy_abs().adjusted() >= int_digits:
            exponent += 1
            mantissa = number.scaleb(-exponent)
    try:
        mantissa = mantissa.quantize(
            Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP
        )
    except InvalidOperation:
        return _general(float(number))
    negative = mantissa < 0
    whole, _, fraction = f"{abs(mantissa):f}".partition(".")
    text = whole.rjust(int_digits, "0") + ("." + fraction if decimals else "")
    sign = "-" if exponent < 0 else ("+" if match["sign"] == "+" else "")
    text += f"{match['e']}{sign}{abs(exponent):0{len(match['exp'])}d}"
    return f"-{text}" if negative and mantissa != 0 else text
