"""Transcendental Math functions evaluated like 32-bit JScript, identically on every platform."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import mpmath  # pyright: ignore[reportMissingTypeStubs]

_mp: Any = mpmath
_WORK = 160
_EXTENDED = 64


def _hp(fn: Callable[..., Any], *args: float) -> Any:
    with _mp.workprec(_WORK):
        return fn(*[_mp.mpf(a) for a in args])


def _ext(value: Any) -> Any:
    with _mp.workprec(_EXTENDED):
        return +value


def _double(fn: Callable[..., Any], *args: float) -> float:
    """Value rounded to 64-bit extended precision, then to double."""
    return float(_ext(_hp(fn, *args)))


def _exp2_extended(t: Any) -> float:
    with _mp.workprec(_WORK):
        n = _mp.nint(t)
        frac = t - n
        v = _mp.power(2, frac) - 1
    v = _ext(v)
    with _mp.workprec(_EXTENDED):
        v = v + 1
    with _mp.workprec(_WORK):
        return float(v * _mp.power(2, n))


_LOG2E = _ext(_hp(lambda: _mp.log(_mp.e, 2)))


def sin(x: float) -> float:
    return _double(_mp.sin, x)


def cos(x: float) -> float:
    return _double(_mp.cos, x)


def tan(x: float) -> float:
    return _double(_mp.tan, x)


def atan(x: float) -> float:
    return _double(_mp.atan, x)


def asin(x: float) -> float:
    if not -1 <= x <= 1:
        return math.nan
    return _double(_mp.asin, x)


def acos(x: float) -> float:
    if not -1 <= x <= 1:
        return math.nan
    return _double(_mp.acos, x)


def atan2(y: float, x: float) -> float:
    if y == 0 or x == 0 or math.isinf(x) or math.isinf(y):
        return math.atan2(y, x)
    return _double(_mp.atan2, y, x)


def log(x: float) -> float:
    if x < 0:
        return math.nan
    if x == 0:
        return -math.inf
    return _double(_mp.log, x)


def exp(x: float) -> float:
    if x > 709.8:
        return math.inf
    if x < -745.2:
        return 0.0
    if abs(x) <= 20:
        return _double(_mp.exp, x)
    with _mp.workprec(_EXTENDED):
        t = _mp.mpf(x) * _LOG2E
    return _exp2_extended(t)


def pow(x: float, y: float) -> float:
    if y == 0:
        return 1.0
    if (
        math.isnan(x)
        or math.isnan(y)
        or x == 0
        or math.isinf(x)
        or math.isinf(y)
        or x == 1
    ):
        try:
            return math.pow(x, y) if not (abs(x) == 1 and math.isinf(y)) else math.nan
        except (OverflowError, ValueError, ZeroDivisionError):
            return _pow_special(x, y)
    integer = y == math.floor(y)
    if x < 0 and not integer:
        return math.nan
    with _mp.workprec(_WORK):
        lg = _mp.log(_mp.mpf(abs(x)), 2)
    lg = _ext(lg)
    with _mp.workprec(_EXTENDED):
        t = _mp.mpf(y) * lg
    if t > 1100:
        v = math.inf
    elif t < -1200:
        v = 0.0
    else:
        v = _exp2_extended(t)
    if x < 0 and integer and int(y) % 2:
        return -v
    return v


def _pow_special(x: float, y: float) -> float:
    if x == 0:
        if y < 0:
            odd = y == math.floor(y) and int(y) % 2 == 1
            return -math.inf if odd and math.copysign(1, x) < 0 else math.inf
        return 0.0
    return math.inf if abs(x) > 1 else 0.0
