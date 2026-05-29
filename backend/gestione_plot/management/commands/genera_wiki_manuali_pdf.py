"""
Rigenera uno o tutti i manuali PDF wiki.

Uso cron (produzione, consigliato al posto del thread in-process):

  docker compose exec backend python manage.py genera_wiki_manuali_pdf --all

  docker compose exec backend python manage.py genera_wiki_manuali_pdf --slug=giocatore
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from gestione_plot.models import ManualePdf, ManualePdfBatchJob
from gestione_plot.views import _render_wiki_widgets_for_pdf
from gestione_plot.wiki_pdf_service import esegui_generazione_manuale, make_pdf_request, process_batch_job


class Command(BaseCommand):
    help = "Genera PDF per manuali wiki (singolo, tutti, o job batch pendente)."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Tutti i manuali attivi")
        parser.add_argument("--slug", type=str, help="Solo questo manuale (slug)")
        parser.add_argument(
            "--job-id",
            type=int,
            help="Elabora un ManualePdfBatchJob pending (per worker/cron)",
        )
        parser.add_argument(
            "--host",
            type=str,
            default="",
            help="Host per URL assoluti WeasyPrint (default: primo ALLOWED_HOSTS)",
        )

    def handle(self, *args, **options):
        host = (options["host"] or "").strip()
        if not host:
            hosts = getattr(settings, "ALLOWED_HOSTS", None) or ["localhost"]
            host = hosts[0] if hosts and hosts[0] != "*" else "localhost"

        request = make_pdf_request(host)

        if options["job_id"]:
            process_batch_job(options["job_id"], host, _render_wiki_widgets_for_pdf)
            job = ManualePdfBatchJob.objects.get(pk=options["job_id"])
            self.stdout.write(self.style.SUCCESS(f"Job {job.pk} → {job.status}"))
            return

        if options["slug"]:
            manuale = ManualePdf.objects.filter(slug=options["slug"]).first()
            if not manuale:
                raise CommandError(f"Manuale «{options['slug']}» non trovato.")
            log = esegui_generazione_manuale(
                manuale, request, _render_wiki_widgets_for_pdf, triggered_by_email="manage.py"
            )
            self.stdout.write(self.style.SUCCESS(f"OK {manuale.slug} → {log.file_path} ({log.file_size_bytes} B)"))
            return

        if options["all"]:
            errors = 0
            for manuale in ManualePdf.objects.filter(attivo=True).order_by("ordine", "titolo"):
                try:
                    log = esegui_generazione_manuale(
                        manuale, request, _render_wiki_widgets_for_pdf, triggered_by_email="manage.py"
                    )
                    self.stdout.write(f"  ✓ {manuale.slug} ({log.file_size_bytes} B)")
                except Exception as exc:
                    errors += 1
                    self.stdout.write(self.style.ERROR(f"  ✗ {manuale.slug}: {exc}"))
            if errors:
                raise CommandError(f"{errors} manuali non generati.")
            self.stdout.write(self.style.SUCCESS("Tutti i manuali attivi rigenerati."))
            return

        raise CommandError("Specifica --all, --slug=<slug> oppure --job-id=<id>.")
