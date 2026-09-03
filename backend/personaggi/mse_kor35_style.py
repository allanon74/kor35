"""
Genera package `.mse-style` KOR35 / Cronache delle Sette Elegie (clean-room).

Allineato a `mse_kor35_game_spec` e al regolamento (PG/OGG/LUO/EVT, 7 aure).
Layout TCG: art ampia, title bar, type line, rules, stats PG (FOR/ROB/INI).
Cornici colorate per aura; Terra (LUO) senza simbolo energia e senza stats.
"""
from __future__ import annotations

import io
import struct
import zlib
import zipfile
from typing import Callable

# Codici aura allineati a carte_collezionabili_models (niente import Django qui:
# il modulo deve restare usabile anche in SimpleTestCase / generatori offline).
CARTA_ENERGIA_MARZIALE = "MAR"
CARTA_ENERGIA_TECNOLOGICA = "TEC"
CARTA_ENERGIA_INNATA = "INN"
CARTA_ENERGIA_MAGICA = "MAG"
CARTA_ENERGIA_SACRA = "SAC"
CARTA_ENERGIA_PSIONICA = "PSI"
CARTA_ENERGIA_ARCANA = "ARC"

KOR35_TEMPLATE_SLUG = "kor35-standard"
KOR35_TEMPLATE_NAME = "Sette Elegie Standard"
KOR35_STYLE_GAME = "kor35"
KOR35_STYLE_VERSION = "3.2"

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

