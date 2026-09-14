"""
Test residui T2/T3: Guscio PS, Chakra Extra, Cavaliere DaM condizionale, Macchinista mix.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from personaggi.models import (
    CARATTERISTICA,
    MODIFICATORE_ADDITIVO,
    Abilita,
    AbilitaStatistica,
    ClasseOggetto,
    Personaggio,
    PersonaggioAbilita,
    PersonaggioStatisticaBase,
    Punteggio,
    Statistica,
    TIPO_OGGETTO_FISICO,
    TIPO_OGGETTO_MATERIA,
    TIPO_OGGETTO_MOD,
    Oggetto,
    OggettoBase,
    OggettoCaratteristica,
    abilita_punteggio_dipendente,
)
from personaggi.services import GestioneOggettiService


class GuscioFantasmaPsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="guscio-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Guscio", proprietario=self.user)
        self.ca = Punteggio.objects.create(nome="Car Guscio", sigla="CGU", tipo=CARATTERISTICA)
        self.ps = Statistica.objects.create(
            nome="Punti Guscio", sigla="PS", parametro="guscio", valore_base_predefinito=0,
            is_risorsa_pool=True,
        )
        self.ab = Abilita.objects.create(
            nome="Guscio Fantasma Avanzata II test",
            caratteristica=self.ca,
            costo_pc=0,
            costo_crediti=0,
        )
        AbilitaStatistica.objects.create(
            abilita=self.ab,
            statistica=self.ps,
            valore=2,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.ab)

    def test_ps_plus_due(self):
        if hasattr(self.pg, "_modificatori_calcolati_cache"):
            del self.pg._modificatori_calcolati_cache
        self.assertEqual(self.pg.get_valore_statistica("PS"), 2)


class ChakraExtraImmunitaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="chakra-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Chakra", proprietario=self.user)
        self.ca = Punteggio.objects.create(nome="Car Cha", sigla="CCH", tipo=CARATTERISTICA)
        self.cha = Statistica.objects.create(
            nome="Chakra",
            sigla="CHA",
            parametro="chakra",
            valore_base_predefinito=3,
            is_risorsa_pool=True,
        )
        PersonaggioStatisticaBase.objects.create(
            personaggio=self.pg, statistica=self.cha, valore_base=3
        )
        self.pg._set_risorsa_corrente("CHA", 3)
        self.pg.save(update_fields=["risorse_consumabili"])
        self.ab = Abilita.objects.create(
            nome="Chakra Extra test",
            caratteristica=self.ca,
            costo_pc=0,
            costo_crediti=0,
            immunita_scarica_chakra_esterna=True,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.ab)

    def test_staff_non_puo_scaricare_cha(self):
        with self.assertRaises(ValueError):
            self.pg.regola_risorsa_staff("CHA", -1)
        self.assertEqual(self.pg.get_risorsa_corrente("CHA"), 3)

    def test_consumo_volontario_ok(self):
        nuovo = self.pg.consuma_risorsa_attivazione("CHA", 1, motivo="test")
        self.assertEqual(nuovo, 2)


class CavaliereDamCondizionaleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cav-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Cav", proprietario=self.user)
        self.rob = Punteggio.objects.create(nome="Robustezza", sigla="ROB", tipo=CARATTERISTICA)
        self.dam = Statistica.objects.create(
            nome="Danni Mischia", sigla="DaM", parametro="dannimis", valore_base_predefinito=0
        )
        # base Robustezza 2 via abilita_punteggio
        grant = Abilita.objects.create(
            nome="Grant ROB", caratteristica=self.rob, costo_pc=0, costo_crediti=0
        )
        from personaggi.models import abilita_punteggio

        abilita_punteggio.objects.create(abilita=grant, punteggio=self.rob, valore=2)
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=grant)

        self.cav = Abilita.objects.create(
            nome="Cavaliere 1 test",
            caratteristica=self.rob,
            costo_pc=0,
            costo_crediti=0,
        )
        abilita_punteggio_dipendente.objects.create(
            abilita=self.cav,
            punteggio_target=self.dam,
            punteggio_sorgente=self.rob,
            incremento=1,
            ogni_x=1,
            richiede_pesanti_una_mano=True,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.cav)

        self.forza = Abilita.objects.create(
            nome="Forza II test",
            caratteristica=self.rob,
            costo_pc=0,
            costo_crediti=0,
            consente_pesanti_una_mano=True,
        )

    def test_senza_forza_no_dam(self):
        if hasattr(self.pg, "_modificatori_calcolati_cache"):
            del self.pg._modificatori_calcolati_cache
        self.assertEqual(self.pg.get_valore_statistica("DaM"), 0)

    def test_con_forza_dam_da_robustezza(self):
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.forza)
        if hasattr(self.pg, "_modificatori_calcolati_cache"):
            del self.pg._modificatori_calcolati_cache
        # Robustezza 2 → DaM +2
        self.assertEqual(self.pg.get_valore_statistica("DaM"), 2)


class MacchinistaMixTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mac-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Mac", proprietario=self.user)
        self.ca = Punteggio.objects.create(nome="Car Mac", sigla="CMA", tipo=CARATTERISTICA)
        self.classe = ClasseOggetto.objects.create(nome="Spada Mac", max_mod_totali=2)
        # whitelist vuota materia e mod → di base bloccato senza mix
        tpl = OggettoBase.objects.create(nome="Tpl", tipo_oggetto=TIPO_OGGETTO_FISICO)
        self.host = Oggetto.objects.create(
            nome="Spada host",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            classe_oggetto=self.classe,
            oggetto_base_generatore=tpl,
            is_tecnologico=True,
        )
        self.mod = Oggetto.objects.create(
            nome="Mod test",
            tipo_oggetto=TIPO_OGGETTO_MOD,
            is_tecnologico=True,
            oggetto_base_generatore=OggettoBase.objects.create(
                nome="Tpl mod", tipo_oggetto=TIPO_OGGETTO_MOD
            ),
        )
        OggettoCaratteristica.objects.create(
            oggetto=self.mod, caratteristica=self.ca, valore=1
        )
        self.mat = Oggetto.objects.create(
            nome="Mat test",
            tipo_oggetto=TIPO_OGGETTO_MATERIA,
            is_tecnologico=False,
            oggetto_base_generatore=OggettoBase.objects.create(
                nome="Tpl mat", tipo_oggetto=TIPO_OGGETTO_MATERIA
            ),
        )
        OggettoCaratteristica.objects.create(
            oggetto=self.mat, caratteristica=self.ca, valore=1
        )
        # Installa mod bypassando check (diretto)
        self.mod.ospitato_su = self.host
        self.mod.save(update_fields=["ospitato_su", "updated_at"])

        self.mac = Abilita.objects.create(
            nome="Macchinista test",
            caratteristica=self.ca,
            costo_pc=0,
            costo_crediti=0,
            permette_mix_materia_mod=True,
        )

    def test_senza_macchinista_bloccato(self):
        ok, msg = GestioneOggettiService.verifica_compatibilita_hardware(
            self.host, self.mat, personaggio=self.pg
        )
        self.assertFalse(ok)

    def test_con_macchinista_ok(self):
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.mac)
        ok, msg = GestioneOggettiService.verifica_compatibilita_hardware(
            self.host, self.mat, personaggio=self.pg
        )
        self.assertTrue(ok, msg)
