"""
Font simboli MSE per le 7 Aure KOR35 (Sette Elegie).
Genera PNG + package `mse-symbol-font` installabile nel registry Card Studio.
"""
from __future__ import annotations

import io
import math
import zipfile
from pathlib import Path

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_ARCANA,
    CARTA_ENERGIA_INNATA,
    CARTA_ENERGIA_MAGICA,
    CARTA_ENERGIA_MARZIALE,
    CARTA_ENERGIA_PSIONICA,
    CARTA_ENERGIA_SACRA,
    CARTA_ENERGIA_TECNOLOGICA,
)
from personaggi.carte_platform_models import MSE_PACKAGE_SYMBOL_FONT
from personaggi.mse_kor35_style import rgba_png

KOR35_SYMBOL_FONT_NAME = "KOR35 Aure"
KOR35_SYMBOL_FONT_SLUG = "kor35-aure"
KOR35_SYMBOL_GLYPH_PX = 256

# Colori allineati ad AMZ/ATE/AIN/AMA/ASA/APS/AAR (tests_carte_collezionabili).
KOR35_AURA_GLYPHS: dict[str, dict] = {
    CARTA_ENERGIA_MARZIALE: {"rgb": (76, 54, 245), "ring": (40, 28, 160)},
    CARTA_ENERGIA_TECNOLOGICA: {"rgb": (250, 246, 16), "ring": (160, 150, 8)},
    CARTA_ENERGIA_INNATA: {"rgb": (199, 158, 11), "ring": (120, 90, 6)},
    CARTA_ENERGIA_MAGICA: {"rgb": (168, 85, 247), "ring": (88, 28, 180)},
    CARTA_ENERGIA_SACRA: {"rgb": (248, 248, 252), "ring": (120, 130, 150)},
    CARTA_ENERGIA_PSIONICA: {"rgb": (239, 170, 255), "ring": (140, 70, 180)},
    CARTA_ENERGIA_ARCANA: {"rgb": (146, 250, 136), "ring": (50, 140, 55)},
}

# Costi generici 0–9 per testo regole e costo carta ({0}…{9}).
KOR35_COST_DIGITS = tuple(str(d) for d in range(10))
KOR35_COST_GLYPH_META = {"rgb": (250, 204, 21), "ring": (180, 140, 20), "ink": (40, 28, 8)}

# Bitmap 5×7 per cifre (1 = pixel acceso).
_DIGIT_BITMAP_5x7: dict[str, list[str]] = {
    "0": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
}


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge0 == edge1:
        return 1.0 if x >= edge1 else 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def _aura_glyph_png(
    fill: tuple[int, int, int],
    ring: tuple[int, int, int],
    *,
    size: int = KOR35_SYMBOL_GLYPH_PX,
) -> bytes:
    """Gemma circolare con bordo (simbolo aura per anteprima/PNG export)."""
    cx = cy = (size - 1) / 2.0
    outer = size * 0.46
    inner = size * 0.34
    ring_w = max(3.0, size * 0.08)

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        dx = x - cx
        dy = y - cy
        dist = math.hypot(dx, dy)
        if dist > outer + 2.5:
            return 0, 0, 0, 0
        outer_a = _smoothstep(outer + 2.0, outer - ring_w, dist)
        if outer_a <= 0.0:
            return 0, 0, 0, 0
        if dist > outer - ring_w:
            a = int(255 * min(1.0, outer_a))
            return ring[0], ring[1], ring[2], a
        if dist <= inner:
            hl = max(0.0, 1.0 - (dx + dy * 0.6) / (inner * 1.4))
            r = min(255, int(fill[0] + hl * 40))
            g = min(255, int(fill[1] + hl * 40))
            b = min(255, int(fill[2] + hl * 40))
            return r, g, b, 255
        t = (dist - inner) / max(outer - inner, 1)
        r = int(fill[0] * (1 - t * 0.25) + ring[0] * t * 0.25)
        g = int(fill[1] * (1 - t * 0.25) + ring[1] * t * 0.25)
        b = int(fill[2] * (1 - t * 0.25) + ring[2] * t * 0.25)
        return r, g, b, 255

    return rgba_png(size, size, pixel)


def _digit_coverage(bitmap: list[str], x: float, y: float, scale: float, bx0: float, by0: float) -> float:
    lx = x - bx0
    ly = y - by0
    if lx < 0 or ly < 0:
        return 0.0
    col = int(lx / scale)
    row = int(ly / scale)
    fx = (lx / scale) - col
    fy = (ly / scale) - row
    bh = len(bitmap)
    bw = max(len(row) for row in bitmap)

    def cell_on(c: int, r: int) -> float:
        if r < 0 or r >= bh or c < 0 or c >= bw:
            return 0.0
        row_s = bitmap[r]
        if c >= len(row_s):
            return 0.0
        return 1.0 if row_s[c] == "1" else 0.0

    v00 = cell_on(col, row)
    v10 = cell_on(col + 1, row)
    v01 = cell_on(col, row + 1)
    v11 = cell_on(col + 1, row + 1)
    return (1 - fx) * (1 - fy) * v00 + fx * (1 - fy) * v10 + (1 - fx) * fy * v01 + fx * fy * v11