# Accenti cornice per aura (allineati a glyph font / game colors).
_AURA_FRAME_PALETTE: dict[str, dict[str, tuple[int, int, int]]] = {
    CARTA_ENERGIA_MARZIALE: {
        "ink": (14, 18, 48),
        "ink2": (28, 36, 90),
        "accent": (76, 54, 245),
        "accent_hi": (140, 130, 255),
    },
    CARTA_ENERGIA_TECNOLOGICA: {
        "ink": (36, 34, 8),
        "ink2": (58, 54, 14),
        "accent": (250, 246, 16),
        "accent_hi": (255, 252, 120),
    },
    CARTA_ENERGIA_INNATA: {
        "ink": (42, 28, 8),
        "ink2": (70, 46, 14),
        "accent": (199, 158, 11),
        "accent_hi": (240, 190, 70),
    },
    CARTA_ENERGIA_MAGICA: {
        "ink": (36, 12, 68),
        "ink2": (58, 22, 98),
        "accent": (168, 85, 247),
        "accent_hi": (216, 180, 254),
    },
    CARTA_ENERGIA_SACRA: {
        "ink": (36, 40, 52),
        "ink2": (58, 64, 82),
        "accent": (248, 248, 252),
        "accent_hi": (255, 255, 255),
    },
    CARTA_ENERGIA_PSIONICA: {
        "ink": (36, 16, 48),
        "ink2": (62, 28, 82),
        "accent": (239, 170, 255),
        "accent_hi": (250, 210, 255),
    },
    CARTA_ENERGIA_ARCANA: {
        "ink": (12, 36, 18),
        "ink2": (22, 58, 30),
        "accent": (146, 250, 136),
        "accent_hi": (190, 255, 180),
    },
    "neutral": {
        "ink": (18, 22, 32),
        "ink2": (28, 34, 48),
        "accent": (212, 175, 95),
        "accent_hi": (240, 214, 140),
    },
    "luo": {
        "ink": (12, 28, 20),
        "ink2": (22, 48, 34),
        "accent": (74, 222, 128),
        "accent_hi": (160, 240, 180),
    },
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


def kor35_frame_png(
    width: int = 375,
    height: int = 523,
    *,
    palette_key: str = "neutral",
    include_stats_window: bool = True,
) -> bytes:
    """
    Cornice TCG: bordo tinto + filetto accento, finestre title/art/type/rules(/stats)
    trasparenti (testo e arte vivono sotto come layer CSS).
    """
    pal = _AURA_FRAME_PALETTE.get(palette_key) or _AURA_FRAME_PALETTE["neutral"]
    ink = pal["ink"]
    ink2 = pal["ink2"]
    accent = pal["accent"]
    accent_hi = pal["accent_hi"]

    margin = 12
    art = (22, 78, 331, 210)
    title = (22, 18, 331, 52)
    type_line = (22, 292, 331, 28)
    rules = (22, 326, 331, 130 if include_stats_window else 162)
    stats = (22, 464, 331, 44)

    windows = [title, art, type_line, rules]
    if include_stats_window:
        windows.append(stats)

    def in_box(x: int, y: int, box: tuple[int, int, int, int]) -> bool:
        l, t, w, h = box
        return l <= x < l + w and t <= y < t + h

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        for box in windows:
            if in_box(x, y, box):
                return 0, 0, 0, 0

        if x < margin or y < margin or x >= width - margin or y >= height - margin:
            near_inner = (
                x == margin - 1
                or y == margin - 1
                or x == width - margin
                or y == height - margin
            )
            if near_inner:
                return accent_hi[0], accent_hi[1], accent_hi[2], 255
            t = (x + y) / max(width + height, 1)
            r = _lerp(ink[0], ink2[0], t)
            g = _lerp(ink[1], ink2[1], t)
            b = _lerp(ink[2], ink2[2], t)
            if x < 28 or y < 28 or x >= width - 28 or y >= height - 28:
                r = _lerp(r, accent[0], 0.42)
                g = _lerp(g, accent[1], 0.42)
                b = _lerp(b, accent[2], 0.42)
            return r, g, b, 255

        sep_tops = [art[1] - 2, type_line[1] - 2, rules[1] - 2]
        if include_stats_window:
            sep_tops.append(stats[1] - 2)
        for top in sep_tops:
            if abs(y - top) <= 1 and margin <= x < width - margin:
                return accent[0], accent[1], accent[2], 230

        return ink2[0], ink2[1], ink2[2], 255

    return rgba_png(width, height, pixel)


def kor35_art_placeholder_png(
    width: int = 331,
    height: int = 210,
    *,
    card_type: str = "",
) -> bytes:
    """
    Placeholder art per tipo carta:
    PG (blu), OGG (ambra), LUO (verde), EVT (rosa), default neutro.
    """
    palettes = {
        "PG": {"top": (36, 64, 120), "bot": (18, 32, 64), "accent": (120, 170, 240)},
        "OGG": {"top": (90, 70, 24), "bot": (48, 36, 12), "accent": (240, 200, 90)},
        "LUO": {"top": (28, 84, 56), "bot": (14, 42, 28), "accent": (120, 220, 160)},
        "EVT": {"top": (96, 40, 78), "bot": (48, 18, 40), "accent": (240, 130, 190)},
        "": {"top": (42, 56, 84), "bot": (28, 36, 52), "accent": (120, 140, 180)},
    }
    pal = palettes.get(str(card_type or "").upper(), palettes[""])
    cx, cy = width / 2, height / 2

    def in_ellipse(x: int, y: int, ex: float, ey: float, rx: float, ry: float) -> bool:
        return ((x - ex) / max(rx, 1)) ** 2 + ((y - ey) / max(ry, 1)) ** 2 <= 1.0

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        if x < 1 or y < 1 or x >= width - 1 or y >= height - 1:
            return pal["accent"][0], pal["accent"][1], pal["accent"][2], 255
        t = y / max(height - 1, 1)
        r = _lerp(pal["top"][0], pal["bot"][0], t)
        g = _lerp(pal["top"][1], pal["bot"][1], t)
        b = _lerp(pal["top"][2], pal["bot"][2], t)
        tip = str(card_type or "").upper()
        mark = False
        if tip == "PG":
            # testa + busto stilizzati
            mark = in_ellipse(x, y, cx, cy - 28, 22, 22) or in_ellipse(x, y, cx, cy + 28, 38, 48)
        elif tip == "OGG":
            # diamante
            mark = abs(x - cx) / 40 + abs(y - cy) / 55 <= 1.0
        elif tip == "LUO":
            # colline
            h1 = cy + 20 + 18 * ((x / max(width, 1)) ** 0.5)
            h2 = cy + 40 + 12 * abs((x - cx) / max(cx, 1))
            mark = y > h1 or y > h2
        elif tip == "EVT":
            # stella a 4 punte
            mark = abs(x - cx) * 2.2 + abs(y - cy) * 0.6 < 48 or abs(y - cy) * 2.2 + abs(x - cx) * 0.6 < 48
        else:
            mark = abs(x - cx) < 1.2 or abs(y - cy) < 1.2
        if mark:
            return pal["accent"][0], pal["accent"][1], pal["accent"][2], 220
        return r, g, b, 255

    return rgba_png(width, height, pixel)


def _art_select_script() -> str:
    """Placeholder diverso per tipo se manca card.image."""
    return (
        'if card.image then card.image else '
        'if card.type = "PG" then "images/art-pg.png" else '
        'if card.type = "OGG" then "images/art-ogg.png" else '
        'if card.type = "LUO" then "images/art-luo.png" else '
        'if card.type = "EVT" then "images/art-evt.png" else '
        '"images/art-placeholder.png"'
    )


def kor35_plate_png(
    width: int = 331,
    height: int = 52,
    *,
    alpha: int = 210,
    tint: tuple[int, int, int] = (24, 30, 46),
) -> bytes:
    """Piastra semi-opaca per title / type / rules (layer sotto il testo)."""

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        edge = x < 2 or y < 2 or x >= width - 2 or y >= height - 2
        if edge:
            return (
                min(255, tint[0] + 16),
                min(255, tint[1] + 16),
                min(255, tint[2] + 18),
                min(255, alpha + 20),
            )
        t = y / max(height - 1, 1)
        r = _lerp(tint[0], tint[0] + 12, t)
        g = _lerp(tint[1], tint[1] + 14, t)
        b = _lerp(tint[2], tint[2] + 16, t)
        return r, g, b, alpha

    return rgba_png(width, height, pixel)


def kor35_stat_badge_png(
    width: int = 70,
    height: int = 36,
    *,
    fill: tuple[int, int, int] = (40, 24, 28),
) -> bytes:
    """Badge arrotondato per FOR / ROB / INI."""

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        rx, ry = 8, 8
        cx = min(max(x, rx), width - 1 - rx)
        cy = min(max(y, ry), height - 1 - ry)
        dx = abs(x - cx)
        dy = abs(y - cy)
        if (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) > 1.05:
            return 0, 0, 0, 0
        edge = (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) > 0.72
        if edge:
            return min(255, fill[0] + 40), min(255, fill[1] + 40), min(255, fill[2] + 40), 240
        return fill[0], fill[1], fill[2], 220

    return rgba_png(width, height, pixel)


def _frame_select_script() -> str:
    """Script MSE: cornice terra oppure per codice aura."""
    parts = ['if card.type = "LUO" then "images/frame-luo.png"']
    for code in (
        CARTA_ENERGIA_MARZIALE,
        CARTA_ENERGIA_TECNOLOGICA,
        CARTA_ENERGIA_INNATA,
        CARTA_ENERGIA_MAGICA,
        CARTA_ENERGIA_SACRA,
        CARTA_ENERGIA_PSIONICA,
        CARTA_ENERGIA_ARCANA,
    ):
        parts.append(f'if card.energy = "{code}" then "images/frame-{code.lower()}.png"')
    parts.append('"images/frame-neutral.png"')
    expr = parts[-1]
    for p in reversed(parts[:-1]):
        expr = f"{p} else {expr}"
    return expr


def _type_label_script() -> str:
    return (
        'if card.type = "PG" then "Personaggio" else '
        'if card.type = "OGG" then "Oggetto" else '
        'if card.type = "LUO" then "Luogo" else '
        'if card.type = "EVT" then "Evento" else card.type'
    )


def _rarity_label_script() -> str:
    return (
        'if card.rarity = "COM" then "Comune" else '
        'if card.rarity = "NC" then "Non comune" else '
        'if card.rarity = "RAR" then "Rara" else '
        'if card.rarity = "EPI" then "Epica" else '
        'if card.rarity = "LEG" then "Leggendaria" else '
        'if card.rarity = "UNI" then "Unica" else card.rarity'
    )


def build_kor35_style_text() -> str:
    """File `style` MSE — layout Sette Elegie tipizzato."""
    frame_script = _frame_select_script()
    art_script = _art_select_script()
    type_label = _type_label_script()
    rarity_label = _rarity_label_script()
    is_pg = 'card.type = "PG"'
    not_luo = 'not (card.type = "LUO")'
    show_stats = f"styling.show_stats and ({is_pg})"

    return f"""mse version: 2.0.0
game: kor35
short name: Sette Elegie
full name: Cronache delle Sette Elegie — Template Standard
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
	description: Mostra FOR / ROB / INI (solo Personaggio).

styling field:
	type: boolean
	name: show_lore
	initial: false
	description: Mostra testo lore sotto il box regole.

card style:
	card_frame:
		left: 0
		top: 0
		width: 375
		height: 523
		z index: 100
		render style: image
		image: {{{frame_script}}}

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
		image: {{{art_script}}}

card style:
	energy:
		left: 24
		top: 22
		width: 44
		height: 44
		z index: 45
		visible: {{{not_luo}}}
		alignment: middle center
		render style: symbol
		font:
			always symbol: true
			size: 30
			color: rgb(255,255,255)
			symbol font: KOR35 Aure

card style:
	name:
		left: 68
		top: 22
		width: 218
		height: 44
		z index: 40
		alignment: middle left
		font:
			name: Beleren
			size: 19
			color: rgb(255,248,230)
			weight: bold

card style:
	cost:
		left: 288
		top: 22
		width: 48
		height: 44
		z index: 40
		visible: {{{not_luo}}}
		alignment: middle center
		render style: symbol
		font:
			always symbol: true
			size: 28
			color: rgb(255,255,255)
			symbol font: KOR35 Aure

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
		width: 200
		height: 24
		z index: 35
		alignment: middle left
		text: {{{type_label}}}
		font:
			name: Beleren
			size: 14
			color: rgb(186,230,253)
			weight: bold

card style:
	rarity:
		left: 230
		top: 294
		width: 116
		height: 24
		z index: 35
		alignment: middle right
		text: {{{rarity_label}}}
		font:
			name: Beleren
			size: 13
			color: rgb(250,204,21)

card style:
	rules:
		left: 30
		top: 334
		width: 315
		height: 110
		z index: 50
		alignment: top left
		render style: symbol
		font:
			name: MPlantin
			size: 13
			color: rgb(241,245,249)
			symbol font: KOR35 Aure

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
	stat_badge_attack:
		left: 40
		top: 468
		width: 70
		height: 36
		z index: 55
		visible: {{{show_stats}}}
		render style: image
		image: images/badge-attack.png

card style:
	stat_badge_health:
		left: 152
		top: 468
		width: 70
		height: 36
		z index: 55
		visible: {{{show_stats}}}
		render style: image
		image: images/badge-health.png

card style:
	stat_badge_initiative:
		left: 264
		top: 468
		width: 70
		height: 36
		z index: 55
		visible: {{{show_stats}}}
		render style: image
		image: images/badge-initiative.png

card style:
	attack_label:
		left: 40
		top: 471
		width: 70
		height: 11
		z index: 58
		visible: {{{show_stats}}}
		alignment: middle center
		text: FOR
		font:
			name: Arial
			size: 7
			color: rgb(254,202,202)
			weight: bold

card style:
	attack:
		left: 40
		top: 484
		width: 70
		height: 18
		z index: 60
		visible: {{{show_stats}}}
		alignment: middle center
		font:
			name: Arial
			size: 17
			color: rgb(254,226,226)
			weight: bold

card style:
	health_label:
		left: 152
		top: 471
		width: 70
		height: 11
		z index: 58
		visible: {{{show_stats}}}
		alignment: middle center
		text: ROB
		font:
			name: Arial
			size: 7
			color: rgb(187,247,208)
			weight: bold

card style:
	health:
		left: 152
		top: 484
		width: 70
		height: 18
		z index: 60
		visible: {{{show_stats}}}
		alignment: middle center
		font:
			name: Arial
			size: 17
			color: rgb(220,252,231)
			weight: bold

card style:
	initiative_label:
		left: 264
		top: 471
		width: 70
		height: 11
		z index: 58
		visible: {{{show_stats}}}
		alignment: middle center
		text: INI
		font:
			name: Arial
			size: 7
			color: rgb(191,219,254)
			weight: bold

card style:
	initiative:
		left: 264
		top: 484
		width: 70
		height: 18
		z index: 60
		visible: {{{show_stats}}}
		alignment: middle center
		font:
			name: Arial
			size: 17
			color: rgb(219,234,254)
			weight: bold
"""


def build_kor35_mse_style_zip() -> bytes:
    """Zip in-memory pronto per `import_mse_style_package`."""
    style_text = build_kor35_style_text()
    art = kor35_art_placeholder_png()
    title_plate = kor35_plate_png(331, 52, alpha=200)
    type_plate = kor35_plate_png(331, 28, alpha=190)
    rules_plate = kor35_plate_png(331, 130, alpha=185)
    badge_atk = kor35_stat_badge_png(fill=(72, 28, 36))
    badge_hp = kor35_stat_badge_png(fill=(24, 56, 40))
    badge_ini = kor35_stat_badge_png(fill=(28, 40, 72))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("style", style_text)
        zf.writestr("images/frame-neutral.png", kor35_frame_png(palette_key="neutral"))
        zf.writestr(
            "images/frame-luo.png",
            kor35_frame_png(palette_key="luo", include_stats_window=False),
        )
        # Alias legacy usato da versioni precedenti / fallback
        zf.writestr("images/frame.png", kor35_frame_png(palette_key="neutral"))
        for code in (
            CARTA_ENERGIA_MARZIALE,
            CARTA_ENERGIA_TECNOLOGICA,
            CARTA_ENERGIA_INNATA,
            CARTA_ENERGIA_MAGICA,
            CARTA_ENERGIA_SACRA,
            CARTA_ENERGIA_PSIONICA,
            CARTA_ENERGIA_ARCANA,
        ):
            zf.writestr(
                f"images/frame-{code.lower()}.png",
                kor35_frame_png(palette_key=code),
            )
        zf.writestr("images/art-placeholder.png", art)
        for tip in ("PG", "OGG", "LUO", "EVT"):
            zf.writestr(
                f"images/art-{tip.lower()}.png",
                kor35_art_placeholder_png(card_type=tip),
            )
        zf.writestr("images/title-plate.png", title_plate)
        zf.writestr("images/type-plate.png", type_plate)
        zf.writestr("images/rules-plate.png", rules_plate)
        zf.writestr("images/badge-attack.png", badge_atk)
        zf.writestr("images/badge-health.png", badge_hp)
        zf.writestr("images/badge-initiative.png", badge_ini)
    return buf.getvalue()
