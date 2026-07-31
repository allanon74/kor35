"""
Genera package `.mse-style` KOR35 (clean-room) allineato a `kor35_mse_game_spec`.

Layout ispirato ai TCG moderni (finestra art ampia, title bar, type line, rules box, PT):
pulito, leggibile, senza cornici opache che nascondono testo/art.
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
KOR35_STYLE_VERSION = "2.0"

KOR35_FIELD_MAPPING = {
    "code": "codice",
    "name": "nome",
    "image": "immagine",
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
    return int(a + (b - a) * max(0.0, min(1.0, t)))


def kor35_frame_png(width: int = 375, height: int = 523) -> bytes:
    """
    Cornice TCG: bordo scuro + filetto oro, finestre title/art/type/rules/stats
    trasparenti (il testo e l'arte vivono sotto come layer CSS).
    """
    # Geometria allineata a build_kor35_style_text()
    margin = 12
    art = (22, 78, 331, 210)  # left, top, w, h
    title = (22, 18, 331, 52)
    type_line = (22, 292, 331, 28)
    rules = (22, 326, 331, 130)
    stats = (22, 464, 331, 44)

    ink = (18, 22, 32)
    ink2 = (28, 34, 48)
    gold = (212, 175, 95)
    gold_hi = (240, 214, 140)
    gold_lo = (150, 118, 55)

    windows = (title, art, type_line, rules, stats)

    def in_box(x: int, y: int, box: tuple[int, int, int, int]) -> bool:
        l, t, w, h = box
        return l <= x < l + w and t <= y < t + h

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        # Trasparente nelle finestre contenuto
        for box in windows:
            if in_box(x, y, box):
                return 0, 0, 0, 0

        # Bordo esterno pieno
        if x < margin or y < margin or x >= width - margin or y >= height - margin:
            # Filetto oro sul bordo interno
            near_inner = (
                x == margin - 1
                or y == margin - 1
                or x == width - margin
                or y == height - margin
            )
            if near_inner:
                return gold_hi[0], gold_hi[1], gold_hi[2], 255
            t = (x + y) / max(width + height, 1)
            r = _lerp(ink[0], ink2[0], t)
            g = _lerp(ink[1], ink2[1], t)
            b = _lerp(ink[2], ink2[2], t)
            # Angoli leggermente più chiari
            if x < 28 or y < 28 or x >= width - 28 or y >= height - 28:
                r = _lerp(r, gold_lo[0], 0.18)
                g = _lerp(g, gold_lo[1], 0.18)
                b = _lerp(b, gold_lo[2], 0.18)
            return r, g, b, 255

        # Separatori orizzontali sottili (tra finestre)
        for top in (art[1] - 2, type_line[1] - 2, rules[1] - 2, stats[1] - 2):
            if abs(y - top) <= 1 and margin <= x < width - margin:
                return gold[0], gold[1], gold[2], 230

        # Riempimento telaio interno (sottile)
        return ink2[0], ink2[1], ink2[2], 255

    return rgba_png(width, height, pixel)


def kor35_art_placeholder_png(width: int = 331, height: int = 210) -> bytes:
    """Placeholder art: gradiente freddo + croce guida."""
    cx, cy = width / 2, height / 2

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        if x < 1 or y < 1 or x >= width - 1 or y >= height - 1:
            return 90, 110, 150, 255
        t = y / max(height - 1, 1)
        r = _lerp(42, 70, t)
        g = _lerp(56, 88, t)
        b = _lerp(84, 120, t)
        # Croce centrale sottile
        if abs(x - cx) < 1.2 or abs(y - cy) < 1.2:
            return 120, 140, 180, 200
        return r, g, b, 255

    return rgba_png(width, height, pixel)


def kor35_plate_png(width: int = 331, height: int = 52, *, alpha: int = 210) -> bytes:
    """Piastra semi-opaca per title / type / rules (layer sotto il testo)."""

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        edge = x < 2 or y < 2 or x >= width - 2 or y >= height - 2
        if edge:
            return 40, 48, 64, min(255, alpha + 20)
        t = y / max(height - 1, 1)
        r = _lerp(24, 36, t)
        g = _lerp(30, 44, t)
        b = _lerp(46, 62, t)
        return r, g, b, alpha

    return rgba_png(width, height, pixel)


def build_kor35_style_text() -> str:
    """File `style` MSE — layout TCG leggibile."""
    return f"""mse version: 2.0.0
game: kor35
short name: KOR35 Standard
full name: KOR35 Standard Card Template
version: {KOR35_STYLE_VERSION}
creator: KOR35 Card Studio
card width: 375
card height: 523
card dpi: 300
card background: rgb(12,16,28)

styling field:
	type: boolean
	name: show_stats
	initial: true
	description: Show attack / health / initiative badges.

styling field:
	type: boolean
	name: show_lore
	initial: false
	description: Show flavor text under the rules box.

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
	title_plate:
		left: 22
		top: 18
		width: 331
		height: 52
		z index: 8
		render style: image
		image: images/title-plate.png

card style:
	type_plate:
		left: 22
		top: 292
		width: 331
		height: 28
		z index: 8
		render style: image
		image: images/type-plate.png

card style:
	rules_plate:
		left: 22
		top: 326
		width: 331
		height: 130
		z index: 8
		render style: image
		image: images/rules-plate.png

card style:
	art:
		left: 22
		top: 78
		width: 331
		height: 210
		z index: 5
		render style: image
		image: {{if card.image then card.image else "images/art-placeholder.png"}}

card style:
	energy:
		left: 26
		top: 24
		width: 40
		height: 40
		z index: 45
		alignment: middle center
		render style: symbol
		font:
			always symbol: true
			size: 28
			color: rgb(255,255,255)

card style:
	name:
		left: 72
		top: 24
		width: 210
		height: 40
		z index: 40
		alignment: middle left
		font:
			name: Georgia
			size: 20
			color: rgb(255,248,230)
			weight: bold

card style:
	cost:
		left: 290
		top: 24
		width: 54
		height: 40
		z index: 40
		alignment: middle center
		font:
			name: Arial
			size: 22
			color: rgb(250,204,21)
			weight: bold

card style:
	code:
		left: 286
		top: 8
		width: 70
		height: 14
		z index: 50
		alignment: middle right
		font:
			name: Consolas
			size: 10
			color: rgb(148,163,184)

card style:
	type:
		left: 30
		top: 294
		width: 220
		height: 24
		z index: 35
		alignment: middle left
		font:
			name: Arial
			size: 13
			color: rgb(186,230,253)
			weight: bold

card style:
	rarity:
		left: 250
		top: 294
		width: 96
		height: 24
		z index: 35
		alignment: middle right
		font:
			name: Arial
			size: 12
			color: rgb(226,232,240)

card style:
	rules:
		left: 30
		top: 334
		width: 315
		height: 110
		z index: 50
		alignment: top left
		font:
			name: Georgia
			size: 13
			color: rgb(241,245,249)

card style:
	lore:
		left: 30
		top: 438
		width: 315
		height: 18
		z index: 45
		visible: {{styling.show_lore}}
		alignment: top left
		font:
			name: Georgia
			size: 10
			color: rgb(148,163,184)

card style:
	attack:
		left: 40
		top: 470
		width: 70
		height: 32
		z index: 60
		visible: {{styling.show_stats}}
		alignment: middle center
		font:
			name: Arial
			size: 20
			color: rgb(254,226,226)
			weight: bold

card style:
	health:
		left: 152
		top: 470
		width: 70
		height: 32
		z index: 60
		visible: {{styling.show_stats}}
		alignment: middle center
		font:
			name: Arial
			size: 20
			color: rgb(220,252,231)
			weight: bold

card style:
	initiative:
		left: 264
		top: 470
		width: 70
		height: 32
		z index: 60
		visible: {{styling.show_stats}}
		alignment: middle center
		font:
			name: Arial
			size: 20
			color: rgb(219,234,254)
			weight: bold
"""


def build_kor35_mse_style_zip() -> bytes:
    """Zip in-memory pronto per `import_mse_style_package`."""
    style_text = build_kor35_style_text()
    frame = kor35_frame_png()
    art = kor35_art_placeholder_png()
    title_plate = kor35_plate_png(331, 52, alpha=200)
    type_plate = kor35_plate_png(331, 28, alpha=190)
    rules_plate = kor35_plate_png(331, 130, alpha=185)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("style", style_text)
        zf.writestr("images/frame.png", frame)
        zf.writestr("images/art-placeholder.png", art)
        zf.writestr("images/title-plate.png", title_plate)
        zf.writestr("images/type-plate.png", type_plate)
        zf.writestr("images/rules-plate.png", rules_plate)
    return buf.getvalue()
