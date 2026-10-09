"""Colour and date parameter fields with a picker popup next to the text entry.

A colour is stored as ``#RRGGBB``, a date as ``YYYY-MM-DD``.
"""

from __future__ import annotations

import calendar
import datetime
import re
from collections.abc import Callable

from imgui_bundle import imgui

from editor_gui.widgets.dpi import px
from editor_gui.widgets.strings import S

# Theme colours (top row of the palette) and the standard colours row.
_THEME_COLORS = (
    0xFFFFFF,
    0x000000,
    0xEEECE1,
    0x1F497D,
    0x4F81BD,
    0xC0504D,
    0x9BBB59,
    0x8064A2,
    0x4BACC6,
    0xF79646,
)
_STANDARD_COLORS = (
    0xC00000,
    0xFF0000,
    0xFFC000,
    0xFFFF00,
    0x92D050,
    0x00B050,
    0x00B0F0,
    0x0070C0,
    0x002060,
    0x7030A0,
)
# Shades below each theme colour: positive lightens towards white, negative darkens.
_SHADES = (0.8, 0.6, 0.4, -0.25, -0.5)
_WHITE_SHADES = (-0.05, -0.15, -0.25, -0.35, -0.5)
_BLACK_SHADES = (0.5, 0.35, 0.25, 0.15, 0.05)

_HEX = re.compile(r"#?([0-9A-Fa-f]{6})")
_ISO_DATE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_DOTTED_DATE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
_MONTH_DAY = re.compile(r"(\d{1,2})-(\d{1,2})")


def parse_color(text: str) -> str | None:
    """``#RRGGBB`` for a hex colour entered with or without ``#``; None if invalid."""
    match = _HEX.fullmatch(text.strip())
    return f"#{match[1].upper()}" if match else None


def shade(rgb: int, amount: float) -> int:
    """``rgb`` lightened (positive ``amount``) or darkened (negative) by that fraction."""
    channels = ((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF)
    if amount >= 0:
        shaded = [round(c + (255 - c) * amount) for c in channels]
    else:
        shaded = [round(c * (1 + amount)) for c in channels]
    return (shaded[0] << 16) | (shaded[1] << 8) | shaded[2]


def parse_date(text: str, year_shown: bool, stored: str) -> str | None:
    """``YYYY-MM-DD`` for an entered date; None if invalid.

    Accepts ``YYYY-MM-DD`` and ``DD.MM.YYYY``; without a shown year ``MM-DD``, keeping the
    year of ``stored``.
    """
    text = text.strip()
    if match := _ISO_DATE.fullmatch(text):
        year, month, day = (int(g) for g in match.groups())
    elif match := _DOTTED_DATE.fullmatch(text):
        day, month, year = (int(g) for g in match.groups())
    elif not year_shown and (match := _MONTH_DAY.fullmatch(text)):
        month, day = (int(g) for g in match.groups())
        year = _date_of(stored).year
    else:
        return None
    try:
        return datetime.date(year, month, day).isoformat()
    except ValueError:
        return None


def format_date(stored: str, year_shown: bool) -> str:
    """The stored date as shown: ``YYYY-MM-DD``, or ``MM-DD`` when the type hides the year."""
    if not year_shown and _ISO_DATE.fullmatch(stored):
        return stored[5:]
    return stored


def render_color_param(
    widget_id: str, value: str, on_change: Callable[[str], None], differs: bool
) -> None:
    """A hex colour entry with a swatch that opens the colour picker."""
    width = imgui.calc_item_width()
    rgb = int(value[1:], 16) if not differs and parse_color(value) else 0xFFFFFF
    size = imgui.get_frame_height()
    popup = f"##color_popup_{widget_id}"
    if imgui.color_button(
        f"##swatch_{widget_id}", _vec4(rgb), 0, imgui.ImVec2(size, size)
    ):
        imgui.open_popup(popup)
    imgui.same_line(0, imgui.get_style().item_inner_spacing.x)
    imgui.set_next_item_width(
        max(px(40.0), width - size - imgui.get_style().item_inner_spacing.x)
    )
    if differs:
        _, text = imgui.input_text_with_hint(f"##{widget_id}", S.PARAM_DIFFERS, "")
    else:
        _, text = imgui.input_text(f"##{widget_id}", value)
    if imgui.is_item_deactivated_after_edit() and text != value:
        color = parse_color(text)
        if color is not None:
            on_change(color)
    if imgui.begin_popup(popup):
        picked = _render_color_popup(rgb)
        if picked is not None:
            on_change(f"#{picked:06X}")
        imgui.end_popup()


def _render_color_popup(current: int) -> int | None:
    picked: int | None = None
    if imgui.begin_tab_bar("##color_tabs"):
        if imgui.begin_tab_item(S.COLOR_STANDARD)[0]:
            imgui.text_disabled(S.COLOR_THEME_COLORS)
            for col, base in enumerate(_THEME_COLORS):
                if col:
                    imgui.same_line()
                picked = _swatch(base, current) or picked
            shades = {0xFFFFFF: _WHITE_SHADES, 0x000000: _BLACK_SHADES}
            for row in range(len(_SHADES)):
                for col, base in enumerate(_THEME_COLORS):
                    if col:
                        imgui.same_line()
                    amount = shades.get(base, _SHADES)[row]
                    picked = _swatch(shade(base, amount), current) or picked
            imgui.text_disabled(S.COLOR_STANDARD_COLORS)
            for col, rgb in enumerate(_STANDARD_COLORS):
                if col:
                    imgui.same_line()
                picked = _swatch(rgb, current) or picked
            imgui.end_tab_item()
        if imgui.begin_tab_item(S.COLOR_ADVANCED)[0]:
            color = [((current >> s) & 0xFF) / 255.0 for s in (16, 8, 0)]
            changed, color = imgui.color_picker3(
                "##color_picker", color, imgui.ColorEditFlags_.display_hex
            )
            if imgui.is_item_deactivated_after_edit() or (
                changed and not imgui.is_mouse_down(imgui.MouseButton_.left)
            ):
                r, g, b = (round(c * 255) for c in color)
                picked = (r << 16) | (g << 8) | b
            imgui.end_tab_item()
        imgui.end_tab_bar()
    if picked is not None:
        imgui.close_current_popup()
    return picked


def _swatch(rgb: int, current: int) -> int | None:
    size = imgui.ImVec2(px(18.0), px(18.0))
    if rgb == current:
        imgui.push_style_var(imgui.StyleVar_.frame_border_size, px(2.0))
    clicked = imgui.color_button(
        f"#{rgb:06X}##swatch", _vec4(rgb), imgui.ColorEditFlags_.no_tooltip, size
    )
    if rgb == current:
        imgui.pop_style_var()
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"#{rgb:06X}")
    return rgb if clicked else None


