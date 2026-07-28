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

# Colori allineati ad AMZ/ATE/AIN/AMA/ASA/APS/AAR (tests_carte_collezionabili).
KOR35_AURA_GLYPHS: dict[str, dict] = {
    CARTA_ENERGIA_MARZIALE: {"rgb": (76, 54, 245), "ring": (40, 28, 160)},
    CARTA_ENERGIA_TECNOLOGICA: {"rgb": (250, 246, 16), "ring": (160, 150, 8)},
    CARTA_ENERGIA_INNATA: {"rgb": (199, 158, 11), "ring": (120, 90, 6)},
    CARTA_ENERGIA_MAGICA: {"rgb": (18, 18, 22), "ring": (90, 90, 100)},
    CARTA_ENERGIA_SACRA: {"rgb": (248, 248, 252), "ring": (120, 130, 150)},
    CARTA_ENERGIA_PSIONICA: {"rgb": (239, 170, 255), "ring": (140, 70, 180)},
    CARTA_ENERGIA_ARCANA: {"rgb": (146, 250, 136), "ring": (50, 140, 55)},
}


def _aura_glyph_png(
    fill: tuple[int, int, int],
    ring: tuple[int, int, int],
    *,
    size: int = 64,
) -> bytes:
    """Gemma circolare con bordo (simbolo aura per anteprima/PNG export)."""
    cx = cy = (size - 1) / 2.0
    outer = size * 0.46
    inner = size * 0.34
    ring_w = max(2.0, size * 0.06)

    def pixel(x: int, y: int) -> tuple[int, int, int, int]:
        dx = x - cx
        dy = y - cy
        dist = math.hypot(dx, dy)
        if dist > outer + 1.5:
            return 0, 0, 0, 0
        if dist > outer - ring_w:
            t = max(0.0, min(1.0, (outer - dist) / ring_w))
            a = int(255 * t)
            return ring[0], ring[1], ring[2], a
        if dist <= inner:
            # highlight toward top-left
            hl = max(0.0, 1.0 - (dx + dy * 0.6) / (inner * 1.4))
            r = min(255, int(fill[0] + hl * 40))
            g = min(255, int(fill[1] + hl * 40))
            b = min(255, int(fill[2] + hl * 40))
            return r, g, b, 255
        # mid ring between inner gem and outer border
        t = (dist - inner) / max(outer - inner, 1)
        r = int(fill[0] * (1 - t * 0.25) + ring[0] * t * 0.25)
        g = int(fill[1] * (1 - t * 0.25) + ring[1] * t * 0.25)
        b = int(fill[2] * (1 - t * 0.25) + ring[2] * t * 0.25)
        return r, g, b, 255

    return rgba_png(size, size, pixel)


def build_kor35_symbol_font_text() -> str:
    lines = [
        "mse version: 2.0.0",
        "game: kor35",
        "short name: KOR35 Aure",
        "full name: KOR35 Sette Aure Symbol Font",
        "version: 1.0",
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
    return "\n".join(lines)


def build_kor35_symbol_font_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("symbol font", build_kor35_symbol_font_text())
        for code, meta in KOR35_AURA_GLYPHS.items():
            png = _aura_glyph_png(meta["rgb"], meta["ring"])
            zf.writestr(f"symbols/{code.lower()}.png", png)
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
