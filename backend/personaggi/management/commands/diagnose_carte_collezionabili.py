"""
Diagnostica rapida carte collezionabili (catalogo, config, accesso PG).

Uso:
  python manage.py diagnose_carte_collezionabili
  python manage.py diagnose_carte_collezionabili --campagna-slug kor35
  make diagnose-carte ENV=prod
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from personaggi.carte_collezionabili_models import (
    BustinaCarte,
    CartaCollezionabile,
    CartaPosseduta,
    ConfigurazioneCarteCollezionabili,
    EspansioneCarte,
    KeywordCarta,
)
from personaggi.carte_collezionabili_service import (
    get_carte_accesso_modo,
    personaggio_puo_accedere_carte,
    stato_carte_per_personaggio,
)
from personaggi.models import Campagna, Personaggio


class Command(BaseCommand):
    help = "Riepilogo DB carte: catalogo, config accesso, collezioni PG."

    def add_arguments(self, parser):
        parser.add_argument(
            "--campagna-slug",
            default="",
            help="Filtra per campagna (default: tutte le attive).",
        )
        parser.add_argument(
            "--personaggio-id",
            default="",
            help="UUID personaggio per stato accesso/collezione.",
        )

    def handle(self, *args, **options):
        slug_filter = (options.get("campagna_slug") or "").strip()
        pg_id = (options.get("personaggio_id") or "").strip()

        campagne = Campagna.objects.filter(attiva=True)
        if slug_filter:
            campagne = campagne.filter(slug=slug_filter)

        if not campagne.exists():
            self.stderr.write(self.style.ERROR("Nessuna campagna attiva trovata."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("=== Carte collezionabili — diagnostica ==="))
        self.stdout.write(
            f"Globale: carte={CartaCollezionabile.objects.count()} "
            f"espansioni={EspansioneCarte.objects.count()} "
            f"bustine={BustinaCarte.objects.count()} "
            f"keyword={KeywordCarta.objects.count()} "
            f"possedute={CartaPosseduta.objects.count()}"
        )

        for campagna in campagne.order_by("slug"):
            cfg = ConfigurazioneCarteCollezionabili.objects.filter(campagna=campagna).first()
            modo = get_carte_accesso_modo(campagna)
            n_carte = CartaCollezionabile.objects.filter(campagna=campagna).count()
            n_bust = BustinaCarte.objects.filter(campagna=campagna).count()
            n_poss = CartaPosseduta.objects.filter(personaggio__campagna=campagna).count()

            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO(f"Campagna: {campagna.nome} ({campagna.slug})"))
            self.stdout.write(
                f"  Config: abilitata={getattr(cfg, 'abilitata', None)} "
                f"accesso_modo={getattr(cfg, 'accesso_modo', None)} → effettivo={modo}"
            )
            self.stdout.write(f"  Catalogo: {n_carte} carte, {n_bust} bustine | Collezioni PG: {n_poss} istanze")

            if not cfg:
                self.stdout.write(
                    self.style.WARNING(
                        "  ⚠ Nessuna ConfigurazioneCarteCollezionabili: tab Carte nascosta (OFF)."
                    )
                )
            elif modo == "OFF":
                self.stdout.write(
                    self.style.WARNING(
                        "  ⚠ accesso_modo=OFF: tab Carte nascosta per tutti i PG."
                    )
                )
            elif modo == "TEST":
                self.stdout.write(
                    self.style.WARNING(
                        "  ⚠ accesso_modo=TEST: tab Carte solo per PnG staff (tipologia non giocante)."
                    )
                )
            elif n_carte == 0:
                self.stdout.write(
                    self.style.WARNING(
                        "  ⚠ Catalogo vuoto: esegui make seed-carte-esempio ENV=prod"
                    )
                )

        if pg_id:
            pg = Personaggio.objects.filter(pk=pg_id).select_related("campagna", "tipologia").first()
            if not pg:
                self.stderr.write(self.style.ERROR(f"Personaggio {pg_id} non trovato."))
                return
            stato = stato_carte_per_personaggio(pg)
            poss = CartaPosseduta.objects.filter(personaggio=pg).count()
            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO(f"Personaggio: {pg.nome} ({pg.id})"))
            self.stdout.write(f"  Campagna: {pg.campagna.slug}")
            self.stdout.write(f"  puo_accedere={stato.get('puo_accedere')} accesso_modo={stato.get('accesso_modo')}")
            self.stdout.write(f"  is_png_staff={stato.get('is_png_staff')} carte_possedute={poss}")
            if stato.get("puo_accedere") and poss == 0:
                self.stdout.write(
                    self.style.NOTICE(
                        "  Il seed carica solo il catalogo staff: apri una bustina per vedere carte in collezione."
                    )
                )
            if not personaggio_puo_accedere_carte(pg):
                self.stdout.write(
                    self.style.WARNING(
                        "  Tab «Carte» non visibile in app finché accesso_modo non è OPEN "
                        "(o TEST con PnG staff)."
                    )
                )
