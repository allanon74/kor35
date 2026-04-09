"""
Rinomina i suffissi nel campo nome delle Abilità:
- termina con "III" → sostituisce "III" con "Avanzata I"
- termina con "IV" → sostituisce "IV" con "Avanzata II"
- termina con "Extra" o "extra" → sostituisce il suffisso con "Avanzata Extra"

Ordine: Extra/extra, poi IV, poi III (IV prima di III per evitare match ambigui su suffissi).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from personaggi.models import Abilita


def propone_nuovo_nome(nome: str) -> str | None:
    if nome.endswith("Extra"):
        return nome[:-5] + "Avanzata Extra"
    if nome.endswith("extra"):
        return nome[:-5] + "Avanzata Extra"
    if nome.endswith("IV"):
        return nome[:-2] + "Avanzata II"
    if nome.endswith("III"):
        return nome[:-3] + "Avanzata I"
    return None


class Command(BaseCommand):
    help = (
        "Aggiorna il nome delle Abilità: suffissi III/IV/Extra → Avanzata I / II / Avanzata Extra"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra le modifiche senza salvare sul database",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        qs = Abilita.objects.all().order_by("id")
        aggiornate = 0
        saltate_lunghezza = 0

        modifiche: list[tuple[str, str, int]] = []

        for ab in qs:
            nuovo = propone_nuovo_nome(ab.nome)
            if nuovo is None:
                continue
            if len(nuovo) > 90:
                self.stdout.write(
                    self.style.ERROR(
                        f"  [SKIP lunghezza] id={ab.id}: «{ab.nome}» → «{nuovo}» (>90 caratteri)"
                    )
                )
                saltate_lunghezza += 1
                continue
            modifiche.append((ab.nome, nuovo, ab.id))

        if not modifiche:
            self.stdout.write(self.style.WARNING("Nessuna abilità corrisponde ai criteri."))
            return

        self.stdout.write(f"Trovate {len(modifiche)} abilità da aggiornare.\n")

        for vecchio, nuovo, pk in modifiche:
            self.stdout.write(f"  id={pk}: «{vecchio}» → «{nuovo}»")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry-run: nessuna modifica salvata."))
            return

        with transaction.atomic():
            for vecchio, nuovo, pk in modifiche:
                Abilita.objects.filter(pk=pk).update(nome=nuovo)
                aggiornate += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nAggiornate {aggiornate} abilità nel database.")
        )
        if saltate_lunghezza:
            self.stdout.write(
                self.style.WARNING(f"Saltate per superamento max_length: {saltate_lunghezza}")
            )
