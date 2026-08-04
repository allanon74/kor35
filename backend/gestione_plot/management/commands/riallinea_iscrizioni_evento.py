from django.core.management.base import BaseCommand

from gestione_plot.iscrizioni_evento_sync import riallinea_iscrizioni_catturate


class Command(BaseCommand):
    help = (
        "Riallinea Evento.partecipanti dai pagamenti PayPal CAPTURED (tipo ISCRIZIONE) "
        "orfani — ripara iscritti che hanno pagato ma non risultano in lista."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--evento",
            type=int,
            default=None,
            help="Limita a un evento (id numerico).",
        )

    def handle(self, *args, **options):
        stats = riallinea_iscrizioni_catturate(evento_id=options.get("evento"))
        self.stdout.write(self.style.SUCCESS(
            f"Esaminati={stats['esaminati']} aggiunti={stats['aggiunti']} "
            f"già_presenti={stats['gia_presenti']} conflitti={stats['conflitti']}"
        ))
