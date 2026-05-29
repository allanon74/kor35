"""
Generazione PDF wiki per ManualePdf (WeasyPrint).
"""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from gestione_plot.models import ManualePdf, PaginaRegolamento
from gestione_plot.wiki_pdf_styles import resolve_manuale_stile

pdf_render_stile: ContextVar[dict | None] = ContextVar("pdf_render_stile", default=None)


def wiki_manual_export_dir() -> Path:
    return Path(settings.MEDIA_ROOT) / "wiki_exports"


def wiki_manual_latest_path(manuale: ManualePdf) -> Path:
    return wiki_manual_export_dir() / f"kor35-manuale-{manuale.slug}-latest.pdf"


def wiki_manual_legacy_latest_path() -> Path:
    """Percorso storico del singolo manuale monolitico."""
    return wiki_manual_export_dir() / "kor35-manuale-latest.pdf"


def get_current_pdf_stile() -> dict:
    stile = pdf_render_stile.get()
    if stile:
        return stile
    from gestione_plot.wiki_pdf_styles import merge_manuale_stile
    return merge_manuale_stile("giocatore", {})


def get_pages_for_manuale(manuale: ManualePdf, *, force_public: bool = True) -> list[PaginaRegolamento]:
    qs = (
        PaginaRegolamento.objects.filter(
            includi_in_pdf=True,
            manuali_pdf=manuale,
        )
        .select_related("parent")
        .prefetch_related("manuali_pdf")
        .order_by("parent__id", "ordine", "titolo")
    )
    if force_public:
        qs = qs.filter(public=True, visibile_solo_staff=False)
    return list(qs.distinct())


def _page_depth_in_manual(page: PaginaRegolamento, pages_by_pk: dict) -> int:
    depth = 0
    parent_id = page.parent_id
    while parent_id and parent_id in pages_by_pk:
        depth += 1
        parent_id = pages_by_pk[parent_id].parent_id
    return depth


def build_toc_entries(pages: list[PaginaRegolamento], rendered_pages: list[dict], max_depth: int) -> list[dict]:
    pages_by_pk = {p.pk: p for p in pages}
    entries = []
    for rp in rendered_pages:
        page = next((p for p in pages if p.slug == rp["slug"]), None)
        depth = _page_depth_in_manual(page, pages_by_pk) if page else 0
        if depth >= max_depth and not rp.get("solo_indice"):
            # Voce foglia oltre profondità: mostra come figlio dell'ultimo livello ammesso
            display_depth = max_depth - 1
        else:
            display_depth = min(depth, max_depth - 1)
        entries.append(
            {
                "titolo": rp["titolo"],
                "slug": rp["slug"],
                "depth": display_depth,
                "chapter_num": rp.get("chapter_num"),
                "solo_indice": rp.get("solo_indice"),
            }
        )
    return entries


def build_rendered_pages(pages, request, render_content_fn) -> list[dict]:
    rendered = []
    chapter_num = 0
    for page in pages:
        titolo = (page.pdf_titolo_capitolo or page.titolo or "").strip() or page.titolo
        body = ""
        if not page.pdf_solo_indice:
            chapter_num += 1
            body = render_content_fn(page.contenuto or "", request)
        rendered.append(
            {
                "titolo": titolo,
                "slug": page.slug,
                "rendered_content": body,
                "solo_indice": bool(page.pdf_solo_indice),
                "forza_nuova_pagina": bool(page.pdf_forza_nuova_pagina),
                "chapter_num": chapter_num if not page.pdf_solo_indice else None,
            }
        )
    return rendered


def resolve_manuale_cover_image_url(request, manuale: ManualePdf, pages: list[PaginaRegolamento], pdf_style: dict):
    if pdf_style.get("cover_text_only"):
        return None
    if manuale.copertina and not pdf_style.get("cover_minimal"):
        try:
            return request.build_absolute_uri(manuale.copertina.url)
        except Exception:
            pass
    if pdf_style.get("cover_minimal"):
        return None
    cover_source = next((p for p in pages if p.slug == "home" and getattr(p, "immagine", None)), None)
    if cover_source is None:
        cover_source = next((p for p in pages if getattr(p, "immagine", None)), None)
    if cover_source and cover_source.immagine:
        try:
            return request.build_absolute_uri(cover_source.immagine.url)
        except Exception:
            return None
    return None


def render_manuale_html(
    request,
    manuale: ManualePdf,
    pages: list[PaginaRegolamento],
    rendered_pages: list[dict],
    cover_image_url,
    pdf_style: dict | None = None,
) -> str:
    style = pdf_style or resolve_manuale_stile(manuale)
    toc_entries = build_toc_entries(pages, rendered_pages, style.get("indice_profondita", 2))
    context = {
        "manuale": manuale,
        "pages": pages,
        "rendered_pages": rendered_pages,
        "toc_entries": toc_entries,
        "pdf_style": style,
        "total_pages_count": len([p for p in rendered_pages if not p.get("solo_indice")]),
        "cover_image_url": cover_image_url,
        "generated_from_host": request.get_host(),
        "generated_at": timezone.localtime(),
    }
    return render_to_string("wiki/manuale_pdf.html", context)


def write_manuale_pdf_bytes(manuale: ManualePdf, pdf_bytes: bytes) -> Path:
    output_path = wiki_manual_latest_path(manuale)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)
    manuale.ultimo_generato_at = timezone.now()
    manuale.save(update_fields=["ultimo_generato_at"])
    if manuale.slug == "completo":
        legacy = wiki_manual_legacy_latest_path()
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_bytes(pdf_bytes)
    return output_path


def build_manuale_html_for_request(manuale: ManualePdf, request, *, render_content_fn, force_public: bool = True) -> str:
    pdf_style = resolve_manuale_stile(manuale)
    token = pdf_render_stile.set(pdf_style)
    try:
        pages = get_pages_for_manuale(manuale, force_public=force_public)
        if not pages:
            raise ValueError("Nessuna pagina wiki assegnata a questo manuale.")
        rendered_pages = build_rendered_pages(pages, request, render_content_fn)
        cover_image_url = resolve_manuale_cover_image_url(request, manuale, pages, pdf_style)
        return render_manuale_html(request, manuale, pages, rendered_pages, cover_image_url, pdf_style)
    finally:
        pdf_render_stile.reset(token)


def generate_manuale_pdf(manuale: ManualePdf, request, *, render_content_fn, force_public: bool = True) -> bytes:
    html_string = build_manuale_html_for_request(
        manuale, request, render_content_fn=render_content_fn, force_public=force_public
    )
    from weasyprint import HTML

    return HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()
