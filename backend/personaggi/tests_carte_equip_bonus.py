"""Test bonus equip in duello (incluso se_leader)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_MARZIALE,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_OGGETTO,
    CARTA_TIPO_PERSONAGGIO,
    CartaCollezionabile,
    CartaPosseduta,
    ConfigurazioneCarteCollezionabili,
    CARTE_ACCESSO_TEST,
    DUELLO_STATO_IN_CORSO,
    DuelloCarte,
)
from personaggi.carte_duello_service import (
    _inizializza_stato_gioco,
    _pg_key,
    _stats_eroe_slot,
    esegui_azione_duello,
)
from personaggi.carte_equip_bonus import applica_bonus_equip_duello
from personaggi.models import Campagna, Personaggio, TipologiaPersonaggio

User = get_user_model()


class CarteEquipBonusParserTests(TestCase):
    def test_legacy_sigla_forza(self):
        delta = applica_bonus_equip_duello({"stat_sigla": "FOR", "valore": 2}, is_leader=False)
        self.assertEqual(delta["forza"], 2)
        self.assertEqual(delta["robustezza"], 0)

    def test_piatto_se_leader(self):
        bonus = {"forza": 2, "robustezza_se_leader": 3}
        no_ldr = applica_bonus_equip_duello(bonus, is_leader=False)
        self.assertEqual(no_ldr["forza"], 2)
        self.assertEqual(no_ldr["robustezza"], 0)
        ldr = applica_bonus_equip_duello(bonus, is_leader=True)
        self.assertEqual(ldr["forza"], 2)
        self.assertEqual(ldr["robustezza"], 3)

    def test_lista_duello(self):
        bonus = {
            "duello": [
                {"stat": "forza", "valore": 1},
                {"stat": "robustezza", "valore": 2, "se_leader": True},
            ],
        }
        self.assertEqual(applica_bonus_equip_duello(bonus, is_leader=True)["robustezza"], 2)


class ValidateBonusEquipTests(TestCase):
    def test_vuoto(self):
        from personaggi.carte_equip_bonus import validate_bonus_equip

        self.assertEqual(validate_bonus_equip(None), {})
        self.assertEqual(validate_bonus_equip({}), {})

    def test_reliquario_e_piatto(self):
        from personaggi.carte_equip_bonus import validate_bonus_equip

        out = validate_bonus_equip({
            "stat_sigla": "FOR",
            "valore": 1,
            "forza": 2,
            "robustezza_se_leader": 3,
        })
        self.assertEqual(out["stat_sigla"], "FOR")
        self.assertEqual(out["valore"], 1)
        self.assertEqual(out["forza"], 2)
        self.assertEqual(out["robustezza_se_leader"], 3)

    def test_lista_duello(self):
        from personaggi.carte_equip_bonus import validate_bonus_equip

        out = validate_bonus_equip({
            "duello": [{"stat": "INI", "valore": 1, "se_leader": True}],
        })
        self.assertEqual(len(out["duello"]), 1)
        self.assertEqual(out["duello"][0]["stat"], "iniziativa")
        self.assertTrue(out["duello"][0]["se_leader"])

    def test_sigla_invalida(self):
        from django.core.exceptions import ValidationError

        from personaggi.carte_equip_bonus import validate_bonus_equip

        with self.assertRaises(ValidationError):
            validate_bonus_equip({"stat_sigla": "XYZ", "valore": 1})


class CarteEquipBonusDuelloTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="eq_a", password="x")
        self.user_b = User.objects.create_user(username="eq_b", password="x")
        self.campagna = Campagna.objects.create(slug="eq-test", nome="Eq", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_TEST, abilitata=True,
        )
        tipo = TipologiaPersonaggio.objects.create(nome="PNG", giocante=False)
        self.pg_a = Personaggio.objects.create(
            nome="A", proprietario=self.user_a, campagna=self.campagna, tipologia=tipo,
        )
        self.pg_b = Personaggio.objects.create(
            nome="B", proprietario=self.user_b, campagna=self.campagna, tipologia=tipo,
        )

    def test_equip_forza_su_eroe(self):
        eroe = CartaPosseduta.objects.create(
            personaggio=self.pg_a,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="EQ-EROE", nome="Guerriero",
                tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1, attacco=2, salute=3,
            ),
        )
        ogg = CartaPosseduta.objects.create(
            personaggio=self.pg_a,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="EQ-OGG", nome="Spada",
                tipo=CARTA_TIPO_OGGETTO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1,
                bonus_equip={"forza": 2},
            ),
        )
        duello = self._duello_con_eroe_equip(eroe, ogg, slot=1)
        lato = duello.stato_gioco[_pg_key(self.pg_a)]
        stats = _stats_eroe_slot(duello, self.pg_a, lato, 1)
        # 2 attacco + 1 aura marziale + 2 equip
        self.assertEqual(stats["forza"], 5)

    def test_equip_se_leader_solo_su_leader(self):
        leader_card = CartaCollezionabile.objects.create(
            campagna=self.campagna, codice="EQ-LDR", nome="Comandante",
            tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE, costo_gioco=2, attacco=3, salute=4,
        )
        leader_cp = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=leader_card)
        ogg = CartaPosseduta.objects.create(
            personaggio=self.pg_a,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="EQ-COR", nome="Corazza",
                tipo=CARTA_TIPO_OGGETTO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1,
                bonus_equip={
                    "forza": 2,
                    "robustezza_se_leader": 2,
                },
            ),
        )
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            leader_sfidante_id=str(leader_cp.id),
            leader_sfidato_id=str(leader_cp.id),
            mazzo_sfidante_ids=[str(leader_cp.id)] * 15,
            mazzo_sfidato_ids=[str(leader_cp.id)] * 15,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["eroi"][0] = str(leader_cp.id)
        duello.stato_gioco[key_a]["salute_eroi"] = [4, None]
        duello.stato_gioco[key_a]["oggetti"] = {"0": str(ogg.id)}
        duello.save()

        stats_leader = _stats_eroe_slot(duello, self.pg_a, duello.stato_gioco[key_a], 0)
        self.assertTrue(stats_leader["is_leader"])
        self.assertEqual(stats_leader["forza"], 6)
        self.assertEqual(stats_leader["robustezza"], 6)

        # Non-leader nello slot 1: stesso equip, senza bonus se_leader
        altro = CartaPosseduta.objects.create(
            personaggio=self.pg_a,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="EQ-ALT", nome="Soldato",
                tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1, attacco=1, salute=2,
            ),
        )
        duello.stato_gioco[key_a]["eroi"][1] = str(altro.id)
        duello.stato_gioco[key_a]["oggetti"]["1"] = str(ogg.id)
        stats_alt = _stats_eroe_slot(duello, self.pg_a, duello.stato_gioco[key_a], 1)
        self.assertFalse(stats_alt["is_leader"])
        self.assertEqual(stats_alt["robustezza"], 2)

    def test_gioca_equip_aumenta_salute_leader(self):
        leader_card = CartaCollezionabile.objects.create(
            campagna=self.campagna, codice="EQ-LDR2", nome="Comandante2",
            tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE, costo_gioco=2, attacco=3, salute=4,
        )
        leader_cp = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=leader_card)
        ogg = CartaPosseduta.objects.create(
            personaggio=self.pg_a,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="EQ-COR2", nome="Corazza2",
                tipo=CARTA_TIPO_OGGETTO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=0,
                bonus_equip={"robustezza_se_leader": 2},
            ),
        )
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            leader_sfidante_id=str(leader_cp.id),
            leader_sfidato_id=str(leader_cp.id),
            mazzo_sfidante_ids=[str(leader_cp.id)] * 15,
            mazzo_sfidato_ids=[str(leader_cp.id)] * 15,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["mano"] = [str(ogg.id)]
        duello.stato_gioco[key_a]["energia"] = 5
        duello.save()

        esegui_azione_duello(
            duello.id, self.pg_a, "gioca_carta",
            {"carta_posseduta_id": str(ogg.id), "slot_eroe": 0},
        )
        duello.refresh_from_db()
        sal = duello.stato_gioco[key_a]["salute_eroi"][0]
        stats = _stats_eroe_slot(duello, self.pg_a, duello.stato_gioco[key_a], 0)
        self.assertEqual(sal, stats["robustezza"])

    def _duello_con_eroe_equip(self, eroe_cp, ogg_cp, slot=1):
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            leader_sfidante_id=str(eroe_cp.id),
            leader_sfidato_id=str(eroe_cp.id),
            mazzo_sfidante_ids=[str(eroe_cp.id)] * 15,
            mazzo_sfidato_ids=[str(eroe_cp.id)] * 15,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["eroi"][slot] = str(eroe_cp.id)
        duello.stato_gioco[key_a]["salute_eroi"][slot] = int(eroe_cp.carta.salute or 1)
        duello.stato_gioco[key_a]["oggetti"] = {str(slot): str(ogg_cp.id)}
        duello.save()
        return duello
