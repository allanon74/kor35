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


def _bool_mse(raw, default: bool = False) -> bool:
    if raw is None or raw == "":
        return default
    return str(raw).lower() not in {"false", "no", "0"}


def _mse_prop_value(raw: str) -> dict:
    """Valore proprietà stile: literal o script inline `{...}`."""
    s = (raw or "").strip()
    if len(s) >= 2 and s.startswith("{") and s.endswith("}"):
        return {"kind": "script", "expr": s[1:-1].strip()}
    return {"kind": "literal", "value": s}


def _mse_line_indent(line: str) -> int:
    """Livello indentazione MSE: un tab o 4 spazi = un livello."""
    level = 0
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\t":
            level += 1
            i += 1
        elif ch == " ":
            j = i
            while j < len(line) and line[j] == " ":
                j += 1
            spaces = j - i
            if spaces:
                level += max(1, spaces // 4)
                i = j
            else:
                break
        else:
            break
    return level


def _mse_split_key_value(line: str) -> tuple[int, str, str, str] | None:
    """Ritorna (indent, key_raw, key_lower, value) oppure None se non è riga chiave:valore."""
    stripped = line.lstrip(" \t")
    if not stripped or ":" not in stripped:
        return None
    indent = _mse_line_indent(line)
    key, value = stripped.split(":", 1)
    key_raw = key.strip()
    return indent, key_raw, key_raw.lower(), value.strip()


def parse_mse_style_spec(style_text: str) -> dict:
    """
    Parser leggero del file `style` MSE (.mse-style).
    Estrae card style, styling fields e metadati canvas per preview Card Studio.
    """
    if not style_text:
        return {"version": "1", "card_styles": {}, "styling_fields": [], "extra_card_styles": {}}

    meta = _parse_style_metadata(style_text)
    card_background = ""
    card_styles: dict[str, dict] = {}
    extra_card_styles: dict[str, dict] = {}
    styling_fields: list[dict] = []

    section: str | None = None
    current_field_name: str | None = None
    current_style: dict | None = None
    current_styling: dict | None = None
    nested_key: str | None = None
    nested_indent = 0
    script_target: dict | None = None
    script_prop: str | None = None
    script_indent = 0
    script_lines: list[str] = []

    def _style_bucket() -> dict:
        nonlocal current_style, current_field_name
        if current_style is None:
            current_style = {}
        if current_field_name:
            if section == "extra_card_style":
                extra_card_styles.setdefault(current_field_name, current_style)
            else:
                card_styles.setdefault(current_field_name, current_style)
        return current_style

    def _set_prop(target: dict, key: str, value: str):
        nonlocal nested_key, nested_indent, script_target, script_prop, script_lines
        norm = key.strip().lower().replace(" ", "_")
        if norm == "script" and not value:
            script_target = target
            script_prop = None
            script_lines = []
            nested_key = None
            return
        if script_target is not None and target is script_target and not script_prop:
            script_prop = norm
            script_lines = [value] if value else []
            return
        prop_val = _mse_prop_value(value)
        if not value and norm in {"font", "border", "background"}:
            target[norm] = target.get(norm) or {}
            nested_key = norm
            nested_indent = indent
            return
        if nested_key and target is _style_bucket() and indent > nested_indent:
            nested = _style_bucket().setdefault(nested_key, {})
            nested[norm] = prop_val
            return
        target[norm] = prop_val
        nested_key = None

    def _flush_script():
        nonlocal script_target, script_prop, script_lines
        if script_target is not None and script_prop:
            expr = "\n".join(script_lines).strip()
            script_target[script_prop] = {"kind": "script", "expr": expr}
        script_target = None
        script_prop = None
        script_lines = []

    for raw_line in style_text.splitlines():
        if script_target is not None and script_prop:
            line = raw_line.rstrip("\n\r")
            indent = _mse_line_indent(line)
            stripped = line.lstrip(" \t")
            if indent <= script_indent and stripped and ":" in stripped:
                _flush_script()
            elif stripped:
                script_lines.append(stripped)
                continue
            else:
                continue

        if not raw_line.strip():
            continue
        line = raw_line.rstrip("\n\r")
        parsed = _mse_split_key_value(line)
        if not parsed:
            continue
        indent, key_raw, key, value = parsed

        if indent == 0:
            _flush_script()
            nested_key = None
            current_field_name = None
            current_style = None
            current_styling = None
            if key == "card background":
                card_background = value
                section = None
                continue
            if key == "card style":
                section = "card_style"
                continue
            if key == "styling field":
                section = "styling_field"
                current_styling = {"choices": []}
                styling_fields.append(current_styling)
                continue
            if key == "extra card style":
                section = "extra_card_style"
                continue
            section = None
            continue

        if section == "styling_field" and current_styling is not None:
            if key == "choice":
                current_styling.setdefault("choices", []).append({"name": value} if value else {})
                continue
            norm = key.replace(" ", "_")
            current_styling[norm] = value
            if norm == "name" and value:
                current_styling["name"] = value
            continue

        if section in {"card_style", "extra_card_style"}:
            if indent == 1:
                _flush_script()
                nested_key = None
                current_field_name = key_raw.rstrip(":") if key_raw.endswith(":") else key_raw
                if value:
                    current_field_name = value
                current_style = {}
                _style_bucket()
                continue
            if current_field_name and indent >= 2:
                script_indent = indent
                _set_prop(_style_bucket(), key_raw, value)
                continue

    _flush_script()

    width = _safe_float(meta.get("card_width_raw", ""), 375.0) or 375.0
    height = _safe_float(meta.get("card_height_raw", ""), 523.0) or 523.0
    dpi = _safe_float(meta.get("card_dpi_raw", ""), 96.0) or 96.0

    cleaned_styling: list[dict] = []
    for f in styling_fields:
        if not f.get("name"):
            continue
        cleaned_styling.append(
            {
                "name": f.get("name"),
                "type": (f.get("type") or "text").lower(),
                "initial": f.get("initial", ""),
                "default": f.get("default", ""),
                "choices": [c for c in (f.get("choices") or []) if c.get("name")],
            }
        )

    return {
        "version": "1",
        "game": meta.get("game", ""),
        "card_size": {"width": width, "height": height, "dpi": dpi},
        "card_background": card_background or "white",
        "card_styles": card_styles,
        "extra_card_styles": extra_card_styles,
        "styling_fields": cleaned_styling,
    }


def _apply_parsed_style_to_layout(layout_spec: dict, style_text: str, parsed_meta: dict) -> dict:
    layout_spec = dict(layout_spec or {})
    layout_spec.setdefault("version", "1")
    width = _safe_float(parsed_meta.get("card_width_raw", ""))
    height = _safe_float(parsed_meta.get("card_height_raw", ""))
    dpi = _safe_float(parsed_meta.get("card_dpi_raw", ""), 96.0)
    if width:
        layout_spec["card_width_px"] = width
    if height:
        layout_spec["card_height_px"] = height
    if dpi:
        layout_spec["dpi"] = dpi
    if style_text:
        layout_spec["mse_v1"] = parse_mse_style_spec(style_text)
    return layout_spec


def parse_mse_game_spec(game_text: str) -> dict:
    """
    Parser leggero del file `game` MSE.
    Estrae principalmente card fields/set fields e opzioni di base utili al Card Editor.
    """
    if not game_text:
        return {"version": "1", "card_fields": [], "set_fields": []}

    card_fields: list[dict] = []
    set_fields: list[dict] = []
    pack_types: list[dict] = []
    pack_items: list[dict] = []
    keyword_modes: list[str] = []
    has_keywords = False
    card_list_color_script = ""
    current_field: dict | None = None
    current_choice: dict | None = None
    current_map_key: str | None = None
    map_indent = 0
    in_color_script = False
    color_script_lines: list[str] = []
    pack_section: str | None = None
    current_pack: dict | None = None
    current_pack_item: dict | None = None

    pack_scalar_keys = {"name", "select", "enabled", "selectable", "summary", "filter", "amount", "weight"}

    def _set_pack_scalar(target: dict, key: str, value: str):
        norm = key.strip().lower().replace(" ", "_")
        if norm == "filter":
            if value:
                target["filter"] = _mse_prop_value(value) if value.startswith("{") else {"kind": "script", "expr": value}
            return
        if norm in {"enabled", "selectable", "summary"}:
            target[norm] = _bool_mse(value, True)
            return
        if norm == "amount":
            target[norm] = _mse_prop_value(value) if value.startswith("{") else {"kind": "literal", "value": value or "1"}
            return
        if norm == "weight":
            target[norm] = _mse_prop_value(value) if value.startswith("{") else {"kind": "literal", "value": value or "1"}
            return
        target[norm] = value

    def _append_pack_item_ref(pack: dict, ref_name: str):
        nonlocal current_pack_item
        current_pack_item = {"name": ref_name, "amount": {"kind": "literal", "value": "1"}}
        pack.setdefault("items", []).append(current_pack_item)

    def _handle_pack_item_line(key_raw: str, key: str, value: str, indent: int):
        nonlocal current_pack_item
        if key == "item":
            if value:
                _append_pack_item_ref(current_pack, value)
            else:
                current_pack_item = {}
                current_pack.setdefault("items", []).append(current_pack_item)
            return True
        if current_pack_item is not None and indent >= 2:
            _set_pack_scalar(current_pack_item, key_raw, value)
            return True
        if indent == 1 and key in pack_scalar_keys:
            _set_pack_scalar(current_pack, key_raw, value)
            return True
        return False

    field_scalar_keys = {
        "name",
        "type",
        "editable",
        "identifying",
        "multi line",
        "default",
        "initial",
        "card list column",
        "card list width",
        "card list visible",
        "card list allow",
        "card list alignment",
        "show statistics",
        "description",
        "card list name",
        "match",
        "empty name",
        "required",
        "reqired",
    }

    for raw_line in game_text.splitlines():
        if not raw_line.strip():
            if in_color_script:
                color_script_lines.append("")
            continue
        line = raw_line.rstrip("\n\r")
        stripped = line.lstrip(" \t")
        indent = _mse_line_indent(line)
        if ":" not in stripped:
            if in_color_script:
                color_script_lines.append(stripped)
            continue
        key, value = stripped.split(":", 1)
        key_raw = key.strip()
        key = key_raw.lower()
        value = value.strip()

        if indent == 0:
            in_color_script = False
            current_choice = None
            current_map_key = None
            if key == "card field":
                current_field = {"choices": []}
                card_fields.append(current_field)
                continue
            if key == "set field":
                current_field = {"choices": []}
                set_fields.append(current_field)
                continue
            if key == "has keywords":
                has_keywords = _bool_mse(value, False)
                current_field = None
                continue
            if key == "card list color script":
                in_color_script = True
                color_script_lines = [value] if value else []
                current_field = None
                pack_section = None
                continue
            if key == "pack type":
                pack_section = "pack_type"
                current_pack = {"items": []}
                pack_types.append(current_pack)
                current_pack_item = None
                current_field = None
                in_color_script = False
                continue
            if key == "pack item":
                pack_section = "pack_item"
                current_pack_item = {}
                pack_items.append(current_pack_item)
                current_pack = None
                current_field = None
                in_color_script = False
                continue
            pack_section = None
            current_pack = None
            current_pack_item = None
            current_field = None
            continue

        if pack_section == "pack_type" and current_pack is not None:
            if _handle_pack_item_line(key_raw, key, value, indent):
                continue

        if pack_section == "pack_item" and current_pack_item is not None and indent >= 1:
            _set_pack_scalar(current_pack_item, key_raw, value)
            continue

        if in_color_script and current_field is None:
            color_script_lines.append(stripped)
            continue

        if current_field is None:
            if key == "keyword mode" and value:
                keyword_modes.append(value)
            continue

        if current_map_key and indent > map_indent:
            current_field.setdefault(current_map_key, {})[key] = value
            continue
        if current_map_key and indent <= map_indent:
            current_map_key = None

        if key == "choice":
            current_choice = {}
            current_field.setdefault("choices", []).append(current_choice)
            if value:
                current_choice["name"] = value
            continue

        if key == "choice colors":
            current_map_key = "choice_colors"
            map_indent = indent
            current_field.setdefault("choice_colors", {})
            if value:
                current_field["choice_colors"]["*"] = value
            continue
        if key == "choice colors cardlist":
            current_map_key = "choice_colors_cardlist"
            map_indent = indent
            current_field.setdefault("choice_colors_cardlist", {})
            if value:
                current_field["choice_colors_cardlist"]["*"] = value
            continue

        target = current_choice if (current_choice is not None and indent >= 2) else current_field
        if key in field_scalar_keys:
            normalized = key.replace(" ", "_")
            if normalized == "reqired":
                normalized = "required"
            target[normalized] = value

    card_list_color_script = "\n".join(color_script_lines).strip()

    def _clean(fields: list[dict]) -> list[dict]:
        cleaned: list[dict] = []
        for f in fields:
            if not f.get("name"):
                continue
            f_type = (f.get("type") or "text").lower()
            required_raw = f.get("required", f.get("reqired"))
            item = {
                "name": f.get("name"),
                "type": f_type,
                "editable": _bool_mse(f.get("editable"), True),
                "multi_line": _bool_mse(f.get("multi_line"), False),
                "identifying": _bool_mse(f.get("identifying"), False),
                "choices": [c for c in (f.get("choices") or []) if c.get("name")],
                "choice_colors": dict(f.get("choice_colors") or {}),
                "choice_colors_cardlist": dict(f.get("choice_colors_cardlist") or {}),
                "default": f.get("default", ""),
                "initial": f.get("initial", ""),
                "description": f.get("description", ""),
                "card_list_name": f.get("card_list_name", ""),
                "card_list_visible": _bool_mse(f.get("card_list_visible"), False),
                "card_list_allow": _bool_mse(f.get("card_list_allow"), True),
                "card_list_alignment": f.get("card_list_alignment", "left"),
                "card_list_column": _safe_int(f.get("card_list_column", 0), 0),
                "card_list_width": _safe_int(f.get("card_list_width", 100), 100),
                "show_statistics": _bool_mse(f.get("show_statistics"), True),
                "match": f.get("match", ""),
                "required": _bool_mse(required_raw, True),
                "empty_name": f.get("empty_name", "None"),
            }
            cleaned.append(item)
        return cleaned

    cleaned_pack_items = [p for p in pack_items if p.get("name")]
    cleaned_pack_types = [p for p in pack_types if p.get("name")]

    return {
        "version": "1",
        "has_keywords": has_keywords,
        "keyword_modes": keyword_modes,
        "card_list_color_script": card_list_color_script,
        "card_fields": _clean(card_fields),
        "set_fields": _clean(set_fields),
        "pack_types": cleaned_pack_types,
        "pack_items": cleaned_pack_items,
    }


def _safe_float(raw: str, default: float | None = None) -> float | None:
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _safe_int(raw, default: int = 0) -> int:
    try:
        return int(str(raw).strip())
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
    layout_spec = _apply_parsed_style_to_layout(dict(template.layout_spec or {}), style_text, parsed_meta)

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
    layout_spec = _apply_parsed_style_to_layout(dict(template.layout_spec or {}), style_text, parsed_meta)

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
    if package_type == "mse-symbol-font" and root_text:
        from personaggi.mse_set_import import parse_mse_symbol_font

        sf = parse_mse_symbol_font(root_text)
        parsed_meta = {**parsed_meta, "symbols": sf.get("symbols", {})}
    return destination_root_rel, manifest, parsed_meta
