"""
Genera package `.mse-style` KOR35 (clean-room) allineato a `kor35_mse_game_spec`.
"""
from __future__ import annotations

import io
import struct
import zlib
import zipfile
from typing import Callable

KOR35_TEMPLATE_SLUG = "kor35-standard"
KOR35_TEMPLATE_NAME = "KOR35 Standard"
KOR35_STYLE_GAME = "kor35"

KOR35_FIELD_MAPPING = {
    "code": "codice",
    "name": "nome",
    "type": "tipo",
    "energy": "energia",
    "rarity": "rarita",
    "cost": "costo_gioco",
    "attack": "attacco",
    "health": "salute",
    "initiative": "iniziativa",
    "rules": "testo_gioco",
    "lore": "testo_lore",
}


def kor35_campi_schema() -> dict:
    return {
        "version": "1",
        "mse_game": KOR35_STYLE_GAME,
        "mapping": dict(KOR35_FIELD_MAPPING),
    }


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def rgba_png(width: int, height: int, pixel_fn: Callable[[int, int], tuple[int, int, int, int]]) -> bytes:
    """PNG RGBA minimale senza dipendenze esterne."""
    rows = []
    for y in range(height):
        row = b"\x00"
        for x in range(width):
            r, g, b, a = pixel_fn(x, y)
            row += bytes((r & 255, g & 255, b & 255, a & 255))
        rows.append(row)
    compressed = zlib.compress(b"".join(rows), 9)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", ihdr),
            _chunk(b"IDAT", compressed),
            _chunk(b"IEND", b""),
        ]
    )


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def kor35_frame_png(width: int = 375, height: int = 523) -> bytes:
    """Cornice carta: bordo dorato, area interna scura, fascia stats in basso."""
    border = 14
    inner = 22
    stats_h = 52
    gold = (196, 154, 72)
    gold_dark = (140, 108, 48)
    panel = (23, 32, 51)
    panel_light = (31, 42, 68)
    stats_bg = (15, 20, 32)

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        if x < border or y < border or x >= width - border or y >= height - border:
            t = (x + y) / max(width + height, 1)
            r = _lerp(gold_dark[0], gold[0], t)
            g = _lerp(gold_dark[1], gold[1], t)
            b = _lerp(gold_dark[2], gold[2], t)
            return r, g, b, 255
        if x < inner or y < inner or x >= width - inner or y >= height - inner:
            return gold_dark[0], gold_dark[1], gold_dark[2], 255
        if y >= height - border - stats_h:
            return stats_bg[0], stats_bg[1], stats_bg[2], 230
        t = y / max(height, 1)
        r = _lerp(panel_light[0], panel[0], t)
        g = _lerp(panel_light[1], panel[1], t)
        b = _lerp(panel_light[2], panel[2], t)
        return r, g, b, 255

    return rgba_png(width, height, pixel)


def kor35_art_placeholder_png(width: int = 337, height: int = 250) -> bytes:
    """Placeholder area illustrazione (semi-trasparente)."""
    cx, cy = width / 2, height / 2

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        dx = abs(x - cx) / max(cx, 1)
        dy = abs(y - cy) / max(cy, 1)
        if dx + dy > 0.92:
            return 80, 96, 128, 40
        return 45, 55, 78, 90

    return rgba_png(width, height, pixel)


def build_kor35_style_text() -> str:
    """File `style` MSE per tutti i campi card_fields KOR35."""
    return """mse version: 2.0.0
game: kor35
short name: KOR35 Standard
full name: KOR35 Standard Card Template
version: 1.0
creator: KOR35 Card Studio
card width: 375
card height: 523
card dpi: 300
card background: rgb(23,32,51)

styling field:
    type: boolean
    name: show_stats
    initial: true
    description: Show attack / health / initiative bar on the card.

styling field:
    type: boolean
    name: show_lore
    initial: false
    description: Show flavor text strip at the bottom of the card face.

card style:
    card_frame:
        left: 0
        top: 0
        width: 375
        height: 523
        z index: 100
        render style: image
        image: images/frame.png

card style:
    art:
        left: 19
        top: 118
        width: 337
        height: 250
        z index: 5
        render style: image
        image: images/art-placeholder.png

card style:
    code:
        left: 286
        top: 24
        width: 68
        height: 22
        z index: 30
        alignment: middle right
        font:
            name: Consolas
            size: 11
            color: rgb(203,213,225)

card style:
    name:
        left: 34
        top: 44
        width: 240
        height: 36
        z index: 40
        alignment: bottom left
        font:
            name: Georgia
            size: 22
            color: rgb(248,250,252)
            weight: bold

card style:
    type:
        left: 34
        top: 82
        width: 200
        height: 22
        z index: 35
        alignment: middle left
        font:
            name: Arial
            size: 13
            color: rgb(191,219,254)

card style:
    energy:
        left: 18
        top: 16
        width: 44
        height: 44
        z index: 45
        alignment: middle center
        render style: symbol
        font:
            always symbol: true
            size: 28

card style:
    rarity:
        left: 248
        top: 82
        width: 96
        height: 20
        z index: 35
        alignment: middle right
        font:
            name: Arial
            size: 11
            color: rgb(203,213,225)

card style:
    cost:
        left: 318
        top: 52
        width: 32
        height: 32
        z index: 35
        alignment: middle center
        font:
            name: Arial
            size: 18
            color: rgb(250,204,21)
            weight: bold

card style:
    rules:
        left: 28
        top: 378
        width: 319
        height: 96
        z index: 50
        alignment: top left
        font:
            name: Georgia
            size: 12
            color: rgb(226,232,240)

card style:
    lore:
        left: 28
        top: 478
        width: 319
        height: 28
        z index: 45
        visible: {styling.show_lore}
        alignment: top left
        font:
            name: Georgia
            size: 10
            color: rgb(148,163,184)

card style:
    attack:
        left: 48
        top: 486
        width: 48
        height: 28
        z index: 60
        visible: {styling.show_stats}
        alignment: middle center
        font:
            name: Arial
            size: 20
            color: rgb(248,250,252)
            weight: bold

card style:
    health:
        left: 164
        top: 486
        width: 48
        height: 28
        z index: 60
        visible: {styling.show_stats}
        alignment: middle center
        font:
            name: Arial
            size: 20
            color: rgb(248,250,252)
            weight: bold

card style:
    initiative:
        left: 280
        top: 486
        width: 48
        height: 28
        z index: 60
        visible: {styling.show_stats}
        alignment: middle center
        font:
            name: Arial
            size: 20
            color: rgb(248,250,252)
            weight: bold
"""


def build_kor35_mse_style_zip() -> bytes:
    """Zip in-memory pronto per `import_mse_style_package`."""
    style_text = build_kor35_style_text()
    frame = kor35_frame_png()
    art = kor35_art_placeholder_png()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("style", style_text)
        zf.writestr("images/frame.png", frame)
        zf.writestr("images/art-placeholder.png", art)
    return buf.getvalue()
