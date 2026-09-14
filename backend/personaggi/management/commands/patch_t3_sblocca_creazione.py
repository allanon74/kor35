"""
Allinea le abilità T3 craft (livello 5/6) ai campi:
  sblocca_creazione_livello / ambito_creazione / aura_creazione

Mappatura (testi catalogo prod):
  Mago / Sacerdote / Arcanista / Psionico / Cecchino / Lottatore → TES_AURA
  Trasmutatore → MATERIA (AMS)
  Genetista → MUTAZIONE (AIN)
  Ingegnere → MOD (ATE)
  Apotecario → CONSUMABILE (ALC)

Uso:
  python manage.py patch_t3_sblocca_creazione
  python manage.py patch_t3_sblocca_creazione --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from personaggi.models import AURA, Abilita, Punteggio


# (nome_abilita, livello, ambito, sigla_aura|None)
PATCHES = (
    ("Mago 1", 5, Abilita.AMBITO_CREAZIONE_TES_AURA, "AMA"),
    ("Mago 2", 6, Abilita.AMBITO_CREAZIONE_TES_AURA, "AMA"),
    ("Sacerdote 1", 5, Abilita.AMBITO_CREAZIONE_TES_AURA, "ASA"),
    ("Sacerdote 2", 6, Abilita.AMBITO_CREAZIONE_TES_AURA, "ASA"),
    ("Arcanista 1", 5, Abilita.AMBITO_CREAZIONE_TES_AURA, "AAR"),
    ("Arcanista 2", 6, Abilita.AMBITO_CREAZIONE_TES_AURA, "AAR"),
    ("Psionico 1", 5, Abilita.AMBITO_CREAZIONE_TES_AURA, "APS"),
    ("Psionico 2", 6, Abilita.AMBITO_CREAZIONE_TES_AURA, "APS"),
    ("Cecchino 1", 5, Abilita.AMBITO_CREAZIONE_TES_AURA, "AMD"),
    ("Cecchino 2", 6, Abilita.AMBITO_CREAZIONE_TES_AURA, "AMD"),
    ("Lottatore 1", 5, Abilita.AMBITO_CREAZIONE_TES_AURA, "AMZ"),
    ("Lottatore 2", 6, Abilita.AMBITO_CREAZIONE_TES_AURA, "AMZ"),
    ("Trasmutatore 1", 5, Abilita.AMBITO_CREAZIONE_MATERIA, None),
    ("Trasmutatore 2", 6, Abilita.AMBITO_CREAZIONE_MATERIA, None),
    ("Genetista 1", 5, Abilita.AMBITO_CREAZIONE_MUTAZIONE, None),
    ("Genetista 2", 6, Abilita.AMBITO_CREAZIONE_MUTAZIONE, None),
    ("Ingegnere 1", 5, Abilita.AMBITO_CREAZIONE_MOD, None),
    ("Ingegnere 2", 6, Abilita.AMBITO_CREAZIONE_MOD, None),
    ("Apotecario 1", 5, Abilita.AMBITO_CREAZIONE_CONSUMABILE, None),
    ("Apotecario 2", 6, Abilita.AMBITO_CREAZIONE_CONSUMABILE, None),
)


class Command(BaseCommand):
    help = "Patch T3: sblocca_creazione_livello 5/6 su professioni craft"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]
        aura_by_sigla = {
            p.sigla: p for p in Punteggio.objects.filter(tipo=AURA, is_generica=False)
        }
        ok = True
        for nome, livello, ambito, sigla in PATCHES:
            if not self._patch_one(nome, livello, ambito, sigla, aura_by_sigla, dry):
                ok = False
        if dry:
            self.stdout.write(self.style.WARNING("Dry-run: nessuna modifica salvata."))
            transaction.set_rollback(True)
        elif ok:
            self.stdout.write(self.style.SUCCESS("Patch T3 sblocca creazione completata."))
        else:
            self.stdout.write(self.style.ERROR("Patch incompleta: alcune abilità o aure mancanti."))

    def _touch(self, abilita):
        try:
            from kor35.syncing import touch_sync_updated_at

            touch_sync_updated_at(Abilita, abilita.pk)
        except Exception:
            Abilita.objects.filter(pk=abilita.pk).update(updated_at=timezone.now())

    def _patch_one(self, nome, livello, ambito, sigla, aura_by_sigla, dry):
        ab = Abilita.objects.filter(nome=nome).first()
        if not ab:
            self.stdout.write(self.style.WARNING(f"SKIP (abilità non trovata): {nome}"))
            return False

        aura = None
        if sigla:
            aura = aura_by_sigla.get(sigla)
            if not aura:
                self.stdout.write(self.style.ERROR(f"Aura mancante {sigla} per {nome}"))
                return False

        desired = {
            "sblocca_creazione_livello": livello,
            "ambito_creazione": ambito,
            "aura_creazione_id": aura.id if aura else None,
        }
        current = {
            "sblocca_creazione_livello": ab.sblocca_creazione_livello,
            "ambito_creazione": ab.ambito_creazione or "",
            "aura_creazione_id": ab.aura_creazione_id,
        }
        if current == desired:
            self.stdout.write(f"OK {nome} → {ambito} Lv{livello}" + (f"/{sigla}" if sigla else ""))
            return True

        self.stdout.write(
            f"UPDATE {nome}: {current} → {desired}"
        )
        if not dry:
            ab.sblocca_creazione_livello = livello
            ab.ambito_creazione = ambito
            ab.aura_creazione = aura
            ab.save(
                update_fields=[
                    "sblocca_creazione_livello",
                    "ambito_creazione",
                    "aura_creazione",
                    "updated_at",
                ]
            )
            self._touch(ab)
        return True
