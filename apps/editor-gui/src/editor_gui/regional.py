"""Number and date formats of the operating system's regional settings.

The regional locale (e.g. ``de-DE``) is taken from the operating system; its separators and date
pattern come from fixed tables, so a locale formats the same on every operating system.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

# Short date pattern per locale, else per language: d/M unpadded, dd/MM padded, yyyy the year.
_SHORT_DATES = {
    "de": "dd.MM.yyyy",
    "en-US": "M/d/yyyy",
    "en-GB": "dd/MM/yyyy",
    "nl": "d-M-yyyy",
}


@dataclass(frozen=True, slots=True)
class RegionalFormat:
    decimal: str = "."
    group: str = ","
    short_date: str = "yyyy-MM-dd"


@cache
def regional_format() -> RegionalFormat:
    """The regional format of the operating system's locale."""
    from xknxeditor.prod.script.compat.runtime import number_separators, system_locale

    locale = system_locale()
    decimal, group = number_separators(locale)
    short_date = _SHORT_DATES.get(locale) or _SHORT_DATES.get(
        locale.split("-")[0], RegionalFormat.short_date
    )
    return RegionalFormat(decimal, group, short_date)
