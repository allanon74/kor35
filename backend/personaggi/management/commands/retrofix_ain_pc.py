from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.db.models import Q

from personaggi.models import Personaggio, PersonaggioAbilita, PuntiCaratteristicaMovimento


RETROFIX_PREFIX = "Retrofix AIN tratti:"
AIN_CHANGE_PREFIX = "Cambio tratto AIN:"


class Command(BaseCommand):
    help = (
        "Retrofix PC per tratti AIN pregressi: ricalcola il bonus/malus atteso dai tratti "
        "attualmente posseduti e applica solo il delta mancante."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Applica i movimenti PC. Senza flag esegue solo dry-run.",
        )
        parser.add_argument(
            "--personaggio-id",
            type=int,
            default=None,
            help="Limita il retrofix a un singolo personaggio.",
        )

    def _get_expected_ain_effect(self, personaggio):
        """Effetto PC atteso dallo stato AIN corrente (somma di -costo_pc per slot attivi)."""
        pivots = PersonaggioAbilita.objects.select_related("abilita").filter(
            personaggio=personaggio,
            abilita__is_tratto_aura=True,
            abilita__aura_riferimento__sigla="AIN",
        ).order_by("-data_acquisizione")

        arch = next((p for p in pivots if p.abilita.livello_riferimento in (0, 1)), None)
        forma = next((p for p in pivots if p.abilita.livello_riferimento == 2), None)

        total = 0
        if arch:
            total += -int(arch.abilita.costo_pc or 0)
        if forma:
            total += -int(forma.abilita.costo_pc or 0)
        return total

    def _get_applied_ain_effect(self, personaggio):
        """Effetto PC già registrato tramite movimenti AIN (cambio tratto + retrofix)."""
        val = (
            PuntiCaratteristicaMovimento.objects.filter(
                personaggio=personaggio,
            ).filter(
                Q(descrizione__startswith=AIN_CHANGE_PREFIX)
                | Q(descrizione__startswith=RETROFIX_PREFIX)
            ).aggregate(tot=Sum("importo"))["tot"]
            or 0
        )
        return int(val)

    def handle(self, *args, **options):
        apply_changes = options.get("apply", False)
        personaggio_id = options.get("personaggio_id")

        qs = Personaggio.objects.select_related("tipologia").all().order_by("id")
        if personaggio_id:
            qs = qs.filter(id=personaggio_id)

        total = 0
        impacted = 0
        total_delta = 0
        rows = []

        for pg in qs.iterator():
            total += 1
            expected = self._get_expected_ain_effect(pg)
            applied = self._get_applied_ain_effect(pg)
            missing = expected - applied
            if missing == 0:
                continue
            impacted += 1
            total_delta += missing
            rows.append((pg, expected, applied, missing))

        self.stdout.write(f"Personaggi analizzati: {total}")
        self.stdout.write(f"Personaggi con delta da applicare: {impacted}")
        self.stdout.write(f"Delta PC complessivo da applicare: {total_delta:+d}")

        for pg, expected, applied, missing in rows[:30]:
            self.stdout.write(
                f"- [{pg.id}] {pg.nome}: atteso={expected:+d}, gia_applicato={applied:+d}, delta={missing:+d}"
            )
        if len(rows) > 30:
            self.stdout.write(f"... altri {len(rows) - 30} personaggi omessi in output")

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run completato. Usa --apply per registrare i movimenti PC."
                )
            )
            return

        if not rows:
            self.stdout.write(self.style.SUCCESS("Nessun delta da applicare."))
            return

        with transaction.atomic():
            for pg, expected, applied, missing in rows:
                pg.modifica_pc(
                    missing,
                    f"{RETROFIX_PREFIX} atteso={expected:+d}, gia_applicato={applied:+d}, delta={missing:+d}",
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Retrofix completato. Movimenti creati: {len(rows)} | Delta totale: {total_delta:+d}"
            )
        )