def _vec4(rgb: int) -> imgui.ImVec4:
    return imgui.ImVec4(
        ((rgb >> 16) & 0xFF) / 255.0,
        ((rgb >> 8) & 0xFF) / 255.0,
        (rgb & 0xFF) / 255.0,
        1.0,
    )


# Month shown by each open date popup, keyed by widget id.
_shown_month: dict[str, tuple[int, int]] = {}


def render_date_param(
    widget_id: str,
    value: str,
    year_shown: bool,
    on_change: Callable[[str], None],
    differs: bool,
) -> None:
    """A date entry with a button that opens a calendar."""
    width = imgui.calc_item_width()
    button = imgui.calc_text_size("...").x + 2 * imgui.get_style().frame_padding.x
    spacing = imgui.get_style().item_inner_spacing.x
    imgui.set_next_item_width(max(px(60.0), width - button - spacing))
    shown = "" if differs else format_date(value, year_shown)
    if differs:
        _, text = imgui.input_text_with_hint(f"##{widget_id}", S.PARAM_DIFFERS, "")
    else:
        _, text = imgui.input_text(f"##{widget_id}", shown)
    if imgui.is_item_deactivated_after_edit() and text != shown:
        date = parse_date(text, year_shown, value)
        if date is not None:
            on_change(date)
    imgui.same_line(0, spacing)
    popup = f"##date_popup_{widget_id}"
    if imgui.button(f"...##date_{widget_id}"):
        current = _date_of(value)
        _shown_month[widget_id] = (current.year, current.month)
        imgui.open_popup(popup)
    if imgui.begin_popup(popup):
        picked = _render_calendar(widget_id, _date_of(value), year_shown)
        if picked is not None:
            on_change(picked.isoformat())
            imgui.close_current_popup()
        imgui.end_popup()


def _date_of(stored: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(stored)
    except ValueError:
        return datetime.date.today()


def _render_calendar(
    widget_id: str, selected: datetime.date, year_shown: bool
) -> datetime.date | None:
    year, month = _shown_month.get(widget_id, (selected.year, selected.month))
    if year_shown and imgui.button("<<"):
        year -= 1
    imgui.same_line()
    if imgui.arrow_button("##prev_month", imgui.Dir.left):
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    imgui.same_line()
    imgui.text(f"{year:04d}-{month:02d}" if year_shown else f"{month:02d}")
    imgui.same_line()
    if imgui.arrow_button("##next_month", imgui.Dir.right):
        year, month = (year, month + 1) if month < 12 else (year + 1, 1)
    if year_shown:
        imgui.same_line()
        if imgui.button(">>"):
            year += 1
    year = min(max(year, datetime.MINYEAR), datetime.MAXYEAR)
    _shown_month[widget_id] = (year, month)

    picked: datetime.date | None = None
    flags = imgui.TableFlags_.sizing_fixed_same | imgui.TableFlags_.no_saved_settings
    if imgui.begin_table("##calendar", 7, flags):
        for name in S.CALENDAR_WEEKDAYS.split():
            imgui.table_next_column()
            imgui.text_disabled(name)
        for week in calendar.Calendar(firstweekday=0).monthdatescalendar(year, month):
            imgui.table_next_row()
            for day in week:
                imgui.table_next_column()
                if day.month != month:
                    continue
                if imgui.selectable(
                    f"{day.day:2d}##{day.isoformat()}",
                    day == selected,
                    0,
                    imgui.ImVec2(imgui.calc_text_size("00").x, 0),
                )[0]:
                    picked = day
        imgui.end_table()
    return picked
