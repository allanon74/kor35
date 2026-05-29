"""
Servizi Fase 3: changelog generazioni, batch job, diagnostica, export ZIP.
"""

from __future__ import annotations

import logging
import threading
import time
import zipfile
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.test import RequestFactory
from django.utils import timezone

from gestione_plot.models import ManualePdf, ManualePdfBatchJob, ManualePdfGenerazione, PaginaRegolamento
from gestione_plot.wiki_pdf import (
    generate_manuale_pdf,
    get_pages_for_manuale,
    wiki_manual_export_dir,
    wiki_manual_latest_path,
    write_manuale_pdf_bytes,
)
from gestione_plot.wiki_pdf_styles import resolve_manuale_stile

logger = logging.getLogger(__name__)

BUNDLE_ZIP_NAME = "kor35-manuali-bundle-latest.zip"


def make_pdf_request(http_host: str):
    """Request minimale per WeasyPrint (manage.py / batch senza HTTP reale)."""
    rf = RequestFactory()
    request = rf.get("/api/plot/api/wiki/manuale.pdf")
    host = (http_host or "localhost").replace("https://", "").replace("http://", "").strip("/")
    request.META["HTTP_HOST"] = host.split("/")[0] if host else "localhost"
    return request


def _triggered_by_email_from_request(request) -> str:
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return (getattr(user, "email", None) or getattr(user, "username", None) or "").strip()
    return ""


def _counts_for_manuale(manuale: ManualePdf) -> tuple[int, int]:
    pages = get_pages_for_manuale(manuale, force_public=True)
    capitoli = sum(1 for p in pages if not p.pdf_solo_indice)
    return len(pages), capitoli


def esegui_generazione_manuale(
    manuale: ManualePdf,
    request,
    render_content_fn,
    *,
    triggered_by_email: str = "",
) -> ManualePdfGenerazione:
    """Genera PDF, aggiorna snapshot e registra changelog."""
    started = time.monotonic()
    pagine_count, capitoli_count = _counts_for_manuale(manuale)
    log = ManualePdfGenerazione(
        manuale=manuale,
        triggered_by_email=triggered_by_email or "",
        stile_preset=manuale.stile_preset or "",
        stile_snapshot=resolve_manuale_stile(manuale),
        pagine_count=pagine_count,
        capitoli_count=capitoli_count,
    )
    try:
        if pagine_count == 0:
            raise ValueError("Nessuna pagina wiki assegnata a questo manuale.")
        pdf_bytes = generate_manuale_pdf(
            manuale,
            request,
            render_content_fn=render_content_fn,
            force_public=True,
        )
        output_path = write_manuale_pdf_bytes(manuale, pdf_bytes)
        rel = output_path.relative_to(Path(settings.MEDIA_ROOT))
        log.success = True
        log.file_path = str(rel)
        log.file_size_bytes = len(pdf_bytes)
    except Exception as exc:
        log.success = False
        log.error_message = str(exc)[:2000]
        raise
    finally:
        log.durata_ms = int((time.monotonic() - started) * 1000)
        log.save()
    return log


def compute_wiki_pdf_diagnostica() -> dict:
    """Report pagine wiki vs manuali PDF per lo staff."""
    manuali = list(ManualePdf.objects.all().order_by("ordine", "titolo"))
    manuali_by_id = {m.pk: m for m in manuali}

    incluse_senza_manuale = []
    flag_incluso_ma_non_assegnato = []
    in_manuale_non_pubbliche = []
    pubbliche_con_contenuto_non_incluse = []

    for pagina in PaginaRegolamento.objects.prefetch_related("manuali_pdf").order_by("titolo"):
        manuali_ids = list(pagina.manuali_pdf.values_list("pk", flat=True))
        ha_contenuto = bool((pagina.contenuto or "").strip())

        if pagina.includi_in_pdf and not manuali_ids:
            incluse_senza_manuale.append(_pagina_diag(pagina, manuali_by_id))

        if manuali_ids and not pagina.includi_in_pdf:
            flag_incluso_ma_non_assegnato.append(_pagina_diag(pagina, manuali_by_id, manuali_ids))

        if manuali_ids and (not pagina.public or pagina.visibile_solo_staff):
            in_manuale_non_pubbliche.append(_pagina_diag(pagina, manuali_by_id, manuali_ids))

        if (
            pagina.public
            and not pagina.visibile_solo_staff
            and ha_contenuto
            and not pagina.includi_in_pdf
        ):
            pubbliche_con_contenuto_non_incluse.append(_pagina_diag(pagina, manuali_by_id))

    manuali_senza_pagine = []
    for manuale in manuali:
        n = manuale.pagine.filter(includi_in_pdf=True, public=True, visibile_solo_staff=False).count()
        if n == 0:
            manuali_senza_pagine.append({"slug": manuale.slug, "titolo": manuale.titolo})

    return {
        "manuali_count": len(manuali),
        "incluse_senza_manuale": incluse_senza_manuale,
        "flag_incluso_ma_non_assegnato": flag_incluso_ma_non_assegnato,
        "in_manuale_non_pubbliche": in_manuale_non_pubbliche,
        "pubbliche_con_contenuto_non_incluse": pubbliche_con_contenuto_non_incluse[:80],
        "pubbliche_non_incluse_oltre_limite": max(0, len(pubbliche_con_contenuto_non_incluse) - 80),
        "manuali_senza_pagine": manuali_senza_pagine,
        "has_warnings": bool(
            incluse_senza_manuale
            or flag_incluso_ma_non_assegnato
            or in_manuale_non_pubbliche
            or manuali_senza_pagine
        ),
    }


