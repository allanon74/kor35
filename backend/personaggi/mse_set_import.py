"""
Import `.mse-set` → EspansioneCarte + CartaCollezionabile (subset MSE, clean-room).
"""
from __future__ import annotations

import re
import uuid
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from personaggi.carte_set_codice import build_carta_codice
from personaggi.carte_collezionabili_models import (
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_PERSONAGGIO,
    CartaCollezionabile,
    EspansioneCarte,
)
from personaggi.carte_platform_models import (
    MSE_PACKAGE_SET,
    CarteGiocoDefinizione,
    CarteMsePackageImport,
    CarteStudioTemplate,
)
from personaggi.mse_style_import import (
    _classify_asset,
    _mse_line_indent,
    _sanitize_relpath,
    parse_generic_package_meta,
)


def _split_key_value_line(line: str):
    stripped = line.lstrip(" \t")
    if not stripped or ":" not in stripped:
        return None
    indent = _mse_line_indent(line)
    key, value = stripped.split(":", 1)
    return indent, key.strip(), key.strip().lower(), value.strip()


def parse_mse_set(set_text: str) -> dict:
    """Parser leggero file `set` MSE → set_info, cards, meta."""
    if not set_text:
        return {"version": "1", "set_info": {}, "styling": {}, "cards": [], "meta": {}}

    meta: dict = {}
    set_info: dict = {}
    styling: dict = {}
    cards: list[dict] = []
    keywords: list[dict] = []

    section: str | None = None
    current_card: dict | None = None
    current_style_name: str | None = None
    map_indent = 0

    for raw_line in set_text.splitlines():
        if not raw_line.strip():
            continue
        parsed = _split_key_value_line(raw_line.rstrip("\n\r"))
        if not parsed:
            continue
        indent, key_raw, key, value = parsed

        if indent == 0:
            section = None
            current_card = None
            current_style_name = None
            if key in {"mse version", "version"}:
                meta["mse_version"] = value
                continue
            if key == "game":
                meta["game"] = value
                continue
            if key == "stylesheet":
                meta["stylesheet"] = value
                continue
            if key in {"short name", "name", "full name"}:
                meta[key.replace(" ", "_")] = value
                continue
            if key == "set info":
                section = "set_info"
                continue
            if key == "styling":
                section = "styling"
                continue
            if key == "card":
                section = "card"
                current_card = {}
                cards.append(current_card)
                if value:
                    current_card["_inline"] = value
                continue
            if key == "keyword":
                section = "keyword"
                keywords.append({"name": value} if value else {})
                continue
            continue

        if section == "set_info" and indent >= 1:
            set_info[key_raw] = value
            continue

        if section == "styling" and indent >= 1:
            if indent == 1:
                current_style_name = key_raw
                styling.setdefault(current_style_name, {})
                continue
            if current_style_name and indent >= 2:
                styling[current_style_name][key_raw] = value
            continue

        if section == "card" and current_card is not None and indent >= 1:
            current_card[key_raw] = value
            continue

        if section == "keyword" and keywords and indent >= 1:
            keywords[-1][key_raw] = value

    return {
        "version": "1",
        "meta": meta,
        "set_info": set_info,
        "styling": styling,
        "cards": cards,
        "keywords": keywords,
    }


def parse_mse_symbol_font(font_text: str) -> dict:
    """Parser leggero file `symbol font` MSE → mappa code → image path."""
    if not font_text:
        return {"version": "1", "symbols": {}, "meta": {}}

    meta = parse_generic_package_meta("mse-symbol-font", font_text)
    symbols: dict[str, dict] = {}
    current: dict | None = None
    section: str | None = None

    for raw_line in font_text.splitlines():
        if not raw_line.strip():
            continue
        parsed = _split_key_value_line(raw_line.rstrip("\n\r"))
        if not parsed:
            continue
        indent, key_raw, key, value = parsed

        if indent == 0:
            section = None
            if key in {"symbol", "mana symbol"}:
                section = "symbol"
                current = {"code": value} if value else {}
                if current is not None:
                    code = current.get("code") or value
                    if code:
                        symbols[code] = current
                continue
            continue

        if section == "symbol" and current is not None and indent >= 1:
            if key in {"code", "symbol"}:
                current["code"] = value
                if value:
                    symbols[value] = current
            elif key == "image":
                current["image"] = value
            else:
                current[key_raw] = value

    cleaned = {k: v for k, v in symbols.items() if v.get("code")}
    return {"version": "1", "meta": meta, "symbols": cleaned}


