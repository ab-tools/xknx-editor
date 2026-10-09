from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UiButton:
    """A Button of the application's dynamic section.

    ``id`` is qualified with the module instance; ``handler_parameters`` has module arguments
    substituted. ``online`` is ``"ConnectionOriented"``/``"ConnectionLess"`` for handlers that need
    a bus connection, ``None`` for offline handlers."""

    id: str
    text: str
    cell: str | None = None
    read_only: bool = False
    icon: str | None = None
    name: str | None = None
    handler: str | None = None
    handler_parameters: str | None = None
    online: str | None = None
    module_instance_id: str | None = None
