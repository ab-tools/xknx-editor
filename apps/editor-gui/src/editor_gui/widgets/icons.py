"""Icons an application ships as PNG images, drawn in the text colour when single-coloured."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from imgui_bundle import hello_imgui, imgui

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True, slots=True)
class Icon:
    texture: imgui.ImTextureRef
    # Single-coloured icons are stored white and drawn tinted with the text colour.
    tinted: bool


_cache: dict[str, Icon | None] = {}


def _chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    chunks: list[tuple[bytes, bytes]] = []
    pos = len(_PNG_SIGNATURE)
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        chunks.append((kind, data[pos + 8 : pos + 8 + length]))
        pos += 12 + length
    return chunks


def _unfilter(raw: bytes, width: int, height: int) -> bytearray:
    """Reverse the PNG scanline filters of 8 bit RGBA image data."""
    stride = width * 4
    out = bytearray()
    prev = bytearray(stride)
    pos = 0
    for _ in range(height):
        kind = raw[pos]
        line = bytearray(raw[pos + 1 : pos + 1 + stride])
        pos += 1 + stride
        for x in range(stride):
            left = line[x - 4] if x >= 4 else 0
            up = prev[x]
            if kind == 1:
                line[x] = (line[x] + left) & 0xFF
            elif kind == 2:
                line[x] = (line[x] + up) & 0xFF
            elif kind == 3:
                line[x] = (line[x] + (left + up) // 2) & 0xFF
            elif kind == 4:
                up_left = prev[x - 4] if x >= 4 else 0
                p = left + up - up_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
                pred = left if pa <= pb and pa <= pc else up if pb <= pc else up_left
                line[x] = (line[x] + pred) & 0xFF
        out += line
        prev = line
    return out


def _chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def white_png(data: bytes) -> bytes | None:
    """``data`` re-encoded in white with its alpha, if it is a single-coloured RGBA PNG."""
    if not data.startswith(_PNG_SIGNATURE):
        return None
    try:
        chunks = _chunks(data)
        header = next(payload for kind, payload in chunks if kind == b"IHDR")
        width, height, depth, colour, _, _, interlace = struct.unpack(
            ">IIBBBBB", header
        )
        if depth != 8 or colour != 6 or interlace != 0:
            return None
        raw = zlib.decompress(b"".join(p for kind, p in chunks if kind == b"IDAT"))
        pixels = _unfilter(raw, width, height)
    except (StopIteration, struct.error, zlib.error, IndexError):
        return None
    colours = {
        bytes(pixels[i : i + 3]) for i in range(0, len(pixels), 4) if pixels[i + 3]
    }
    if len(colours) > 1:
        return None
    for i in range(0, len(pixels), 4):
        pixels[i : i + 3] = b"\xff\xff\xff"
    stride = width * 4
    rows = b"".join(
        b"\x00" + pixels[y * stride : (y + 1) * stride] for y in range(height)
    )
    return (
        _PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(rows))
        + _chunk(b"IEND", b"")
    )


def has_icon(key: str) -> bool:
    """Whether the icon for ``key`` was loaded (or found missing) before."""
    return key in _cache


def load_icon(key: str, data: bytes | None) -> Icon | None:
    """The texture for an icon image, created once per ``key``."""
    if key in _cache:
        return _cache[key]
    icon: Icon | None = None
    if data:
        white = white_png(data)
        try:
            image = hello_imgui.image_and_size_from_encoded_data(
                white or data, f"icon:{key}"
            )
        except RuntimeError:
            image = None
        if image is not None and image.size.x > 0:
            icon = Icon(imgui.ImTextureRef(image.texture_id), white is not None)
    _cache[key] = icon
    return icon


def draw_icon(icon: Icon, pos: imgui.ImVec2, size: float) -> None:
    """Draw ``icon`` as a ``size`` square at screen position ``pos``."""
    colour = imgui.get_color_u32(imgui.Col_.text) if icon.tinted else 0xFFFFFFFF
    imgui.get_window_draw_list().add_image(
        icon.texture,
        pos,
        imgui.ImVec2(pos.x + size, pos.y + size),
        imgui.ImVec2(0, 0),
        imgui.ImVec2(1, 1),
        colour,
    )