def _norm_field(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")


def map_mse_card_to_kor35(card_fields: dict, *, codice_fallback: str = "") -> dict:
    """Mappa campi MSE set card → colonne CartaCollezionabile + mse_campi."""
    mapped = {
        "codice": "",
        "nome": "",
        "tipo": CARTA_TIPO_PERSONAGGIO,
        "energia": "MAR",
        "rarita": CARTA_RARITA_COMUNE,
        "costo_gioco": 0,
        "attacco": 0,
        "salute": 0,
        "iniziativa": 0,
        "testo_gioco": "",
        "testo_lore": "",
        "mse_campi": {},
    }
    alias = {
        "name": "nome",
        "card_name": "nome",
        "title": "nome",
        "code": "codice",
        "card_code": "codice",
        "rules": "testo_gioco",
        "rules_text": "testo_gioco",
        "rule_text": "testo_gioco",
        "text": "testo_gioco",
        "card_text": "testo_gioco",
        "lore": "testo_lore",
        "flavor": "testo_lore",
        "flavor_text": "testo_lore",
        "type": "tipo",
        "card_type": "tipo",
        "energy": "energia",
        "mana": "energia",
        "resource": "energia",
        "rarity": "rarita",
        "cost": "costo_gioco",
        "mana_cost": "costo_gioco",
        "attack": "attacco",
        "power": "attacco",
        "forza": "attacco",
        "health": "salute",
        "toughness": "salute",
        "robustezza": "salute",
        "initiative": "iniziativa",
        "iniziativa": "iniziativa",
    }
    numeric = {"costo_gioco", "attacco", "salute", "iniziativa"}

    for raw_key, raw_val in (card_fields or {}).items():
        if raw_key.startswith("_"):
            continue
        nk = _norm_field(raw_key)
        target = alias.get(nk)
        if target:
            if target in numeric:
                try:
                    mapped[target] = int(str(raw_val).strip() or 0)
                except ValueError:
                    mapped[target] = 0
            else:
                mapped[target] = str(raw_val or "")
        else:
            mapped["mse_campi"][nk] = raw_val

    if not mapped["codice"]:
        mapped["codice"] = codice_fallback or mapped["nome"][:32] or f"CARD-{uuid.uuid4().hex[:8].upper()}"
    if not mapped["nome"]:
        mapped["nome"] = mapped["codice"]
    return mapped


def _slugify(raw: str, fallback: str = "set") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (raw or "").lower()).strip("-")
    return (s or fallback)[:80]


def _find_template_for_stylesheet(campagna, gioco, stylesheet_name: str):
    if not stylesheet_name:
        return (
            CarteStudioTemplate.objects.filter(campagna=campagna, gioco_definizione=gioco, attivo=True)
            .order_by("-is_default_for_new_cards", "nome")
            .first()
        )
    slug_hint = _slugify(stylesheet_name.replace(".mse-style", ""))
    qs = CarteStudioTemplate.objects.filter(campagna=campagna, gioco_definizione=gioco, attivo=True)
    hit = qs.filter(slug__icontains=slug_hint).first()
    if hit:
        return hit
    hit = qs.filter(nome__icontains=stylesheet_name).first()
    return hit or qs.filter(is_default_for_new_cards=True).first() or qs.first()


