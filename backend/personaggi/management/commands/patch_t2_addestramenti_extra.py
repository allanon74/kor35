"""
Patch addestramenti T2 utili e cablabili:

- Alchimia Avanzata Extra → AbilitaStatistica NCO +1
  (bonus utilizzi consumabile in CreazioneConsumabileService)
- Uso Armatura Avanzata Extra → raddoppia_pa_da_equip=True

Uso:
  python manage.py patch_t2_addestramenti_extra
  python manage.py patch_t2_addestramenti_extra --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from personaggi.models import (
    MODIFICATORE_ADDITIVO,
    Abilita,
    AbilitaStatistica,
    Statistica,
)


class Command(BaseCommand):
    help = "Patch T2: Alchimia Extra (NCO) e Uso Armatura Extra (raddoppia PA)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]
        ok = True
        ok = self._patch_alchimia_extra(dry) and ok
        ok = self._patch_uso_armatura_extra(dry) and ok
        if dry:
            self.stdout.write(self.style.WARNING("Dry-run: nessuna modifica salvata."))
            transaction.set_rollback(True)
        elif ok:
            self.stdout.write(self.style.SUCCESS("Patch T2 addestramenti extra completata."))
        else:
            self.stdout.write(self.style.ERROR("Patch incompleta."))

    def _get_abilita(self, nome):
        ab = Abilita.objects.filter(nome=nome).first()
        if not ab:
            self.stdout.write(self.style.WARNING(f"SKIP (abilità non trovata): {nome}"))
        return ab

    def _touch(self, abilita):
        try:
            from kor35.syncing import touch_sync_updated_at

            touch_sync_updated_at(Abilita, abilita.pk)
        except Exception:
            Abilita.objects.filter(pk=abilita.pk).update(updated_at=timezone.now())

    def _patch_alchimia_extra(self, dry):
        ab = self._get_abilita("Alchimia Avanzata Extra")
        if not ab:
            return False
        nco = Statistica.objects.filter(sigla="NCO").first()
        if not nco:
            self.stdout.write(self.style.ERROR("Statistica NCO mancante"))
            return False
        link = AbilitaStatistica.objects.filter(abilita=ab, statistica=nco).first()
        if link is None:
            self.stdout.write(f"CREATE {ab.nome} → NCO +1")
            if not dry:
                AbilitaStatistica.objects.create(
                    abilita=ab,
                    statistica=nco,
                    valore=1,
                    tipo_modificatore=MODIFICATORE_ADDITIVO,
                )
                self._touch(ab)
            return True
        changed = False
        if float(link.valore or 0) != 1.0:
            self.stdout.write(f"UPDATE {ab.nome} NCO valore {link.valore} → 1")
            link.valore = 1
            changed = True
        if link.tipo_modificatore != MODIFICATORE_ADDITIVO:
            self.stdout.write(f"UPDATE {ab.nome} NCO tipo → ADD")
            link.tipo_modificatore = MODIFICATORE_ADDITIVO
            changed = True
        if not changed:
            self.stdout.write(f"OK {ab.nome} → NCO +1")
            return True
        if not dry:
            link.save()
            self._touch(ab)
        return True

    def _patch_uso_armatura_extra(self, dry):
        ab = self._get_abilita("Uso Armatura Avanzata Extra")
        if not ab:
            return False
        if ab.raddoppia_pa_da_equip:
            self.stdout.write(f"OK {ab.nome} → raddoppia_pa_da_equip")
            return True
        self.stdout.write(f"UPDATE {ab.nome} → raddoppia_pa_da_equip=True")
        if not dry:
            ab.raddoppia_pa_da_equip = True
            # updated_at solo via _touch (un unico bump LWW).
            ab.save(update_fields=["raddoppia_pa_da_equip"])
            self._touch(ab)
        return True
