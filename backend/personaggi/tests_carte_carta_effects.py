"""Test EffectScript sulla carta (senza keyword mono-uso)."""
from django.contrib.auth.models import User
from django.test import TestCase

from personaggi.carte_carta_effects import validate_carta_effect_scripts
from personaggi.carte_collezionabili_models import (
    CARTE_ACCESSO_OPEN,
    CARTA_ENERGIA_MARZIALE,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_EVENTO,
    CARTA_TIPO_PERSONAGGIO,
    CartaCollezionabile,
    CartaPosseduta,
    ConfigurazioneCarteCollezionabili,
    DuelloCarte,
    DUELLO_STATO_IN_CORSO,
)
from personaggi.carte_duello_service import (
    _inizializza_stato_gioco,
    _inizio_turno_completo,
    _pg_key,
    esegui_azione_duello,
)
from personaggi.carte_effect_script import (
    colpo_influenza_effect_script_template,
    pesca_effect_script_template,
    rigenerazione_energia_effect_script_template,
)
from personaggi.models import Campagna, Personaggio, TipologiaPersonaggio


class CartaEffectScriptsValidationTests(TestCase):
    def test_validate_empty(self):
        self.assertEqual(validate_carta_effect_scripts([]), [])

    def test_validate_on_play_entry(self):
        script = colpo_influenza_effect_script_template()
        entries = validate_carta_effect_scripts([
            {"codice": "COLPO_UNICO", "nome": "Colpo del drago", "script": script},
        ])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["codice"], "COLPO_UNICO")
        self.assertEqual(entries[0]["script"]["trigger"]["event"], "on_play")

    def test_manual_requires_label(self):
        script = rigenerazione_energia_effect_script_template()
        script["trigger"]["event"] = "manual"
        with self.assertRaises(Exception):
            validate_carta_effect_scripts([{"script": script}])


class CartaEffectScriptsDuelloTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="cfx_a", password="x")
        self.user_b = User.objects.create_user(username="cfx_b", password="x")
        self.campagna = Campagna.objects.create(slug="cfx-camp", nome="CFX", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OPEN,
            abilitata=True,
        )
        tipo = TipologiaPersonaggio.objects.create(nome="Umano")
        self.pg_a = Personaggio.objects.create(
            nome="Alpha", proprietario=self.user_a, campagna=self.campagna, tipologia=tipo,
        )
        self.pg_b = Personaggio.objects.create(
            nome="Beta", proprietario=self.user_b, campagna=self.campagna, tipologia=tipo,
        )

    def _carta_evento_script(self, codice, nome, script, testo=""):
        return CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice=codice,
            nome=nome,
            tipo=CARTA_TIPO_EVENTO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            testo_gioco=testo,
            effect_scripts=[{"codice": "EFF", "nome": nome, "script": script}],
        )

    def _duello_con_mano(self, cp_ids_a, cp_ids_b=None):
        cp_ids_b = cp_ids_b or cp_ids_a
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=cp_ids_a,
            mazzo_sfidato_ids=cp_ids_b,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        duello.save()
        return duello

    def test_on_play_senza_keyword_nel_testo(self):
        script = colpo_influenza_effect_script_template()
        script["params"]["X"]["default"] = 2
        carta = self._carta_evento_script(
            "CFX-EVT-1",
            "Raggio",
            script,
            testo="Colpisce l'influenza avversaria.",
        )
        cp = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=carta)
        filler = [
            str(
                CartaPosseduta.objects.create(
                    personaggio=self.pg_a,
                    carta=CartaCollezionabile.objects.create(
                        campagna=self.campagna,
                        codice=f"CFX-F{i}",
                        nome=f"F{i}",
                        tipo=CARTA_TIPO_PERSONAGGIO,
                        energia=CARTA_ENERGIA_MARZIALE,
                        rarita=CARTA_RARITA_COMUNE,
                        costo_gioco=1,
                    ),
                ).id,
            )
            for i in range(14)
        ]
        duello = self._duello_con_mano([str(cp.id)] + filler)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["mano"] = [str(cp.id)]
        duello.stato_gioco[key_a]["energia"] = 5
        duello.save()

        esegui_azione_duello(duello.id, self.pg_a, "gioca_carta", {"carta_posseduta_id": str(cp.id)})
        duello.refresh_from_db()
        self.assertEqual(duello.influenza_sfidato, 18)

    def test_manual_attiva_abilita(self):
        script = rigenerazione_energia_effect_script_template()
        script["trigger"]["event"] = "manual"
        script["params"]["X"]["default"] = 3
        carta = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="CFX-PG-MAN",
            nome="Mago",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=2,
            testo_gioco="Canalizza energia arcana.",
            effect_scripts=[{"codice": "CANAL", "nome": "Canalizza", "script": script}],
        )
        cp = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=carta)
        filler = [
            str(
                CartaPosseduta.objects.create(
                    personaggio=self.pg_a,
                    carta=CartaCollezionabile.objects.create(
                        campagna=self.campagna,
                        codice=f"CFX-MF{i}",
                        nome=f"M{i}",
                        tipo=CARTA_TIPO_PERSONAGGIO,
                        energia=CARTA_ENERGIA_MARZIALE,
                        rarita=CARTA_RARITA_COMUNE,
                        costo_gioco=1,
                    ),
                ).id,
            )
            for i in range(14)
        ]
        duello = self._duello_con_mano([str(cp.id)] + filler)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["eroi"][0] = str(cp.id)
        duello.stato_gioco[key_a]["energia"] = 1
        duello.save()

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "attiva_abilita",
            {"carta_posseduta_id": str(cp.id), "script_codice": "CANAL"},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco[key_a]["energia"], 4)

    def test_on_turn_start_continuo_senza_keyword(self):
        script = pesca_effect_script_template()
        script["trigger"]["event"] = "on_turn_start"
        carta = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="CFX-PESCA",
            nome="Oracolo",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=2,
            testo_gioco="Vede il futuro.",
            effect_scripts=[{"nome": "Pesca turno", "script": script}],
        )
        cp = CartaPosseduta.objects.create(personaggio=self.pg_b, carta=carta)
        filler_a = [
            str(
                CartaPosseduta.objects.create(
                    personaggio=self.pg_a,
                    carta=CartaCollezionabile.objects.create(
                        campagna=self.campagna,
                        codice=f"CFX-PF-A{i}",
                        nome=f"PA{i}",
                        tipo=CARTA_TIPO_PERSONAGGIO,
                        energia=CARTA_ENERGIA_MARZIALE,
                        rarita=CARTA_RARITA_COMUNE,
                        costo_gioco=1,
                    ),
                ).id,
            )
            for i in range(14)
        ]
        filler_b = [
            str(
                CartaPosseduta.objects.create(
                    personaggio=self.pg_b,
                    carta=CartaCollezionabile.objects.create(
                        campagna=self.campagna,
                        codice=f"CFX-PF-B{i}",
                        nome=f"PB{i}",
                        tipo=CARTA_TIPO_PERSONAGGIO,
                        energia=CARTA_ENERGIA_MARZIALE,
                        rarita=CARTA_RARITA_COMUNE,
                        costo_gioco=1,
                    ),
                ).id,
            )
            for i in range(15)
        ]
        duello = self._duello_con_mano(filler_a, [str(cp.id)] + filler_b)
        key_b = _pg_key(self.pg_b)
        duello.turno_personaggio = self.pg_b
        duello.stato_gioco[key_b]["eroi"][0] = str(cp.id)
        duello.stato_gioco[key_b]["mazzo"] = list(filler_b)
        mano_prima = len(duello.stato_gioco[key_b].get("mano") or [])
        duello.save()

        _inizio_turno_completo(duello, self.pg_b)
        duello.refresh_from_db()
        mano_dopo = len(duello.stato_gioco[key_b].get("mano") or [])
        self.assertGreater(mano_dopo, mano_prima)
