"""Renders the Markdown subset used by application help pages."""

from __future__ import annotations

import re

from imgui_bundle import imgui

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
_NUMBERED = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPHASIS = re.compile(r"(\*\*|__|\*|_|`)(.+?)\1")
_HEADING_COLOR = imgui.ImVec4(0.55, 0.78, 1.0, 1.0)


def plain(text: str) -> str:
    """Inline Markdown reduced to its visible text."""
    text = _IMAGE.sub("", text)
    text = _LINK.sub(r"\1", text)
    return _EMPHASIS.sub(r"\2", text)


def render_markdown(text: str) -> None:
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            imgui.text_wrapped(plain(" ".join(paragraph)))
            paragraph.clear()

    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flush()
            imgui.spacing()
        elif m := _HEADING.match(line):
            flush()
            imgui.text_colored(_HEADING_COLOR, plain(m.group(2)))
        elif m := _BULLET.match(line):
            flush()
            imgui.bullet()
            imgui.text_wrapped(plain(m.group(1)))
        elif m := _NUMBERED.match(line):
            flush()
            imgui.text_wrapped(f"{m.group(1)}. {plain(m.group(2))}")
        else:
            paragraph.append(line.strip())
    flush()
