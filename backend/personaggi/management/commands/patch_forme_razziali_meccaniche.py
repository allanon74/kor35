"""
Allinea le forme razziali «facili» agli effetti descritti:
- Siderale: DaM +3 (era +2)
- Onice: DaD +1 per slot COG occupato
- Ossidiana: PV +1 per slot COG occupato
- Astuzia: DaM +1 per slot COG occupato

Uso (dopo migrate 0272):
  python manage.py patch_forme_razziali_meccaniche
  python manage.py patch_forme_razziali_meccaniche --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from personaggi.models import (
    MODIFICATORE_ADDITIVO,
    SLOT_EQUIP_CONTEGGIO_COG_OCCUPATI,
    SLOT_EQUIP_CONTEGGIO_TUTTI_OGGETTI,
    Abilita,
    AbilitaStatistica,
    Statistica,
)

FORME_BY_NOME = {
    "Forma - Siderale": {
        "stat_sigla": "DaM",
        "valore": 3,
        "usa_bonus_slot_equip": False,
        "valore_per_unita": 0,
    },
    "Forma - Dell'Onice": {
        "stat_sigla": "DaD",
        "valore": 0,
        "usa_bonus_slot_equip": True,
        "valore_per_unita": 1,
    },
    "Forma - Di Ossidiana": {
        "stat_sigla": "PV",
        "valore": 0,
        "usa_bonus_slot_equip": True,
        "valore_per_unita": 1,
    },
    "Forma - Dell'Astuzia": {
        "stat_sigla": "DaM",
        "valore": 0,
        "usa_bonus_slot_equip": True,
        "valore_per_unita": 1,
    },
}


class Command(BaseCommand):
    help = "Patch meccaniche forme razziali (Siderale/Onice/Ossidiana/Astuzia)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra le modifiche senza salvare",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]
        stats = {
            sigla: Statistica.objects.filter(sigla=sigla).first()
            for sigla in ("DaM", "DaD", "PV")
        }
        missing = [s for s, obj in stats.items() if obj is None]
        if missing:
            self.stderr.write(self.style.ERROR(f"Statistiche mancanti: {', '.join(missing)}"))
            return

        for nome, cfg in FORME_BY_NOME.items():
            ab = Abilita.objects.filter(nome=nome).first()
            if not ab:
                self.stdout.write(self.style.WARNING(f"SKIP (abilità non trovata): {nome}"))
                continue
            st = stats[cfg["stat_sigla"]]
            link = AbilitaStatistica.objects.filter(abilita=ab, statistica=st).first()
            desired = {
                "valore": cfg["valore"],
                "tipo_modificatore": MODIFICATORE_ADDITIVO,
                "usa_bonus_slot_equip": cfg["usa_bonus_slot_equip"],
                "slot_equip_ammessi": [],
                "modalita_conteggio_slot_equip": (
                    SLOT_EQUIP_CONTEGGIO_COG_OCCUPATI
                    if cfg["usa_bonus_slot_equip"]
                    else SLOT_EQUIP_CONTEGGIO_TUTTI_OGGETTI
                ),
                "valore_per_unita_slot_equip": cfg["valore_per_unita"] or 1,
            }
            if link is None:
                self.stdout.write(f"CREATE {nome} → {cfg['stat_sigla']} {desired}")
                if not dry:
                    AbilitaStatistica.objects.create(abilita=ab, statistica=st, **desired)
                    self._touch_abilita(ab)
                continue

            changes = {}
            for field, val in desired.items():
                cur = getattr(link, field)
                if field == "valore":
                    cur = float(cur or 0)
                    val_cmp = float(val or 0)
                    if cur != val_cmp:
                        changes[field] = (cur, val)
                elif cur != val:
                    changes[field] = (cur, val)
            if not changes:
                self.stdout.write(f"OK (già allineata): {nome}")
                continue
            self.stdout.write(f"UPDATE {nome}: {changes}")
            if not dry:
                for field, (_old, new) in changes.items():
                    setattr(link, field, new)
                link.save()
                self._touch_abilita(ab)

        if dry:
            self.stdout.write(self.style.WARNING("Dry-run: nessuna modifica salvata."))
            transaction.set_rollback(True)
        else:
            self.stdout.write(self.style.SUCCESS("Patch forme razziali completata."))

    @staticmethod
    def _touch_abilita(abilita):
        try:
            from kor35.syncing import touch_sync_updated_at

            touch_sync_updated_at(Abilita, abilita.pk)
        except Exception:
            from django.utils import timezone

            Abilita.objects.filter(pk=abilita.pk).update(updated_at=timezone.now())
