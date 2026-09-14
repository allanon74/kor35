"""
Chiude i pezzi T3 ancora patchabili in modo pulito:

- Celebrante 2 → CCO +1
- Gladiatore 2 → bonus per oggetti modificati per classe:
    armi (Spada/Bastone/Martello/Arma in Asta/Pugnale) → DaM +1 cad.
    difesa (Elmo/Corazza/Mantello/Veste) → PV +1 e PA +1 cad.
    accessori (Cintura/Anello/Collana) → CHA +1 cad.

Uso:
  python manage.py patch_t3_celebrante_gladiatore
  python manage.py patch_t3_celebrante_gladiatore --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from personaggi.models import (
    MODIFICATORE_ADDITIVO,
    SLOT_EQUIP_CONTEGGIO_OGGETTI_MODIFICATI,
    Abilita,
    AbilitaStatistica,
    ClasseOggetto,
    Statistica,
)


ARMI = ("Spada", "Bastone", "Martello", "Arma in Asta", "Pugnale")
DIFESA = ("Elmo", "Corazza", "Mantello", "Veste")
ACCESSORI = ("Cintura", "Anello", "Collana")


class Command(BaseCommand):
    help = "Patch T3: Celebrante 2 (CCO) e Gladiatore 2 (classi oggetto)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]
        ok = self._patch_celebrante_2(dry)
        ok = self._patch_gladiatore_2(dry) and ok
        if dry:
            self.stdout.write(self.style.WARNING("Dry-run: nessuna modifica salvata."))
            transaction.set_rollback(True)
        elif ok:
            self.stdout.write(self.style.SUCCESS("Patch T3 Celebrante/Gladiatore completata."))
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

    def _classi(self, nomi):
        found = []
        for nome in nomi:
            c = ClasseOggetto.objects.filter(nome__iexact=nome).first()
            if not c:
                self.stdout.write(self.style.ERROR(f"ClasseOggetto mancante: {nome}"))
                return None
            found.append(c)
        return found

    def _upsert_flat_stat(self, abilita, sigla, valore, dry):
        st = Statistica.objects.filter(sigla=sigla).first()
        if not st:
            self.stdout.write(self.style.ERROR(f"Statistica mancante: {sigla}"))
            return False
        link = AbilitaStatistica.objects.filter(abilita=abilita, statistica=st).first()
        if link is None:
            self.stdout.write(f"CREATE {abilita.nome} → {sigla} +{valore}")
            if not dry:
                AbilitaStatistica.objects.create(
                    abilita=abilita,
                    statistica=st,
                    valore=valore,
                    tipo_modificatore=MODIFICATORE_ADDITIVO,
                    usa_bonus_slot_equip=False,
                )
                self._touch(abilita)
            return True
        if float(link.valore or 0) == float(valore) and not link.usa_bonus_slot_equip:
            self.stdout.write(f"OK {abilita.nome} → {sigla} +{valore}")
            return True
        self.stdout.write(f"UPDATE {abilita.nome} → {sigla} +{valore}")
        if not dry:
            link.valore = valore
            link.tipo_modificatore = MODIFICATORE_ADDITIVO
            link.usa_bonus_slot_equip = False
            link.save()
            self._touch(abilita)
        return True

    def _upsert_mod_classi(self, abilita, sigla, classi, dry):
        st = Statistica.objects.filter(sigla=sigla).first()
        if not st:
            self.stdout.write(self.style.ERROR(f"Statistica mancante: {sigla}"))
            return False
        link = AbilitaStatistica.objects.filter(abilita=abilita, statistica=st).first()
        desired = {
            "valore": 0,
            "tipo_modificatore": MODIFICATORE_ADDITIVO,
            "usa_bonus_slot_equip": True,
            "modalita_conteggio_slot_equip": SLOT_EQUIP_CONTEGGIO_OGGETTI_MODIFICATI,
            "valore_per_unita_slot_equip": 1,
            "slot_equip_ammessi": [],
        }
        if link is None:
            self.stdout.write(
                f"CREATE {abilita.nome} → {sigla} +1 × oggetti modificati "
                f"[{', '.join(c.nome for c in classi)}]"
            )
            if not dry:
                link = AbilitaStatistica.objects.create(abilita=abilita, statistica=st, **desired)
                link.classi_oggetto_conteggio.set(classi)
                self._touch(abilita)
            return True

        changes = []
        for field, want in desired.items():
            cur = getattr(link, field)
            if field == "slot_equip_ammessi":
                cur = list(cur or [])
            if cur != want:
                changes.append(field)
        cur_ids = set(link.classi_oggetto_conteggio.values_list("id", flat=True))
        want_ids = {c.id for c in classi}
        if cur_ids != want_ids:
            changes.append("classi_oggetto_conteggio")
        if not changes:
            self.stdout.write(f"OK {abilita.nome} → {sigla} classi")
            return True
        self.stdout.write(f"UPDATE {abilita.nome} → {sigla}: {changes}")
        if not dry:
            for field, want in desired.items():
                setattr(link, field, want)
            link.save()
            link.classi_oggetto_conteggio.set(classi)
            self._touch(abilita)
        return True

    def _patch_celebrante_2(self, dry):
        ab = self._get_abilita("Celebrante 2")
        if not ab:
            return False
        return self._upsert_flat_stat(ab, "CCO", 1, dry)

    def _patch_gladiatore_2(self, dry):
        ab = self._get_abilita("Gladiatore 2")
        if not ab:
            return False
        armi = self._classi(ARMI)
        difesa = self._classi(DIFESA)
        accessori = self._classi(ACCESSORI)
        if not armi or not difesa or not accessori:
            return False
        ok = self._upsert_mod_classi(ab, "DaM", armi, dry)
        ok = self._upsert_mod_classi(ab, "PV", difesa, dry) and ok
        ok = self._upsert_mod_classi(ab, "PA", difesa, dry) and ok
        ok = self._upsert_mod_classi(ab, "CHA", accessori, dry) and ok
        return ok
