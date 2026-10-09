from __future__ import annotations

import pytest

from editor_gui.widgets.value_pickers import (
    format_date,
    parse_color,
    parse_date,
    shade,
)


@pytest.mark.parametrize(
    ("text", "color"),
    [
        ("#ffffff", "#FFFFFF"),
        ("00b050", "#00B050"),
        (" #1F497D ", "#1F497D"),
        ("#12345", None),
        ("red", None),
    ],
)
def test_parse_color(text: str, color: str | None) -> None:
    assert parse_color(text) == color


def test_shade_lightens_and_darkens() -> None:
    assert shade(0x000000, 0.5) == 0x808080
    assert shade(0xFFFFFF, -0.5) == 0x808080
    assert shade(0x4F81BD, 0.0) == 0x4F81BD


@pytest.mark.parametrize(
    ("text", "year_shown", "date"),
    [
        ("2026-10-09", True, "2026-10-09"),
        ("2026-2-3", True, "2026-02-03"),
        ("9.10.2026", True, "2026-10-09"),
        ("2026-02-30", True, None),
        ("10-09", True, None),
        ("10-09", False, "2020-10-09"),
        ("nonsense", True, None),
    ],
)
def test_parse_date(text: str, year_shown: bool, date: str | None) -> None:
    assert parse_date(text, year_shown, "2020-01-01") == date


def test_format_date_hides_the_year_when_the_type_does() -> None:
    assert format_date("2026-10-09", True) == "2026-10-09"
    assert format_date("2026-10-09", False) == "10-09"
