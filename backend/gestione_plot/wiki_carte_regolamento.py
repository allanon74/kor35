"""
Sincronizza bozza regolamento carte da docs/wiki/carte/.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import mistune
from django.conf import settings
from mistune.plugins.table import table

from gestione_plot.models import PaginaRegolamento


def _resolve_wiki_carte_dir() -> Path:
    env_dir = os.environ.get("KOR35_WIKI_CARTE_DIR", "").strip()
    if env_dir:
        return Path(env_dir)
    docker_mount = Path("/app/wiki_carte_content")
    if docker_mount.is_dir() and (docker_mount / "manifest.json").is_file():
        return docker_mount
    monorepo = Path(settings.BASE_DIR).parent / "docs" / "wiki" / "carte"
    if monorepo.is_dir():
        return monorepo
    return docker_mount


WIKI_CARTE_DIR = _resolve_wiki_carte_dir()
MANIFEST_FILE = WIKI_CARTE_DIR / "manifest.json"

_markdown = mistune.create_markdown(plugins=[table])


def _enrich_html(html: str) -> str:
    if "<table>" not in html:
        return html
    html = html.replace("<table>", '<div class="wiki-table-scroll"><table data-table-style="grid">')
    return html.replace("</table>", "</table></div>")


def _markdown_to_html(md_text: str) -> str:
    return _enrich_html(_markdown(md_text.strip()))


def _load_manifest() -> dict:
    if not MANIFEST_FILE.is_file():
        raise FileNotFoundError(f"Manifest wiki carte mancante: {MANIFEST_FILE}")
    with MANIFEST_FILE.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if "section" not in data or "pages" not in data:
        raise ValueError(f"Manifest non valido: {MANIFEST_FILE}")
    return data


def _upsert_page(
    *,
    slug,
    titolo,
    contenuto,
    parent=None,
    ordine=0,
    force=False,
    visibile_solo_staff=False,
):
    defaults = {
        "titolo": titolo,
        "contenuto": contenuto,
        "parent": parent,
        "ordine": ordine,
        "public": True,
        "visibile_solo_staff": bool(visibile_solo_staff),
    }
    try:
        page = PaginaRegolamento.objects.get(slug=slug)
    except PaginaRegolamento.DoesNotExist:
        page = PaginaRegolamento.objects.create(slug=slug, **defaults)
        return page, "created"

    if not force:
        return page, "skipped"

    for key, value in defaults.items():
        setattr(page, key, value)
    page.save()
    return page, "updated"


def sync_wiki_carte_regolamento(*, force: bool = False) -> list[dict]:
    manifest = _load_manifest()
    section = manifest["section"]
    results: list[dict] = []

    intro = (section.get("intro") or "").strip()
    intro_html = _markdown_to_html(intro) if intro else ""
    section_body = intro_html
    if intro_html:
        section_body = (
            f"{intro_html}\n<p><em>Sezione regolamento carte — sorgente "
            f"<code>docs/wiki/carte/</code>.</em></p>"
        )

    parent, parent_action = _upsert_page(
        slug=section["slug"],
        titolo=section["titolo"],
        contenuto=section_body,
        parent=None,
        ordine=int(section.get("ordine", 850)),
        force=force,
    )
    results.append({"slug": parent.slug, "action": parent_action, "titolo": parent.titolo})

    for entry in manifest["pages"]:
        source_path = WIKI_CARTE_DIR / entry["source"]
        if not source_path.is_file():
            raise FileNotFoundError(f"Sorgente wiki carte mancante: {source_path}")
        md_text = source_path.read_text(encoding="utf-8")
        html = _markdown_to_html(md_text)
        footer = (
            '<hr><p><small>Fonte: <code>docs/wiki/carte/'
            f"{entry['source']}</code> — modificabile da Wiki; sync: <code>make wiki-carte-sync</code> o staff Carte → Config.</small></p>"
        )
        page, action = _upsert_page(
            slug=entry["slug"],
            titolo=entry["titolo"],
            contenuto=html + footer,
            parent=parent,
            ordine=int(entry.get("ordine", 0)),
            force=force,
            visibile_solo_staff=bool(entry.get("visibile_solo_staff", False)),
        )
        results.append({"slug": page.slug, "action": action, "titolo": page.titolo})

    return results


def get_wiki_carte_regolamento_info() -> dict:
    manifest_path = str(MANIFEST_FILE)
    if not MANIFEST_FILE.is_file():
        return {
            "wiki_carte_dir": str(WIKI_CARTE_DIR),
            "manifest_path": manifest_path,
            "manifest_ok": False,
            "section": None,
            "pages": [],
        }
    manifest = _load_manifest()
    section = manifest["section"]
    pages = [
        {
            "slug": entry["slug"],
            "titolo": entry["titolo"],
            "source": entry["source"],
            "ordine": int(entry.get("ordine", 0)),
        }
        for entry in manifest["pages"]
    ]
    return {
        "wiki_carte_dir": str(WIKI_CARTE_DIR),
        "manifest_path": manifest_path,
        "manifest_ok": True,
        "section": {"slug": section["slug"], "titolo": section["titolo"]},
        "pages": pages,
    }
