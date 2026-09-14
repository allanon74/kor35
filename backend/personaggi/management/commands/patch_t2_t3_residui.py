"""
Chiude i residui T2/T3 ancora cablabili:

- Guscio Fantasma Avanzata II → PS +2
- Chakra Avanzato Extra → immunita_scarica_chakra_esterna
- Forza Straordinaria Avanzata II → consente_pesanti_una_mano
- Macchinista 1 → permette_mix_materia_mod (COG+2 già in patch_t3_abilita_passive)
- Cavaliere 1 → DaM +1 ogni 1 Robustezza se pesanti a una mano

Uso:
  python manage.py patch_t2_t3_residui
  python manage.py patch_t2_t3_residui --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from personaggi.models import (
    MODIFICATORE_ADDITIVO,
    Abilita,
    AbilitaStatistica,
    Statistica,
    abilita_punteggio_dipendente,
    Punteggio,
)


class Command(BaseCommand):
    help = "Patch residui T2/T3: Guscio PS, Chakra Extra, Forza II, Macchinista mix, Cavaliere DaM"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]
        ok = True
        ok = self._patch_guscio_ii(dry) and ok
        ok = self._patch_flag("Chakra Avanzato Extra", "immunita_scarica_chakra_esterna", dry) and ok
        ok = self._patch_flag("Forza Straordinaria Avanzata II", "consente_pesanti_una_mano", dry) and ok
        ok = self._patch_flag("Macchinista 1", "permette_mix_materia_mod", dry) and ok
        ok = self._patch_cavaliere_dam(dry) and ok
        if dry:
            self.stdout.write(self.style.WARNING("Dry-run: nessuna modifica salvata."))
            transaction.set_rollback(True)
        elif ok:
            self.stdout.write(self.style.SUCCESS("Patch residui T2/T3 completata."))
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

    def _patch_flag(self, nome, field, dry):
        ab = self._get_abilita(nome)
        if not ab:
            return False
        if getattr(ab, field):
            self.stdout.write(f"OK {nome} → {field}")
            return True
        self.stdout.write(f"UPDATE {nome} → {field}=True")
        if not dry:
            setattr(ab, field, True)
            ab.save(update_fields=[field, "updated_at"])
            self._touch(ab)
        return True

    def _patch_guscio_ii(self, dry):
        ab = self._get_abilita("Guscio Fantasma Avanzata II")
        if not ab:
            return False
        st = Statistica.objects.filter(sigla="PS").first()
        if not st:
            self.stdout.write(self.style.ERROR("Statistica PS mancante"))
            return False
        link = AbilitaStatistica.objects.filter(abilita=ab, statistica=st).first()
        if link is None:
            self.stdout.write(f"CREATE {ab.nome} → PS +2")
            if not dry:
                AbilitaStatistica.objects.create(
                    abilita=ab,
                    statistica=st,
                    valore=2,
                    tipo_modificatore=MODIFICATORE_ADDITIVO,
                    usa_bonus_slot_equip=False,
                )
                self._touch(ab)
            return True
        if float(link.valore or 0) == 2.0 and not link.usa_bonus_slot_equip:
            self.stdout.write(f"OK {ab.nome} → PS +2")
            return True
        self.stdout.write(f"UPDATE {ab.nome} → PS +2")
        if not dry:
            link.valore = 2
            link.tipo_modificatore = MODIFICATORE_ADDITIVO
            link.usa_bonus_slot_equip = False
            link.save()
            self._touch(ab)
        return True

    def _patch_cavaliere_dam(self, dry):
        ab = self._get_abilita("Cavaliere 1")
        if not ab:
            return False
        target = Statistica.objects.filter(sigla="DaM").first()
        source = Punteggio.objects.filter(nome="Robustezza", tipo="CA").first()
        if not target or not source:
            self.stdout.write(self.style.ERROR("Mancano DaM o Robustezza"))
            return False
        link = abilita_punteggio_dipendente.objects.filter(
            abilita=ab,
            punteggio_target=target,
            punteggio_sorgente=source,
        ).first()
        if link is None:
            self.stdout.write(
                f"CREATE {ab.nome} → DaM +1 ogni 1 Robustezza (richiede pesanti 1-mano)"
            )
            if not dry:
                abilita_punteggio_dipendente.objects.create(
                    abilita=ab,
                    punteggio_target=target,
                    punteggio_sorgente=source,
                    incremento=1,
                    ogni_x=1,
                    richiede_pesanti_una_mano=True,
                )
                self._touch(ab)
            return True
        changed = False
        if int(link.incremento or 0) != 1 or int(link.ogni_x or 0) != 1:
            self.stdout.write(f"UPDATE {ab.nome} DaM/Robustezza incremento/ogni_x → 1/1")
            link.incremento = 1
            link.ogni_x = 1
            changed = True
        if not link.richiede_pesanti_una_mano:
            self.stdout.write(f"UPDATE {ab.nome} → richiede_pesanti_una_mano=True")
            link.richiede_pesanti_una_mano = True
            changed = True
        if not changed:
            self.stdout.write(f"OK {ab.nome} → DaM/Robustezza (1-mano)")
            return True
        if not dry:
            link.save()
            self._touch(ab)
        return True
