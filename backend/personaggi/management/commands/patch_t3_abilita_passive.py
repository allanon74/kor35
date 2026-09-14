"""
Allinea effetti passivi T3 facilmente codificabili:
- Macchinista 1: COG +2
- Celebrante 1: Coralità (CCO) +1, Ritualistica (CRT) +3
- Cavaliere 1: PA +1 ogni 1 Robustezza (punteggi_dipendenti)

Non tocca il grant Tier 2 -2 già presente.

Uso:
  python manage.py patch_t3_abilita_passive
  python manage.py patch_t3_abilita_passive --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from personaggi.models import (
    MODIFICATORE_ADDITIVO,
    Abilita,
    AbilitaStatistica,
    Statistica,
    abilita_punteggio_dipendente,
    Punteggio,
)


class Command(BaseCommand):
    help = "Patch effetti passivi T3 (Macchinista/Celebrante/Cavaliere)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]
        ok = True
        ok = self._patch_macchinista(dry) and ok
        ok = self._patch_celebrante(dry) and ok
        ok = self._patch_cavaliere(dry) and ok
        if dry:
            self.stdout.write(self.style.WARNING("Dry-run: nessuna modifica salvata."))
            transaction.set_rollback(True)
        elif ok:
            self.stdout.write(self.style.SUCCESS("Patch T3 passive completata."))

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
            from django.utils import timezone

            Abilita.objects.filter(pk=abilita.pk).update(updated_at=timezone.now())

    def _upsert_stat(self, abilita, sigla, valore, dry):
        st = Statistica.objects.filter(sigla=sigla).first()
        if not st:
            self.stdout.write(self.style.ERROR(f"Statistica mancante: {sigla}"))
            return False
        link = AbilitaStatistica.objects.filter(abilita=abilita, statistica=st).first()
        desired = {
            "valore": valore,
            "tipo_modificatore": MODIFICATORE_ADDITIVO,
            "usa_bonus_slot_equip": False,
        }
        if link is None:
            self.stdout.write(f"CREATE {abilita.nome} → {sigla} +{valore}")
            if not dry:
                AbilitaStatistica.objects.create(abilita=abilita, statistica=st, **desired)
                self._touch(abilita)
            return True
        changes = {}
        if float(link.valore or 0) != float(valore):
            changes["valore"] = (float(link.valore or 0), valore)
        if link.tipo_modificatore != MODIFICATORE_ADDITIVO:
            changes["tipo_modificatore"] = (link.tipo_modificatore, MODIFICATORE_ADDITIVO)
        if link.usa_bonus_slot_equip:
            changes["usa_bonus_slot_equip"] = (True, False)
        if not changes:
            self.stdout.write(f"OK {abilita.nome} → {sigla}")
            return True
        self.stdout.write(f"UPDATE {abilita.nome} → {sigla}: {changes}")
        if not dry:
            for field, (_old, new) in changes.items():
                setattr(link, field, new)
            link.save()
            self._touch(abilita)
        return True

    def _patch_macchinista(self, dry):
        ab = self._get_abilita("Macchinista 1")
        if not ab:
            return False
        return self._upsert_stat(ab, "COG", 2, dry)

    def _patch_celebrante(self, dry):
        ab = self._get_abilita("Celebrante 1")
        if not ab:
            return False
        ok = self._upsert_stat(ab, "CCO", 1, dry)
        ok = self._upsert_stat(ab, "CRT", 3, dry) and ok
        return ok

    def _patch_cavaliere(self, dry):
        ab = self._get_abilita("Cavaliere 1")
        if not ab:
            return False
        target = Punteggio.objects.filter(nome="Punti armatura").first() or Statistica.objects.filter(sigla="PA").first()
        source = Punteggio.objects.filter(nome="Robustezza", tipo="CA").first()
        if not target or not source:
            self.stdout.write(self.style.ERROR("Mancano Punti armatura o Robustezza"))
            return False
        link = abilita_punteggio_dipendente.objects.filter(
            abilita=ab,
            punteggio_target=target,
            punteggio_sorgente=source,
        ).first()
        if link is None:
            self.stdout.write(
                f"CREATE {ab.nome} → PA +1 ogni 1 Robustezza"
            )
            if not dry:
                abilita_punteggio_dipendente.objects.create(
                    abilita=ab,
                    punteggio_target=target,
                    punteggio_sorgente=source,
                    incremento=1,
                    ogni_x=1,
                )
                self._touch(ab)
            return True
        if int(link.incremento or 0) == 1 and int(link.ogni_x or 0) == 1:
            self.stdout.write(f"OK {ab.nome} → PA/Robustezza")
            return True
        self.stdout.write(
            f"UPDATE {ab.nome} → PA/Robustezza: incremento={link.incremento}, ogni_x={link.ogni_x} → 1/1"
        )
        if not dry:
            link.incremento = 1
            link.ogni_x = 1
            link.save(update_fields=["incremento", "ogni_x", "updated_at"])
            self._touch(ab)
        return True
