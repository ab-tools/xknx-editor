from __future__ import annotations

import pytest

from editor_gui.widgets.float_format import format_float, parse_float, step_float


@pytest.mark.parametrize(
    ("stored", "shown"),
    [
        ("5.011537700000000E+001", "50.115377"),
        ("8.683764000000000E+000", "8.683764"),
        ("50.115377", "50.115377"),
        ("0", "0"),
        ("-0.0", "0"),
        ("1E12", "1000000000000"),
        ("1E15", "1E+15"),
        ("0.0001", "0.0001"),
        ("0.00001", "1E-05"),
        ("0.1", "0.1"),
        ("not a number", "not a number"),
    ],
)
def test_general_format(stored: str, shown: str) -> None:
    assert format_float(stored) == shown


@pytest.mark.parametrize(
    ("stored", "display_format", "shown"),
    [
        ("1.005", "0.00", "1.01"),
        ("2.5", "0", "3"),
        ("-2.5", "0", "-3"),
        ("-0.001", "0.00", "0.00"),
        ("0.5", "#0.00", "0.50"),
        ("1234567.891", "#,##0.00", "1,234,567.89"),
        ("12", "000", "012"),
        ("1234567", "0,", "1235"),
        ("12345", "0.00E+00", "1.23E+04"),
        ("0.000123", "0.0E0", "1.2E-4"),
        ("9.99", "0.0E+00", "1.0E+01"),
    ],
)
def test_display_format(stored: str, display_format: str, shown: str) -> None:
    assert format_float(stored, display_format) == shown


def test_display_factor_and_offset() -> None:
    assert format_float("2", display_factor=0.5, display_offset=10) == "11"
    assert parse_float("11", display_factor=0.5, display_offset=10) == "2"


@pytest.mark.parametrize(
    ("text", "stored"),
    [
        ("50.115377", "50.115377"),
        ("50,115377", "50.115377"),
        (" 8.5 ", "8.5"),
        ("120", "90"),
        ("-120", "-90"),
        ("abc", None),
        ("nan", None),
    ],
)
def test_parse(text: str, stored: str | None) -> None:
    assert parse_float(text, minimum=-90, maximum=90) == stored


@pytest.mark.parametrize(
    ("stored", "steps", "increment", "result"),
    [
        ("50.1", 1, None, "51.1"),
        ("0.1", 2, 0.1, "0.3"),
        ("89.5", 1, None, "90"),
        ("-89.5", -1, None, "-90"),
        ("abc", 1, None, None),
    ],
)
def test_step(
    stored: str, steps: int, increment: float | None, result: str | None
) -> None:
    assert step_float(stored, steps, increment, -90, 90) == result


def test_regional_separators() -> None:
    german = {"decimal": ",", "group": "."}
    assert format_float("5.011537700000000E+001", **german) == "50,115377"
    assert format_float("1234567.891", "#,##0.00", **german) == "1.234.567,89"
    assert parse_float("50,115377", **german) == "50.115377"
    assert parse_float("1.234,5", **german) == "1234.5"
    assert parse_float("50.115377", **german) == "50.115377"
    assert parse_float("1.234.567", **german) is None