def _cost_digit_png(digit: str, *, size: int = KOR35_SYMBOL_GLYPH_PX) -> bytes:
    """Simbolo costo generico (cerchio dorato + cifra antialiased)."""
    meta = KOR35_COST_GLYPH_META
    fill = meta["rgb"]
    ring = meta["ring"]
    ink = meta["ink"]
    cx = cy = (size - 1) / 2.0
    outer = size * 0.46
    inner = size * 0.34
    ring_w = max(3.0, size * 0.08)
    bitmap = _DIGIT_BITMAP_5x7.get(str(digit), _DIGIT_BITMAP_5x7["0"])
    bh = len(bitmap)
    bw = max(len(row) for row in bitmap)
    scale = size * 0.09
    bx0 = cx - (bw * scale) / 2
    by0 = cy - (bh * scale) / 2 + scale * 0.15

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        digit_a = _digit_coverage(bitmap, x + 0.25, y + 0.25, scale, bx0, by0)
        digit_a = max(
            digit_a,
            _digit_coverage(bitmap, x + 0.75, y + 0.25, scale, bx0, by0),
            _digit_coverage(bitmap, x + 0.25, y + 0.75, scale, bx0, by0),
            _digit_coverage(bitmap, x + 0.75, y + 0.75, scale, bx0, by0),
        )
        if digit_a > 0.02:
            a = int(255 * min(1.0, digit_a))
            return ink[0], ink[1], ink[2], a
        dx = x - cx
        dy = y - cy
        dist = math.hypot(dx, dy)
        if dist > outer + 2.5:
            return 0, 0, 0, 0
        if dist > outer - ring_w:
            t = _smoothstep(outer + 2.0, outer - ring_w, dist)
            return ring[0], ring[1], ring[2], int(255 * min(1.0, t))
        if dist <= inner:
            hl = max(0.0, 1.0 - (dx + dy * 0.6) / (inner * 1.4))
            r = min(255, int(fill[0] + hl * 35))
            g = min(255, int(fill[1] + hl * 35))
            b = min(255, int(fill[2] + hl * 20))
            return r, g, b, 255
        t = (dist - inner) / max(outer - inner, 1)
        r = int(fill[0] * (1 - t * 0.2) + ring[0] * t * 0.2)
        g = int(fill[1] * (1 - t * 0.2) + ring[1] * t * 0.2)
        b = int(fill[2] * (1 - t * 0.2) + ring[2] * t * 0.2)
        return r, g, b, 255

    return rgba_png(size, size, pixel)


def build_kor35_symbol_font_text() -> str:
    lines = [
        "mse version: 2.0.0",
        "game: kor35",
        "short name: KOR35 Aure",
        "full name: KOR35 Sette Aure Symbol Font",
        "version: 1.2",
        "creator: KOR35 Card Studio",
        "",
    ]
    for code, meta in KOR35_AURA_GLYPHS.items():
        token = f"{{{code}}}"
        fname = code.lower()
        lines.extend(
            [
                "symbol:",
                f"    code: {token}",
                f"    image: symbols/{fname}.png",
                "",
            ]
        )
    for digit in KOR35_COST_DIGITS:
        token = f"{{{digit}}}"
        lines.extend(
            [
                "symbol:",
                f"    code: {token}",
                f"    image: symbols/cost-{digit}.png",
                "",
            ]
        )
    return "\n".join(lines)


def build_kor35_symbol_font_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("symbol font", build_kor35_symbol_font_text())
        for code, meta in KOR35_AURA_GLYPHS.items():
            png = _aura_glyph_png(meta["rgb"], meta["ring"])
            zf.writestr(f"symbols/{code.lower()}.png", png)
        for digit in KOR35_COST_DIGITS:
            zf.writestr(f"symbols/cost-{digit}.png", _cost_digit_png(digit))
    return buf.getvalue()


def write_kor35_symbol_font_directory(target_dir: str | Path) -> Path:
    """Scrive package su disco (per import_generic_package_directory)."""
    root = Path(target_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "symbol font").write_text(build_kor35_symbol_font_text(), encoding="utf-8")
    sym_dir = root / "symbols"
    sym_dir.mkdir(exist_ok=True)
    for code, meta in KOR35_AURA_GLYPHS.items():
        (sym_dir / f"{code.lower()}.png").write_bytes(_aura_glyph_png(meta["rgb"], meta["ring"]))
    for digit in KOR35_COST_DIGITS:
        (sym_dir / f"cost-{digit}.png").write_bytes(_cost_digit_png(digit))
    return root


def install_kor35_aura_symbol_font(
    *,
    campagna,
    gioco,
    dry_run: bool = False,
):
    """
    Registra il font simboli 7 Aure nel DB (CarteMsePackageImport).
    Ritorna (package, created).
    """
    from personaggi.carte_platform_models import CarteMsePackageImport
    from personaggi.mse_style_import import import_generic_package_directory
    import tempfile

    dest_rel = f"card_studio/mse_packages/{campagna.slug}/mse-symbol-font/{KOR35_SYMBOL_FONT_SLUG}"

    if dry_run:
        return None, False

    with tempfile.TemporaryDirectory(prefix="kor35-aure-") as tmp:
        write_kor35_symbol_font_directory(tmp)
        extracted_root, manifest, parsed_meta = import_generic_package_directory(
            source_dir=tmp,
            package_type=MSE_PACKAGE_SYMBOL_FONT,
            destination_root_rel=dest_rel,
        )

    obj, created = CarteMsePackageImport.objects.update_or_create(
        campagna=campagna,
        package_type=MSE_PACKAGE_SYMBOL_FONT,
        package_name=KOR35_SYMBOL_FONT_NAME,
        defaults={
            "gioco_definizione": gioco,
            "source_priority": 1,
            "source_root": "kor35-generated",
            "source_path": KOR35_SYMBOL_FONT_SLUG,
            "extracted_root": extracted_root,
            "parsed_meta": parsed_meta,
            "assets_manifest": manifest,
            "imported": True,
        },
    )
    return obj, created
