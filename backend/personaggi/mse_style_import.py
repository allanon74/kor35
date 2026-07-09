"""
Import utility per package MSE stylesheet (.mse-style / .zip).

Estrae TUTTI i file del package (grafici e non), costruisce manifest
e prova a derivare metadati base da file `style`.
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
import re
import zipfile

from django.conf import settings
from django.core.files.base import ContentFile


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}


@dataclass
class ImportedMseStyle:
    extracted_root: str
    assets_manifest: list[dict]
    parsed_meta: dict


def _classify_asset(rel: str, data: bytes) -> dict:
    sha = hashlib.sha256(data).hexdigest()
    ext = Path(rel).suffix.lower()
    mime = mimetypes.guess_type(rel)[0] or "application/octet-stream"
    is_binary = b"\x00" in data[:2048]
    asset_type = "image" if ext in IMAGE_EXTENSIONS else ("binary" if is_binary else "text")
    return {
        "path": rel,
        "size": len(data),
        "sha256": sha,
        "mime": mime,
        "asset_type": asset_type,
    }


def _sanitize_relpath(name: str) -> str | None:
    rel = name.replace("\\", "/").strip()
    if not rel or rel.endswith("/"):
        return None
    norm = os.path.normpath(rel).replace("\\", "/")
    if norm.startswith("../") or norm.startswith("/") or "/../" in f"/{norm}/":
        return None
    return norm


def _parse_style_metadata(style_text: str) -> dict:
    def _extract(pattern: str):
        m = re.search(pattern, style_text, flags=re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else ""

    short_name = _extract(r"^\s*short name\s*:\s*(.+)\s*$")
    full_name = _extract(r"^\s*full name\s*:\s*(.+)\s*$")
    game = _extract(r"^\s*game\s*:\s*(.+)\s*$")
    card_width = _extract(r"^\s*card width\s*:\s*(.+)\s*$")
    card_height = _extract(r"^\s*card height\s*:\s*(.+)\s*$")
    card_dpi = _extract(r"^\s*card dpi\s*:\s*(.+)\s*$")
    return {
        "short_name": short_name,
        "full_name": full_name,
        "game": game,
        "card_width_raw": card_width,
        "card_height_raw": card_height,
        "card_dpi_raw": card_dpi,
    }


def parse_generic_package_meta(package_type: str, data_file_text: str) -> dict:
    """
    Estrazione metadati leggeri da file root del package (game/style/include/locale/...).
    """
    def _extract(pattern: str):
        m = re.search(pattern, data_file_text, flags=re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else ""

    meta = {
        "package_type": package_type,
        "short_name": _extract(r"^\s*short name\s*:\s*(.+)\s*$"),
        "full_name": _extract(r"^\s*full name\s*:\s*(.+)\s*$"),
        "game": _extract(r"^\s*game\s*:\s*(.+)\s*$"),
        "version": _extract(r"^\s*version\s*:\s*(.+)\s*$"),
    }
    return {k: v for k, v in meta.items() if v}


def _safe_float(raw: str, default: float | None = None) -> float | None:
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def import_mse_style_package(*, template, upload_file) -> ImportedMseStyle:
    """
    Salva package originale, estrae file e popola metadati template.
    """
    upload_name = Path(upload_file.name or "style.zip").name
    package_name = f"{template.sync_id}_{upload_name}"
    template.mse_style_package.save(
        package_name,
        ContentFile(upload_file.read()),
        save=False,
    )

    package_abspath = Path(template.mse_style_package.path)
    extract_root_rel = f"card_studio/mse_styles_extracted/{template.sync_id}"
    extract_root_abs = Path(settings.MEDIA_ROOT) / extract_root_rel
    extract_root_abs.mkdir(parents=True, exist_ok=True)

    assets_manifest: list[dict] = []
    style_text = ""

    with zipfile.ZipFile(package_abspath, "r") as zf:
        for member in zf.infolist():
            rel = _sanitize_relpath(member.filename)
            if not rel:
                continue
            target = extract_root_abs / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            data = zf.read(member)
            with open(target, "wb") as out:
                out.write(data)

            assets_manifest.append(_classify_asset(rel, data))

            if rel.lower() == "style":
                try:
                    style_text = data.decode("utf-8", errors="replace")
                except Exception:
                    style_text = ""

    parsed_meta = _parse_style_metadata(style_text) if style_text else {}
    width = _safe_float(parsed_meta.get("card_width_raw", ""))
    height = _safe_float(parsed_meta.get("card_height_raw", ""))
    dpi = _safe_float(parsed_meta.get("card_dpi_raw", ""), 96.0)

    layout_spec = dict(template.layout_spec or {})
    layout_spec.setdefault("version", "1")
    if width:
        layout_spec["card_width_px"] = width
    if height:
        layout_spec["card_height_px"] = height
    if dpi:
        layout_spec["dpi"] = dpi

    template.layout_spec = layout_spec
    template.mse_style_riferimento = template.mse_style_package.name
    template.mse_assets_manifest = assets_manifest
    template.mse_extracted_root = extract_root_rel

    return ImportedMseStyle(
        extracted_root=extract_root_rel,
        assets_manifest=assets_manifest,
        parsed_meta=parsed_meta,
    )


def import_mse_style_directory(*, template, source_dir: str | Path) -> ImportedMseStyle:
    """
    Importa template da directory .mse-style già estratta (dataset locale).
    """
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise FileNotFoundError(str(source_dir))

    extract_root_rel = f"card_studio/mse_styles_extracted/{template.sync_id}"
    extract_root_abs = Path(settings.MEDIA_ROOT) / extract_root_rel
    extract_root_abs.mkdir(parents=True, exist_ok=True)

    assets_manifest: list[dict] = []
    style_text = ""

    for file_path in source_dir.rglob("*"):
        if not file_path.is_file():
            continue
        rel = _sanitize_relpath(str(file_path.relative_to(source_dir)))
        if not rel:
            continue
        target = extract_root_abs / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = file_path.read_bytes()
        target.write_bytes(data)
        assets_manifest.append(_classify_asset(rel, data))
        if rel.lower() == "style":
            try:
                style_text = data.decode("utf-8", errors="replace")
            except Exception:
                style_text = ""

    parsed_meta = _parse_style_metadata(style_text) if style_text else {}
    width = _safe_float(parsed_meta.get("card_width_raw", ""))
    height = _safe_float(parsed_meta.get("card_height_raw", ""))
    dpi = _safe_float(parsed_meta.get("card_dpi_raw", ""), 96.0)

    layout_spec = dict(template.layout_spec or {})
    layout_spec.setdefault("version", "1")
    if width:
        layout_spec["card_width_px"] = width
    if height:
        layout_spec["card_height_px"] = height
    if dpi:
        layout_spec["dpi"] = dpi

    template.layout_spec = layout_spec
    template.mse_style_riferimento = str(source_dir)
    template.mse_assets_manifest = assets_manifest
    template.mse_extracted_root = extract_root_rel

    return ImportedMseStyle(
        extracted_root=extract_root_rel,
        assets_manifest=assets_manifest,
        parsed_meta=parsed_meta,
    )


def import_generic_package_directory(
    *,
    source_dir: str | Path,
    package_type: str,
    destination_root_rel: str,
) -> tuple[str, list[dict], dict]:
    """
    Copia una directory package MSE (grafica/non grafica), ritorna root/manifest/meta.
    """
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise FileNotFoundError(str(source_dir))
    dest_abs = Path(settings.MEDIA_ROOT) / destination_root_rel
    dest_abs.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    root_data_name = {
        "mse-style": "style",
        "mse-game": "game",
        "mse-set": "set",
        "mse-symbol-font": "symbol font",
        "mse-export-template": "export-template",
        "mse-include": "include",
        "mse-locale": "locale",
    }.get(package_type, "")
    root_text = ""

    for file_path in source_dir.rglob("*"):
        if not file_path.is_file():
            continue
        rel = _sanitize_relpath(str(file_path.relative_to(source_dir)))
        if not rel:
            continue
        target = dest_abs / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = file_path.read_bytes()
        target.write_bytes(data)
        manifest.append(_classify_asset(rel, data))
        if root_data_name and rel.lower() == root_data_name.lower():
            root_text = data.decode("utf-8", errors="replace")

    parsed_meta = parse_generic_package_meta(package_type, root_text) if root_text else {}
    return destination_root_rel, manifest, parsed_meta