def _pagina_diag(pagina, manuali_by_id, manuali_ids=None):
    ids = manuali_ids if manuali_ids is not None else list(pagina.manuali_pdf.values_list("pk", flat=True))
    return {
        "id": pagina.pk,
        "titolo": pagina.titolo,
        "slug": pagina.slug,
        "includi_in_pdf": pagina.includi_in_pdf,
        "public": pagina.public,
        "visibile_solo_staff": pagina.visibile_solo_staff,
        "manuali": [{"slug": manuali_by_id[mid].slug, "titolo": manuali_by_id[mid].titolo} for mid in ids if mid in manuali_by_id],
    }


def build_manuali_zip_bundle() -> Path:
    """ZIP con tutti i PDF latest dei manuali attivi che esistono su disco."""
    export_dir = wiki_manual_export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    out_path = export_dir / BUNDLE_ZIP_NAME
    added = 0
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for manuale in ManualePdf.objects.filter(attivo=True).order_by("ordine", "titolo"):
            pdf_path = wiki_manual_latest_path(manuale)
            if pdf_path.exists():
                zf.write(pdf_path, arcname=f"kor35-manuale-{manuale.slug}.pdf")
                added += 1
    if added == 0:
        raise ValueError("Nessun PDF generato disponibile per l'export ZIP.")
    return out_path


def process_batch_job(job_id: int, http_host: str, render_content_fn) -> None:
    job = ManualePdfBatchJob.objects.filter(pk=job_id).first()
    if not job:
        return
    job.status = ManualePdfBatchJob.STATUS_RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "updated_at"])

    request = make_pdf_request(http_host)
    results = []
    try:
        for manuale in ManualePdf.objects.filter(attivo=True).order_by("ordine", "titolo"):
            entry = {"slug": manuale.slug, "titolo": manuale.titolo, "ok": False}
            try:
                log = esegui_generazione_manuale(
                    manuale,
                    request,
                    render_content_fn,
                    triggered_by_email=job.triggered_by_email,
                )
                entry["ok"] = True
                entry["generazione_id"] = log.pk
                entry["file_size_bytes"] = log.file_size_bytes
            except Exception as exc:
                entry["error"] = str(exc)[:500]
                logger.warning("Batch PDF fallito per %s: %s", manuale.slug, exc)
            results.append(entry)

        ok_count = sum(1 for r in results if r.get("ok"))
        if ok_count == len(results):
            job.status = ManualePdfBatchJob.STATUS_COMPLETED
        elif ok_count == 0:
            job.status = ManualePdfBatchJob.STATUS_FAILED
            job.error_message = "Nessun manuale generato con successo."
        else:
            job.status = ManualePdfBatchJob.STATUS_PARTIAL
        job.results = results
    except Exception as exc:
        logger.exception("Job batch PDF %s fallito", job_id)
        job.status = ManualePdfBatchJob.STATUS_FAILED
        job.error_message = str(exc)[:2000]
    finally:
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "results", "error_message", "finished_at", "updated_at"])


def enqueue_batch_job(job: ManualePdfBatchJob, http_host: str, render_content_fn) -> None:
    """Avvia batch in thread daemon (dev/single-worker); in prod preferire manage.py."""

    def _worker():
        connection.close()
        try:
            process_batch_job(job.pk, http_host, render_content_fn)
        except Exception:
            logger.exception("Thread batch PDF job %s", job.pk)
            ManualePdfBatchJob.objects.filter(pk=job.pk).update(
                status=ManualePdfBatchJob.STATUS_FAILED,
                finished_at=timezone.now(),
                error_message="Errore imprevisto nel thread batch.",
            )

    threading.Thread(target=_worker, daemon=True).start()


def create_batch_job(triggered_by_email: str = "") -> ManualePdfBatchJob:
    running = ManualePdfBatchJob.objects.filter(
        status__in=(ManualePdfBatchJob.STATUS_PENDING, ManualePdfBatchJob.STATUS_RUNNING)
    ).exists()
    if running:
        raise RuntimeError("Generazione batch già in corso.")
    return ManualePdfBatchJob.objects.create(
        status=ManualePdfBatchJob.STATUS_PENDING,
        triggered_by_email=triggered_by_email or "",
    )
