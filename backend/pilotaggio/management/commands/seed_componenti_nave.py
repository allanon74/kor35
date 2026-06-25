"""
Seed catalogo componenti nave: aura, colori, mattoni placeholder 0-9, coppie opposte.

Uso:
  python manage.py seed_componenti_nave
  python manage.py seed_componenti_nave --skip-if-complete
  python manage.py seed_componenti_nave --force  # ricrea coppie opposte
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from pilotaggio.componenti_nave_constants import AURA_COMPONENTI_NOME, AURA_COMPONENTI_SIGLA
from pilotaggio.models import CoppiaColoriComponente


def placeholders_componenti_completi() -> bool:
    from personaggi.models import Mattone

    indici = set(
        Mattone.objects.filter(
            aura__sigla=AURA_COMPONENTI_SIGLA,
            indice_componente__isnull=False,
        ).values_list("indice_componente", flat=True)
    )
    return all(i in indici for i in range(10))


COLORI_SEED = [
    ("0C0", "Nero", "#111111"),
    ("0C1", "Bianco", "#f5f5f5"),
    ("0C2", "Rosso", "#c62828"),
    ("0C3", "Verde", "#2e7d32"),
    ("0C4", "Blu", "#1565c0"),
    ("0C5", "Giallo", "#f9a825"),
    ("0C6", "Viola", "#6a1b9a"),
    ("0C7", "Arancio", "#ef6c00"),
    ("0C8", "Ciano", "#00838f"),
    ("0C9", "Magenta", "#ad1457"),
]

STATISTICHE_SEED = [
    ("0K0", "Componente 0"),
    ("0K1", "Componente 1"),
    ("0K2", "Componente 2"),
    ("0K3", "Componente 3"),
    ("0K4", "Componente 4"),
    ("0K5", "Componente 5"),
    ("0K6", "Componente 6"),
    ("0K7", "Componente 7"),
    ("0K8", "Componente 8"),
    ("0K9", "Componente 9"),
]

# Coppie opposte tra i 10 colori (5 coppie)
COPPIE_OPPOSITE_INDICI = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]


class Command(BaseCommand):
    help = (
        "Crea placeholder idempotenti: aura 0CP, 10 colori/statistiche, "
        "10 mattoni (indice 0–9) e 5 coppie opposte."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ricrea le coppie opposte anche se già presenti.",
        )
        parser.add_argument(
            "--skip-if-complete",
            action="store_true",
            help="Esce senza modifiche se i 10 mattoni placeholder esistono già.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get("skip_if_complete") and placeholders_componenti_completi():
            self.stdout.write(
                self.style.SUCCESS(
                    "Placeholder componenti nave (0–9, aura 0CP) già presenti. Nessuna azione."
                )
            )
            return

        gia_completi = placeholders_componenti_completi()
        from personaggi.models import (
            CARATTERISTICA,
            AURA,
            MATTONE,
            STATISTICA,
            Mattone,
            MattoneStatistica,
            Punteggio,
            Statistica,
        )

        aura, created_aura = Punteggio.objects.get_or_create(
            sigla=AURA_COMPONENTI_SIGLA,
            defaults={
                "nome": AURA_COMPONENTI_NOME,
                "tipo": AURA,
                "ordine": 900,
            },
        )
        if not created_aura and aura.tipo != AURA:
            self.stderr.write(self.style.ERROR(f"Sigla {AURA_COMPONENTI_SIGLA} già usata da altro tipo."))
            return

        colori = []
        for ordine, (sigla, nome, colore_hex) in enumerate(COLORI_SEED):
            car, _ = Punteggio.objects.get_or_create(
                sigla=sigla,
                defaults={
                    "nome": nome,
                    "tipo": CARATTERISTICA,
                    "colore": colore_hex,
                    "ordine": ordine,
                },
            )
            colori.append(car)

        statistiche = []
        for ordine, (sigla, nome) in enumerate(STATISTICHE_SEED):
            stat, _ = Statistica.objects.get_or_create(
                sigla=sigla,
                defaults={
                    "nome": nome,
                    "tipo": STATISTICA,
                    "ordine": ordine,
                },
            )
            statistiche.append(stat)

        mattoni_creati = 0
        for indice, stat in enumerate(statistiche):
            colore = colori[indice]
            mattone, created = Mattone.objects.get_or_create(
                aura=aura,
                caratteristica_associata=colore,
                indice_componente=indice,
                defaults={
                    "nome": f"Componente {indice} — placeholder ({colore.nome})",
                    "tipo": MATTONE,
                    "ordine": indice,
                    "sigla": f"CP{indice}",
                },
            )
            if created:
                mattoni_creati += 1
            MattoneStatistica.objects.get_or_create(
                mattone=mattone,
                statistica=stat,
                defaults={"valore": 1},
            )

        if options.get("force"):
            CoppiaColoriComponente.objects.all().delete()

        coppie_creati = 0
        for ordine, (ia, ib) in enumerate(COPPIE_OPPOSITE_INDICI):
            _, created = CoppiaColoriComponente.objects.get_or_create(
                colore_a=colori[ia],
                colore_b=colori[ib],
                defaults={"ordine": ordine},
            )
            if created:
                coppie_creati += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed componenti nave: aura={aura.sigla}, mattoni_nuovi={mattoni_creati}, "
                f"coppie_nuove={coppie_creati}, colori={len(colori)}"
                + (" (placeholder già esistenti, solo integrazione)" if gia_completi else "")
            )
        )
