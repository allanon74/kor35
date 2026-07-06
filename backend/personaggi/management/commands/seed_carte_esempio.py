"""
Seed 20 carte demo «Sette Elegie» (10 PG, 2 OGG, 6 EVT, 2 LUO) + keyword MVP.

Uso:
  python manage.py seed_carte_esempio
  python manage.py seed_carte_esempio --campagna-slug kor35
  python manage.py seed_carte_esempio --force
  python manage.py seed_carte_esempio --skip-if-complete
  python manage.py seed_carte_esempio --no-keywords

Docker:
  make seed-carte-esempio ENV=dev-home
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from personaggi.carte_esempio_seed import seed_carte_esempio


class Command(BaseCommand):
    help = (
        "Carica espansione demo e 20 carte di esempio da "
        "personaggi/data/carte_esempio_sette_elegie.json (idempotente)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--campagna-slug",
            default="",
            help="Slug campagna (default: prima campagna attiva).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Aggiorna carte/keyword/espansione già presenti.",
        )
        parser.add_argument(
            "--skip-if-complete",
            action="store_true",
            help="Esce senza modifiche se tutte e 20 le carte esistono già.",
        )
        parser.add_argument(
            "--no-keywords",
            action="store_true",
            help="Non crea/aggiorna le 5 keyword con effect_script MVP.",
        )
        parser.add_argument(
            "--grant-starter",
            action="store_true",
            help="Dopo il seed, concede le carte demo e crediti ai PG della campagna.",
        )
        parser.add_argument(
            "--personaggio-nome",
            default="",
            help="Con --grant-starter, limita a un PG per nome (es. «Mario»).",
        )

    def handle(self, *args, **options):
        slug = (options.get("campagna_slug") or "").strip() or None
        try:
            stats = seed_carte_esempio(
                campagna_slug=slug,
                force=options.get("force", False),
                skip_if_complete=options.get("skip_if_complete", False),
                with_keywords=not options.get("no_keywords", False),
            )
            if options.get("grant_starter"):
                from personaggi.carte_esempio_seed import grant_starter_kit, _resolve_campagna

                campagna = _resolve_campagna(slug)
                nome_pg = (options.get("personaggio_nome") or "").strip() or None
                stats["starter"] = grant_starter_kit(
                    campagna,
                    personaggio_nome=nome_pg,
                )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        if stats.get("skipped"):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Skip: tutte le {stats.get('carte_totali', 20)} carte demo già presenti "
                    f"(campagna {stats['campagna']}, accesso {stats.get('config_accesso', '?')})."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Campagna: {stats['campagna_nome']} ({stats['campagna']})"
            )
        )
        self.stdout.write(f"Espansione: {stats['espansione']}")
        if stats.get("keywords_create") or stats.get("keywords_aggiornate"):
            self.stdout.write(
                f"Keyword: {stats['keywords_create']} create, "
                f"{stats['keywords_aggiornate']} aggiornate"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Carte: {stats['carte_create']} create, "
                f"{stats['carte_aggiornate']} aggiornate "
                f"(totale atteso {stats['carte_totali']})"
            )
        )
        if stats.get("bustina_id"):
            self.stdout.write(
                f"Bustina demo: {stats['bustina_id']}"
                + (" (nuova)" if stats.get("bustina_creata") else "")
            )
        if stats.get("bustina_qr_id"):
            self.stdout.write(f"QR bustina: {stats['bustina_qr_id']}")
        starter = stats.get("starter")
        if starter:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Starter kit: {starter['carte_concedute']} carte nuove su "
                    f"{len(starter['personaggi'])} PG "
                    f"({', '.join(starter['personaggi'][:5])}"
                    f"{'…' if len(starter['personaggi']) > 5 else ''})"
                )
            )
