from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UiSeparator:
    """A ParameterSeparator; ``hint`` is its UIHint (``HorizontalRuler``, ``Headline``,
    ``Information`` or ``Error``) and ``alignment`` its TextAlignment."""

    id: str
    text: str | None
    cell: str | None = None
    hint: str | None = None
    alignment: str | None = None
    icon: str | None = None
