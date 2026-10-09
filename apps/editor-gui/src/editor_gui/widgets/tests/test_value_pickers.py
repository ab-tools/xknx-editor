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
    ("text", "year_shown", "pattern", "date"),
    [
        ("2026-10-09", True, "yyyy-MM-dd", "2026-10-09"),
        ("2026-2-3", True, "yyyy-MM-dd", "2026-02-03"),
        ("9.10.2026", True, "dd.MM.yyyy", "2026-10-09"),
        ("2026-10-09", True, "dd.MM.yyyy", "2026-10-09"),
        ("10/9/2026", True, "M/d/yyyy", "2026-10-09"),
        ("30.02.2026", True, "dd.MM.yyyy", None),
        ("9.10", True, "dd.MM.yyyy", None),
        ("9.10", False, "dd.MM.yyyy", "2020-10-09"),
        ("10-09", False, "yyyy-MM-dd", "2020-10-09"),
        ("nonsense", True, "dd.MM.yyyy", None),
    ],
)
def test_parse_date(
    text: str, year_shown: bool, pattern: str, date: str | None
) -> None:
    assert parse_date(text, year_shown, "2020-01-01", pattern) == date


@pytest.mark.parametrize(
    ("year_shown", "pattern", "shown"),
    [
        (True, "yyyy-MM-dd", "2026-01-09"),
        (False, "yyyy-MM-dd", "01-09"),
        (True, "dd.MM.yyyy", "09.01.2026"),
        (False, "dd.MM.yyyy", "09.01"),
        (True, "M/d/yyyy", "1/9/2026"),
        (False, "d-M-yyyy", "9-1"),
    ],
)
def test_format_date(year_shown: bool, pattern: str, shown: str) -> None:
    assert format_date("2026-01-09", year_shown, pattern) == shown
