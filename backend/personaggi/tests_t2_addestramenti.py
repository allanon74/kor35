"""
Test T2 addestramenti: Alchimia Extra (NCO → utilizzi) e raddoppia PA da equip.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    MODIFICATORE_ADDITIVO,
    Abilita,
    AbilitaStatistica,
    CreazioneConsumabileInCorso,
    Personaggio,
    PersonaggioAbilita,
    Punteggio,
    Statistica,
    Tessitura,
    TIPO_OGGETTO_FISICO,
    Oggetto,
    OggettoBase,
    OggettoStatistica,
    abilita_punteggio,
)
from personaggi.services import CreazioneConsumabileService


class AlchimiaExtraNcoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="t2-alchimia", password="x")
        self.pg = Personaggio.objects.create(nome="PG Alchimia Extra", proprietario=self.user)
        self.ca = Punteggio.objects.create(nome="Car T2", sigla="CT2", tipo=CARATTERISTICA)
        self.aura_alc = Punteggio.objects.create(
            nome="Aura Alchimia T2", sigla="ALC", tipo=AURA, is_generica=False
        )
        self.nco = Statistica.objects.create(
            nome="numero consumabili",
            sigla="NCO",
            parametro="num_cons",
            is_numero=True,
            valore_base_predefinito=3,
        )
        grant = Abilita.objects.create(
            nome="Grant ALC", caratteristica=self.ca, costo_pc=0, costo_crediti=0
        )
        abilita_punteggio.objects.create(abilita=grant, punteggio=self.aura_alc, valore=3)
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=grant)

        self.extra = Abilita.objects.create(
            nome="Alchimia Avanzata Extra test",
            caratteristica=self.ca,
            costo_pc=0,
            costo_crediti=0,
        )
        AbilitaStatistica.objects.create(
            abilita=self.extra,
            statistica=self.nco,
            valore=1,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.extra)

        self.tess = Tessitura.objects.create(
            nome="Pozione test",
            aura_richiesta=self.aura_alc,
        )

    def test_completa_creazione_aggiunge_bonus_nco(self):
        CreazioneConsumabileInCorso.objects.create(
            personaggio=self.pg,
            tessitura=self.tess,
            data_fine_creazione=timezone.now() - timedelta(minutes=1),
            completata=False,
        )
        # numero_base fallback 1 + 2*(alc3 - liv1) + NCO add 1 = 1+4+1 = 6
        ok, data = CreazioneConsumabileService.completa_creazione(self.pg)
        self.assertTrue(ok, data)
        self.assertEqual(data["utilizzi"], 6)


class RaddoppiaPaDaEquipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="t2-armatura", password="x")
        self.pg = Personaggio.objects.create(nome="PG Armatura Extra", proprietario=self.user)
        self.ca = Punteggio.objects.create(nome="Car Arm", sigla="CAR", tipo=CARATTERISTICA)
        self.pa = Statistica.objects.create(
            nome="Punti armatura",
            sigla="PA",
            parametro="armat",
            valore_base_predefinito=0,
        )
        self.extra = Abilita.objects.create(
            nome="Uso Armatura Avanzata Extra test",
            caratteristica=self.ca,
            costo_pc=0,
            costo_crediti=0,
            raddoppia_pa_da_equip=True,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.extra)

        template = OggettoBase.objects.create(
            nome="Template corazza",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
        )
        self.armatura = Oggetto.objects.create(
            nome="Corazza test",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            slot_fisici_possibili="armor",
            oggetto_base_generatore=template,
        )
        OggettoStatistica.objects.create(
            oggetto=self.armatura,
            statistica=self.pa,
            valore=4,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
        )
        self.armatura.sposta_in_inventario(self.pg)
        self.armatura.is_equipaggiato = True
        self.armatura.slot_equip = "armor"
        self.armatura.save(update_fields=["is_equipaggiato", "slot_equip", "updated_at"])

    def test_raddoppia_pa_da_oggetto_equipaggiato(self):
        if hasattr(self.pg, "_modificatori_calcolati_cache"):
            del self.pg._modificatori_calcolati_cache
        self.assertEqual(self.pg.get_valore_statistica("PA"), 8)

    def test_senza_flag_non_raddoppia(self):
        self.extra.raddoppia_pa_da_equip = False
        self.extra.save(update_fields=["raddoppia_pa_da_equip", "updated_at"])
        if hasattr(self.pg, "_modificatori_calcolati_cache"):
            del self.pg._modificatori_calcolati_cache
        self.assertEqual(self.pg.get_valore_statistica("PA"), 4)