@transaction.atomic
def import_mse_set_package(
    *,
    campagna,
    gioco: CarteGiocoDefinizione,
    upload_file,
    espansione_slug: str = "",
    espansione_nome: str = "",
    create_cards: bool = True,
    update_existing: bool = True,
) -> dict:
    """
    Importa package .mse-set/.zip: espansione + carte + registry package.
    """
    upload_name = Path(upload_file.name or "set.zip").name
    package_id = uuid.uuid4()
    extract_root_rel = f"card_studio/mse_packages/{campagna.slug}/mse-set/{package_id}"
    extract_root_abs = Path(settings.MEDIA_ROOT) / extract_root_rel
    extract_root_abs.mkdir(parents=True, exist_ok=True)

    set_text = ""
    manifest: list[dict] = []

    package_abspath = extract_root_abs / upload_name
    package_abspath.write_bytes(upload_file.read())

    if upload_name.lower().endswith(".zip") or zipfile.is_zipfile(package_abspath):
        with zipfile.ZipFile(package_abspath, "r") as zf:
            for member in zf.infolist():
                rel = _sanitize_relpath(member.filename)
                if not rel:
                    continue
                target = extract_root_abs / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                data = zf.read(member)
                target.write_bytes(data)
                manifest.append(_classify_asset(rel, data))
                if rel.lower() == "set":
                    set_text = data.decode("utf-8", errors="replace")
    else:
        data = package_abspath.read_bytes()
        manifest.append(_classify_asset(upload_name, data))
        set_text = data.decode("utf-8", errors="replace")

    parsed = parse_mse_set(set_text)
    meta = parsed.get("meta") or {}
    set_info = parsed.get("set_info") or {}

    title = (
        espansione_nome
        or meta.get("short_name")
        or meta.get("name")
        or meta.get("full_name")
        or set_info.get("title")
        or upload_name.rsplit(".", 1)[0]
    )
    slug = espansione_slug or _slugify(title)
    base_slug = slug
    idx = 2
    while EspansioneCarte.objects.filter(campagna=campagna, slug=slug).exclude(
        mse_set_riferimento=upload_name
    ).exists():
        slug = f"{base_slug}-{idx}"[:80]
        idx += 1

    template = _find_template_for_stylesheet(campagna, gioco, meta.get("stylesheet", ""))

    esp, esp_created = EspansioneCarte.objects.get_or_create(
        campagna=campagna,
        slug=slug,
        defaults={
            "nome": title[:120],
            "descrizione": set_info.get("description") or set_info.get("descrizione") or "",
            "gioco_definizione": gioco,
            "default_studio_template": template,
            "mse_set_riferimento": upload_name,
            "studio_set_spec": {
                "version": "1",
                "mse_set_fields": {_norm_field(k): v for k, v in set_info.items()},
                "styling": parsed.get("styling") or {},
                "meta": meta,
            },
            "attiva": True,
        },
    )
    if not esp_created:
        esp.nome = title[:120]
        esp.gioco_definizione = gioco
        if template:
            esp.default_studio_template = template
        esp.mse_set_riferimento = upload_name
        spec = dict(esp.studio_set_spec or {})
        spec.update(
            {
                "version": "1",
                "mse_set_fields": {_norm_field(k): v for k, v in set_info.items()},
                "styling": parsed.get("styling") or {},
                "meta": meta,
            }
        )
        esp.studio_set_spec = spec
        esp.save()

    cards_created = 0
    cards_updated = 0
    if create_cards:
        for i, card_raw in enumerate(parsed.get("cards") or []):
            mapped = map_mse_card_to_kor35(
                card_raw,
                codice_fallback=build_carta_codice(slug, i + 1),
            )
            codice = mapped["codice"]
            existing = CartaCollezionabile.objects.filter(campagna=campagna, codice=codice).first()
            if existing and not update_existing:
                continue
            payload = {
                "campagna": campagna,
                "espansione": esp,
                "codice": codice,
                "nome": mapped["nome"],
                "tipo": mapped["tipo"],
                "energia": mapped["energia"],
                "rarita": mapped["rarita"],
                "costo_gioco": mapped["costo_gioco"],
                "attacco": mapped["attacco"],
                "salute": mapped["salute"],
                "iniziativa": mapped["iniziativa"],
                "testo_gioco": mapped["testo_gioco"],
                "testo_lore": mapped["testo_lore"],
                "mse_campi": mapped["mse_campi"],
                "studio_template": template,
                "attiva": True,
                "ordine_set": i + 1,
            }
            if existing:
                for k, v in payload.items():
                    if k != "campagna":
                        setattr(existing, k, v)
                existing.save()
                cards_updated += 1
            else:
                CartaCollezionabile.objects.create(**payload)
                cards_created += 1

    parsed_meta = {**meta, "set_info": set_info, "card_count": len(parsed.get("cards") or [])}
    CarteMsePackageImport.objects.update_or_create(
        campagna=campagna,
        gioco_definizione=gioco,
        package_type=MSE_PACKAGE_SET,
        package_name=upload_name,
        defaults={
            "source_priority": 0,
            "extracted_root": extract_root_rel,
            "parsed_meta": parsed_meta,
            "imported": True,
        },
    )

    return {
        "espansione_id": str(esp.id),
        "espansione_slug": esp.slug,
        "espansione_created": esp_created,
        "cards_created": cards_created,
        "cards_updated": cards_updated,
        "card_count": len(parsed.get("cards") or []),
        "template_id": str(template.id) if template else None,
        "extracted_root": extract_root_rel,
    }
