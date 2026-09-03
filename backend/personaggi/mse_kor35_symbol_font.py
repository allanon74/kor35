"""
Font simboli MSE per le 7 Aure KOR35 (Sette Elegie).
Glifi fantasy procedurali: medaglione ornamentale + icona per aura, rune per i costi.
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
KOR35_SYMBOL_FONT_VERSION = "1.3"

# Colori allineati ad AMZ/ATE/AIN/AMA/ASA/APS/AAR (tests_carte_collezionabili).
KOR35_AURA_GLYPHS: dict[str, dict] = {
    CARTA_ENERGIA_MARZIALE: {
        "rgb": (96, 72, 255),
        "ring": (36, 24, 140),
        "accent": (180, 170, 255),
        "ink": (230, 228, 255),
    },
    CARTA_ENERGIA_TECNOLOGICA: {
        "rgb": (255, 244, 48),
        "ring": (150, 130, 12),
        "accent": (255, 252, 160),
        "ink": (48, 40, 8),
    },
    CARTA_ENERGIA_INNATA: {
        "rgb": (218, 168, 32),
        "ring": (110, 78, 10),
        "accent": (255, 210, 90),
        "ink": (48, 32, 6),
    },
    CARTA_ENERGIA_MAGICA: {
        "rgb": (186, 98, 255),
        "ring": (88, 28, 170),
        "accent": (230, 190, 255),
        "ink": (36, 12, 58),
    },
    CARTA_ENERGIA_SACRA: {
        "rgb": (255, 252, 248),
        "ring": (150, 160, 190),
        "accent": (255, 255, 255),
        "ink": (60, 68, 90),
    },
    CARTA_ENERGIA_PSIONICA: {
        "rgb": (248, 178, 255),
        "ring": (130, 60, 170),
        "accent": (255, 220, 255),
        "ink": (58, 20, 72),
    },
    CARTA_ENERGIA_ARCANA: {
        "rgb": (130, 255, 120),
        "ring": (36, 120, 44),
        "accent": (200, 255, 190),
        "ink": (16, 48, 20),
    },
}

KOR35_COST_DIGITS = tuple(str(d) for d in range(10))
KOR35_COST_GLYPH_META = {
    "rgb": (236, 190, 72),
    "ring": (120, 82, 18),
    "accent": (255, 230, 150),
    "ink": (48, 28, 6),
    "gem": (255, 248, 210),
}

# Cifre runiche 7×9 (più massicce e angolari del 5×7 base).
_RUNE_DIGIT_7x9: dict[str, list[str]] = {
    "0": [
        "0111110",
        "1100011",
        "1000001",
        "1000001",
        "1000001",
        "1000001",
        "1000001",
        "1100011",
        "0111110",
    ],
    "1": [
        "0011100",
        "0111100",
        "0011100",
        "0011100",
        "0011100",
        "0011100",
        "0011100",
        "0011100",
        "0111110",
    ],
    "2": [
        "0111110",
        "1000011",
        "0000011",
        "0000110",
        "0001100",
        "0011000",
        "0110000",
        "1100000",
        "1111111",
    ],
    "3": [
        "1111110",
        "0000011",
        "0000011",
        "0111110",
        "0000011",
        "0000011",
        "0000011",
        "1000011",
        "0111110",
    ],
    "4": [
        "0001100",
        "0011100",
        "0111100",
        "1101100",
        "1001100",
        "1111111",
        "0001100",
        "0001100",
        "0001100",
    ],
    "5": [
        "1111111",
        "1100000",
        "1100000",
        "1111110",
        "0000011",
        "0000011",
        "0000011",
        "1000011",
        "0111110",
    ],
    "6": [
        "0111110",
        "1100000",
        "1100000",
        "1111110",
        "1100011",
        "1100011",
        "1100011",
        "1100011",
        "0111110",
    ],
    "7": [
        "1111111",
        "0000011",
        "0000110",
        "0001100",
        "0011000",
        "0110000",
        "0110000",
        "0110000",
        "0110000",
    ],
    "8": [
        "0111110",
        "1100011",
        "1100011",
        "0111110",
        "1100011",
        "1100011",
        "1100011",
        "1100011",
        "0111110",
    ],
    "9": [
        "0111110",
        "1100011",
        "1100011",
        "1100011",
        "0111111",
        "0000011",
        "0000011",
        "0000010",
        "0111100",
    ],
}


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge0 == edge1:
        return 1.0 if x >= edge1 else 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _sd_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    denom = abx * abx + aby * aby
    if denom < 1e-9:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / denom))
    qx = ax + t * abx
    qy = ay + t * aby
    return math.hypot(px - qx, py - qy)


def _soft_bar(strength: float, half_thickness: float = 0.055) -> float:
    return _clamp01(_smoothstep(half_thickness, 0.0, half_thickness - strength))


def _soft_ring(r: float, r0: float, r1: float, feather: float = 0.04) -> float:
    outer = _smoothstep(r1 + feather, r1 - feather, r)
    inner = _smoothstep(r0 - feather, r0 + feather, r)
    return _clamp01(outer * inner)


def _rotate(nx: float, ny: float, angle: float) -> tuple[float, float]:
    c = math.cos(angle)
    s = math.sin(angle)
    return nx * c - ny * s, nx * s + ny * c


def _icon_mar(nx: float, ny: float) -> float:
    """Spada verticale."""
    blade = _soft_bar(abs(nx), 0.07) * _clamp01(_smoothstep(0.62, 0.48, ny)) * _clamp01(_smoothstep(-0.72, -0.55, ny))
    guard = _soft_bar(abs(ny + 0.08), 0.055) * _clamp01(_smoothstep(0.38, 0.22, abs(nx)))
    grip = _soft_bar(abs(nx), 0.05) * _clamp01(_smoothstep(0.72, 0.58, ny)) * _clamp01(_smoothstep(0.42, 0.55, ny))
    pommel = _clamp01(_smoothstep(0.11, 0.04, math.hypot(nx, ny - 0.78)))
    return max(blade, guard, grip, pommel)


def _icon_tec(nx: float, ny: float) -> float:
    """Ingranaggio runico."""
    r = math.hypot(nx, ny)
    angle = math.atan2(ny, nx)
    teeth = 0.52 + 0.11 * math.cos(8 * angle)
    gear = _soft_ring(r, 0.56, teeth, 0.035)
    hub = _clamp01(_smoothstep(0.24, 0.14, r))
    spoke_v = _soft_bar(abs(nx), 0.045) * _clamp01(_smoothstep(0.5, 0.35, abs(ny)))
    spoke_h = _soft_bar(abs(ny), 0.045) * _clamp01(_smoothstep(0.5, 0.35, abs(nx)))
    diag_a = _soft_bar(abs(nx - ny) / math.sqrt(2), 0.04) * _clamp01(_smoothstep(0.42, 0.28, r))
    diag_b = _soft_bar(abs(nx + ny) / math.sqrt(2), 0.04) * _clamp01(_smoothstep(0.42, 0.28, r))
    return max(gear, hub, spoke_v, spoke_h, diag_a, diag_b)


def _icon_inn(nx: float, ny: float) -> float:
    """Trifoglio / spirale vitale."""
    best = 0.0
    for i, ang in enumerate((-math.pi / 2, math.pi / 6, 5 * math.pi / 6)):
        lx, ly = _rotate(nx, ny - 0.05, -ang)
        leaf = _clamp01(_smoothstep(0.34, 0.18, (lx / 0.34) ** 2 + ((ly + 0.12) / 0.42) ** 2))
        vein = _soft_bar(abs(lx), 0.025) * _clamp01(_smoothstep(0.2, 0.05, ly)) * _clamp01(_smoothstep(-0.45, -0.25, ly))
        best = max(best, leaf, vein * 0.85)
    stem = _soft_bar(abs(nx), 0.04) * _clamp01(_smoothstep(0.55, 0.35, ny)) * _clamp01(_smoothstep(-0.05, 0.1, ny))
    return max(best, stem)


def _icon_mag(nx: float, ny: float) -> float:
    """Pentacolo arcano."""
    pts = []
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        pts.append((0.42 * math.cos(a), 0.42 * math.sin(a)))
    lines = [(0, 2), (2, 4), (4, 1), (1, 3), (3, 0)]
    best = 0.0
    for i, j in lines:
        ax, ay = pts[i]
        bx, by = pts[j]
        d = _sd_segment(nx, ny, ax, ay, bx, by)
        best = max(best, _soft_bar(d, 0.055))
    outer = _soft_ring(math.hypot(nx, ny), 0.36, 0.44, 0.03)
    core = _clamp01(_smoothstep(0.12, 0.04, math.hypot(nx, ny)))
    return max(best, outer * 0.6, core)


def _icon_sac(nx: float, ny: float) -> float:
    """Sole sacro a croce."""
    r = math.hypot(nx, ny)
    disc = _clamp01(_smoothstep(0.2, 0.1, r))
    cross_v = _soft_bar(abs(nx), 0.06) * _clamp01(_smoothstep(0.55, 0.35, abs(ny)))
    cross_h = _soft_bar(abs(ny), 0.06) * _clamp01(_smoothstep(0.55, 0.35, abs(nx)))
    rays = 0.0
    for i in range(8):
        ang = i * math.pi / 4
        lx, ly = _rotate(nx, ny, -ang)
        ray = _soft_bar(abs(lx), 0.045) * _clamp01(_smoothstep(-0.72, -0.38, ly)) * _clamp01(_smoothstep(-0.28, -0.5, ly))
        rays = max(rays, ray)
    halo = _soft_ring(r, 0.44, 0.5, 0.025)
    return max(disc, cross_v, cross_h, rays * 0.9, halo * 0.5)


def _icon_psi(nx: float, ny: float) -> float:
    """Occhio psionico."""
    eye = _clamp01(_smoothstep(1.0, 0.75, (nx / 0.52) ** 2 + (ny / 0.28) ** 2))
    lid = _clamp01(_smoothstep(0.18, 0.06, abs(ny) - 0.22 + 0.45 * nx**2))
    eye *= lid
    pupil = _clamp01(_smoothstep(0.14, 0.06, math.hypot(nx, ny)))
    iris = _soft_ring(math.hypot(nx, ny), 0.06, 0.13, 0.025)
    brow = _soft_bar(ny - 0.24 - 0.35 * nx**2, 0.035) * _clamp01(_smoothstep(0.45, 0.25, abs(nx)))
    wave = _soft_ring(math.hypot(nx, ny), 0.46, 0.5, 0.02) * 0.7
    return max(eye, pupil, iris, brow * 0.7, wave)


def _icon_arc(nx: float, ny: float) -> float:
    """Ramo runico / albero arcano."""
    trunk = _soft_bar(abs(nx), 0.05) * _clamp01(_smoothstep(0.72, 0.5, ny)) * _clamp01(_smoothstep(-0.72, -0.5, ny))
    branches = 0.0
    for side in (-1.0, 1.0):
        bx = side * 0.28
        by = 0.15
        d = _sd_segment(nx, ny, 0, -0.55, bx, by)
        branches = max(branches, _soft_bar(d, 0.05))
        d2 = _sd_segment(nx, ny, 0, 0.05, bx * 0.85, 0.55)
        branches = max(branches, _soft_bar(d2, 0.045))
    roots = _soft_bar(abs(ny + 0.62 - 0.25 * abs(nx)), 0.04) * _clamp01(_smoothstep(0.35, 0.15, abs(nx)))
    crown = _clamp01(_smoothstep(0.34, 0.2, math.hypot(nx, ny - 0.58)))
    return max(trunk, branches, roots, crown * 0.65)


_AURA_ICON_FN = {
    CARTA_ENERGIA_MARZIALE: _icon_mar,
    CARTA_ENERGIA_TECNOLOGICA: _icon_tec,
    CARTA_ENERGIA_INNATA: _icon_inn,
    CARTA_ENERGIA_MAGICA: _icon_mag,
    CARTA_ENERGIA_SACRA: _icon_sac,
    CARTA_ENERGIA_PSIONICA: _icon_psi,
    CARTA_ENERGIA_ARCANA: _icon_arc,
}


def _medallion_frame(nx: float, ny: float) -> tuple[float, float, float]:
    """Ritorna (body, outer_rim, inner_gem) maschere 0..1 per il medaglione."""
    r = math.hypot(nx, ny)
    angle = math.atan2(ny, nx)
    # Ottagono morbido
    oct_r = 0.5 / max(abs(math.cos(angle)), abs(math.sin(angle))) * 0.72
    body = _clamp01(_smoothstep(oct_r + 0.02, oct_r - 0.06, r))
    outer_rim = _soft_ring(r, oct_r - 0.1, oct_r - 0.02, 0.025)
    inner_rim = _soft_ring(r, 0.34, 0.4, 0.02)
    corner = 0.0
    for i in range(8):
        a = math.pi / 8 + i * math.pi / 4
        gx = 0.38 * math.cos(a)
        gy = 0.38 * math.sin(a)
        corner = max(corner, _clamp01(_smoothstep(0.07, 0.03, math.hypot(nx - gx, ny - gy))))
    return body, max(outer_rim, inner_rim * 0.8), corner


def _blend_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = _clamp01(t)
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _aura_glyph_png(code: str, meta: dict, *, size: int = KOR35_SYMBOL_GLYPH_PX) -> bytes:
    """Medaglione fantasy + icona aura."""
    fill = meta["rgb"]
    ring = meta["ring"]
    accent = meta["accent"]
    ink = meta["ink"]
    icon_fn = _AURA_ICON_FN.get(code, _icon_mag)
    cx = cy = (size - 1) / 2.0
    radius = size * 0.44

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        nx = (x - cx) / radius
        ny = (y - cy) / radius
        body, rim, gems = _medallion_frame(nx, ny)
        if body <= 0.01 and rim <= 0.01:
            return 0, 0, 0, 0

        icon = icon_fn(nx * 0.88, ny * 0.88)
        hl = max(0.0, 1.0 - (nx + ny * 0.65) / 1.3)
        base = _blend_rgb(ring, fill, 0.35 + 0.25 * hl)
        if rim > 0.05:
            col = _blend_rgb(accent, ring, 0.35)
            a = int(255 * min(1.0, rim))
            return col[0], col[1], col[2], a
        if gems > 0.5:
            a = int(255 * gems * 0.9)
            return accent[0], accent[1], accent[2], a
        if icon > 0.04:
            col = _blend_rgb(ink, accent, 0.15 + 0.25 * hl)
            a = int(255 * min(1.0, icon))
            return col[0], col[1], col[2], a
        col = _blend_rgb(base, fill, 0.4 + 0.35 * hl)
        a = int(255 * min(1.0, body))
        return col[0], col[1], col[2], a

    return rgba_png(size, size, pixel)


def _rune_digit_coverage(bitmap: list[str], x: float, y: float, scale: float, bx0: float, by0: float) -> float:
    lx = x - bx0
    ly = y - by0
    if lx < 0 or ly < 0:
        return 0.0
    col = int(lx / scale)
    row = int(ly / scale)
    fx = (lx / scale) - col
    fy = (ly / scale) - row
    bh = len(bitmap)
    bw = max(len(r) for r in bitmap)

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
    """Medaglione bronzo/dorato con cifra runica."""
    meta = KOR35_COST_GLYPH_META
    fill = meta["rgb"]
    ring = meta["ring"]
    accent = meta["accent"]
    ink = meta["ink"]
    gem = meta["gem"]
    bitmap = _RUNE_DIGIT_7x9.get(str(digit), _RUNE_DIGIT_7x9["0"])
    bh = len(bitmap)
    bw = max(len(r) for r in bitmap)
    cx = cy = (size - 1) / 2.0
    radius = size * 0.44
    scale = size * 0.075
    bx0 = cx - (bw * scale) / 2
    by0 = cy - (bh * scale) / 2 + scale * 0.1

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        nx = (x - cx) / radius
        ny = (y - cy) / radius
        body, rim, gems = _medallion_frame(nx, ny)
        rune = _rune_digit_coverage(bitmap, x + 0.25, y + 0.25, scale, bx0, by0)
        rune = max(
            rune,
            _rune_digit_coverage(bitmap, x + 0.75, y + 0.25, scale, bx0, by0),
            _rune_digit_coverage(bitmap, x + 0.25, y + 0.75, scale, bx0, by0),
            _rune_digit_coverage(bitmap, x + 0.75, y + 0.75, scale, bx0, by0),
        )
        if body <= 0.01 and rim <= 0.01:
            return 0, 0, 0, 0
        hl = max(0.0, 1.0 - (nx + ny * 0.6) / 1.25)
        if rune > 0.03:
            col = _blend_rgb(ink, accent, 0.2 * hl)
            return col[0], col[1], col[2], int(255 * min(1.0, rune))
        if gems > 0.5:
            return gem[0], gem[1], gem[2], int(255 * gems * 0.85)
        if rim > 0.05:
            col = _blend_rgb(accent, ring, 0.4)
            return col[0], col[1], col[2], int(255 * min(1.0, rim))
        col = _blend_rgb(ring, fill, 0.45 + 0.35 * hl)
        return col[0], col[1], col[2], int(255 * min(1.0, body))

    return rgba_png(size, size, pixel)


def build_kor35_symbol_font_text() -> str:
    lines = [
        "mse version: 2.0.0",
        "game: kor35",
        "short name: KOR35 Aure",
        "full name: KOR35 Sette Aure Symbol Font",
        f"version: {KOR35_SYMBOL_FONT_VERSION}",
        "creator: KOR35 Card Studio",
        "",
    ]
    for code in KOR35_AURA_GLYPHS:
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
            zf.writestr(f"symbols/{code.lower()}.png", _aura_glyph_png(code, meta))
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
        (sym_dir / f"{code.lower()}.png").write_bytes(_aura_glyph_png(code, meta))
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
