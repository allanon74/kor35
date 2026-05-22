"""
Copia i valori delle FK stat_costo_*, stat_tempo_*, stat_durata_* e stat_numero_*
dall'aura AMA a tutte le altre aure (Punteggio con tipo=AU).
"""
from django.core.management.base import BaseCommand
from django.db import models, transaction

from personaggi.models import AURA, Aura

SOURCE_SIGLA = "AMA"


def _campi_stat_fk():
    """Nomi dei ForeignKey su Punteggio con prefisso stat_costo_, stat_tempo_, stat_durata_ o stat_numero_."""
    return [
        f.name
        for f in Aura._meta.get_fields()
        if isinstance(f, models.ForeignKey)
        and (
            f.name.startswith("stat_costo_")
            or f.name.startswith("stat_tempo_")
            or f.name.startswith("stat_durata_")
            or f.name.startswith("stat_numero_")
        )
    ]


class Command(BaseCommand):
    help = (
        f"Copia le FK stat_costo_*, stat_tempo_*, stat_durata_* e stat_numero_* "
        f"dall'aura sorgente sigla {SOURCE_SIGLA} verso tutte le altre aure."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Esegue l'aggiornamento. Senza flag: solo anteprima (dry-run).",
        )
        parser.add_argument(
            "--sorgente-sigla",
            type=str,
            default=SOURCE_SIGLA,
            help=f"Sigla dell'aura sorgente (default: {SOURCE_SIGLA}).",
        )
        parser.add_argument(
            "--sorgente-pk",
            type=int,
            default=None,
            help="Opzionale: verifica che la sorgente abbia anche questo PK.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        sorgente_sigla = options["sorgente_sigla"].strip().upper()
        sorgente_pk = options["sorgente_pk"]

        campi = _campi_stat_fk()
        if not campi:
            self.stderr.write(self.style.ERROR("Nessun campo FK stat_* trovato sul modello Aura."))
            return

        candidati = Aura.objects.filter(tipo=AURA, sigla__iexact=sorgente_sigla)
        count = candidati.count()
        if count == 0:
            self.stderr.write(
                self.style.ERROR(f"Aura sorgente non trovata: sigla={sorgente_sigla}, tipo={AURA}.")
            )
            return
        if count > 1:
            pks = list(candidati.values_list("pk", flat=True))
            self.stderr.write(
                self.style.ERROR(
                    f"Sigla '{sorgente_sigla}' ambigua: {count} aure trovate (pk={pks}). "
                    "Interrotto per sicurezza."
                )
            )
            return

        sorgente = candidati.get()
        if sorgente_pk is not None and sorgente.pk != sorgente_pk:
            self.stderr.write(
                self.style.ERROR(
                    f"PK atteso {sorgente_pk}, trovato pk={sorgente.pk} per sigla '{sorgente_sigla}'. "
                    "Interrotto per sicurezza."
                )
            )
            return

        valori = {nome: getattr(sorgente, f"{nome}_id") for nome in campi}
        destinazioni = (
            Aura.objects.filter(tipo=AURA).exclude(pk=sorgente.pk).order_by("ordine", "sigla")
        )

        self.stdout.write(
            f"Sorgente: {sorgente.nome} (pk={sorgente.pk}, sigla={sorgente.sigla}) — "
            f"{len(campi)} campi, {destinazioni.count()} aure destinatarie.\n"
        )
        for nome in sorted(campi):
            stat_id = valori[nome]
            etichetta = "—"
            if stat_id:
                fk = getattr(sorgente, nome)
                etichetta = f"{fk.nome} (pk={stat_id})" if fk else f"pk={stat_id}"
            self.stdout.write(f"  {nome}: {etichetta}")

        if not destinazioni.exists():
            self.stdout.write(self.style.WARNING("\nNessuna altra aura da aggiornare."))
            return

        self.stdout.write("")
        aggiornate = 0
        with transaction.atomic():
            for aura in destinazioni:
                modifiche = []
                for nome in campi:
                    nuovo = valori[nome]
                    if getattr(aura, f"{nome}_id") != nuovo:
                        modifiche.append(nome)
                        setattr(aura, f"{nome}_id", nuovo)

                if not modifiche:
                    self.stdout.write(f"  = {aura.sigla} ({aura.nome}): già allineata")
                    continue

                self.stdout.write(
                    f"  → {aura.sigla} ({aura.nome}): {len(modifiche)} campi "
                    f"({', '.join(sorted(modifiche))})"
                )
                if apply:
                    aura.save(update_fields=modifiche)
                aggiornate += 1

            if not apply:
                transaction.set_rollback(True)

        self.stdout.write("")
        if apply:
            self.stdout.write(self.style.SUCCESS(f"Completato: {aggiornate} aure aggiornate."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry-run: {aggiornate} aure sarebbero aggiornate. "
                    "Ripeti con --apply per salvare."
                )
            )
