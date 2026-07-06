"""Test EffectScript v1 — schema, validazione, motore MVP."""
from django.core.exceptions import ValidationError
from django.test import TestCase

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_MARZIALE,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_PERSONAGGIO,
    CARTA_TIPO_EVENTO,
    CartaCollezionabile,
    CartaPosseduta,
    ConfigurazioneCarteCollezionabili,
    CARTE_ACCESSO_OPEN,
    DUELLO_STATO_IN_CORSO,
    DuelloCarte,
    KeywordCarta,
)
from personaggi.carte_duello_service import (
    _avvia_turno_con_effetti,
    _inizializza_stato_gioco,
    _pg_key,
    esegui_azione_duello,
    get_duello_per_giocatore,
)
from personaggi.carte_effect_engine import (
    get_open_effect_choice,
    submit_effect_choice,
    trigger_keyword_effect_for_event,
    trigger_keyword_effect_on_exhaust,
)
from personaggi.carte_effect_script import (
    colpo_influenza_effect_script_template,
    danno_eroe_effect_script_template,
    mutazione_effect_script_template,
    pesca_effect_script_template,
    resolve_param_values,
    rigenerazione_energia_effect_script_template,
    validate_effect_script,
    validate_effect_script_for_keyword,
)
from personaggi.models import Campagna, Personaggio, TipologiaPersonaggio
from django.contrib.auth import get_user_model

User = get_user_model()


class CarteEffectScriptValidationTests(TestCase):
    def test_mutazione_template_valido(self):
        script = mutazione_effect_script_template()
        validate_effect_script(script)
        validate_effect_script_for_keyword(script, nome="Mutazione [X]", codice="MUTAZIONE")

    def test_danno_eroe_template_valido(self):
        script = danno_eroe_effect_script_template()
        validate_effect_script(script)
        validate_effect_script_for_keyword(script, nome="Ferita [X]", codice="FERITA")

    def test_guscio_template_valido(self):
        from personaggi.carte_effect_script import guscio_effect_script_template

        script = guscio_effect_script_template()
        validate_effect_script(script)
        validate_effect_script_for_keyword(script, nome="Guscio [X]", codice="GUSCIO")

    def test_guarigione_template_valido(self):
        from personaggi.carte_effect_script import (
            guarigione_completa_effect_script_template,
            guarigione_effect_script_template,
        )

        script = guarigione_effect_script_template()
        validate_effect_script(script)
        validate_effect_script_for_keyword(script, nome="Guarigione [X]", codice="GUARIGIONE")

        script_full = guarigione_completa_effect_script_template()
        validate_effect_script(script_full)
        validate_effect_script_for_keyword(script_full, nome="Guarigione", codice="GUARIGIONE")

    def test_sinergia_template_valido(self):
        from personaggi.carte_effect_script import (
            sinergia_energia_effect_script_template,
            sinergia_pesca_effect_script_template,
        )

        script = sinergia_pesca_effect_script_template()
        validate_effect_script(script)
        validate_effect_script_for_keyword(script, nome="Sinergia [X]", codice="SINERGIA")

        script_en = sinergia_energia_effect_script_template()
        validate_effect_script(script_en)
        validate_effect_script_for_keyword(script_en, nome="Sinergia [X]", codice="SINERGIA")

    def test_rigenerazione_template_valido(self):
        script = rigenerazione_energia_effect_script_template()
        validate_effect_script(script)
        validate_effect_script_for_keyword(script, nome="Rigenerazione [X]")

    def test_script_senza_params_placeholder_fallisce(self):
        script = mutazione_effect_script_template()
        script["params"] = {}
        with self.assertRaises(ValidationError):
            validate_effect_script_for_keyword(script, nome="Mutazione [X]")

    def test_choice_ref_sconosciuto_fallisce(self):
        script = mutazione_effect_script_template()
        script["steps"][1]["with"] = {"ref": "choice.unknown"}
        with self.assertRaises(ValidationError):
            validate_effect_script(script)

    def test_resolve_params_da_keyword(self):
        script = mutazione_effect_script_template()
        params = resolve_param_values(script, {"X": "3"})
        self.assertEqual(params["X"], 3)


class CarteEffectEngineMutazioneTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="fx_a", password="x")
        self.user_b = User.objects.create_user(username="fx_b", password="x")
        self.campagna = Campagna.objects.create(slug="fx-camp", nome="FX", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_OPEN, abilitata=True,
        )
        tipo = TipologiaPersonaggio.objects.create(nome="Umano")
        self.pg_a = Personaggio.objects.create(
            nome="Alpha", proprietario=self.user_a, campagna=self.campagna, tipologia=tipo,
        )
        self.pg_b = Personaggio.objects.create(
            nome="Beta", proprietario=self.user_b, campagna=self.campagna, tipologia=tipo,
        )
        self.pg = self.pg_a
        self.script = mutazione_effect_script_template()
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="MUTAZIONE",
            nome="Mutazione [X]",
            testo_regola="…costo [X].",
            effect_script=self.script,
        )

    def _carta_in_mano(self, nome, costo, cp_id_suffix, personaggio=None):
        pg = personaggio or self.pg
        c = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice=f"FX-{cp_id_suffix}",
            nome=nome,
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=costo,
            attacco=1,
            salute=2,
        )
        return CartaPosseduta.objects.create(personaggio=pg, carta=c)

    def test_mutazione_replace_da_mano(self):
        eroe = self._carta_in_mano("Eroe", 2, "hero")
        sost = self._carta_in_mano("Sostituto", 0, "sub")
        mazzo_ids = [str(eroe.id)] + [str(self._carta_in_mano(f"C{i}", 1, str(i)).id) for i in range(14)]

        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        pg_key = _pg_key(self.pg)
        duello.stato_gioco[pg_key]["eroi"][0] = str(eroe.id)
        duello.stato_gioco[pg_key]["mano"] = [str(sost.id)]
        duello.save()

        pending = trigger_keyword_effect_on_exhaust(
            duello,
            self.pg,
            carta_posseduta_id=str(eroe.id),
            hero_slot=0,
            keyword_params={"X": "0"},
            effect_script=self.script,
        )
        self.assertEqual(pending["type"], "effect_player_choice")
        self.assertIn(str(sost.id), pending["eligible_carta_posseduta_ids"])

        duello.refresh_from_db()
        after = submit_effect_choice(duello, self.pg, "replacement", str(sost.id))
        self.assertIsNone(after)
        duello.refresh_from_db()
        lato = duello.stato_gioco[pg_key]
        self.assertEqual(lato["eroi"][0], str(sost.id))
        self.assertNotIn(str(sost.id), lato["mano"])
        self.assertIsNone(get_open_effect_choice(duello, self.pg))

    def test_attacco_eroe_avversario_scatena_on_exhaust(self):
        """Attacco che rimuove eroe nemico avvia EffectScript dalla keyword nel testo carta."""
        eroe_b = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-EROE-MUT",
            nome="Mutante",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=1,
            testo_gioco="Alla morte: Mutazione 0.",
        )
        cp_eroe_b = CartaPosseduta.objects.create(personaggio=self.pg_b, carta=eroe_b)
        sost_b = self._carta_in_mano("Sostituto B", 0, "sub-b", personaggio=self.pg_b)
        attaccante = self._carta_in_mano("Attaccante", 1, "atk")

        mazzo_ids = [str(attaccante.id)] + [
            str(self._carta_in_mano(f"M{i}", 1, f"m{i}").id) for i in range(14)
        ]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        key_b = _pg_key(self.pg_b)
        duello.stato_gioco[key_a]["eroi"][0] = str(attaccante.id)
        duello.stato_gioco[key_b]["eroi"][0] = str(cp_eroe_b.id)
        duello.stato_gioco[key_b]["mano"] = [str(sost_b.id)]
        duello.save()

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "attacca",
            {"slot_eroe": 0, "bersaglio_eroe_slot": 0},
        )

        vista_b = get_duello_per_giocatore(duello.id, self.pg_b)
        self.assertIn("effect_pending", vista_b)
        self.assertEqual(vista_b["effect_pending"]["type"], "effect_player_choice")
        self.assertIn(str(sost_b.id), vista_b["effect_pending"]["eligible_carta_posseduta_ids"])

    def test_attacco_riduce_salute_prima_di_esaurire(self):
        """Con salute > attacco l'eroe resta in campo finché la salute non arriva a 0."""
        eroe_b = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-ROBUST",
            nome="Robusto",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=3,
            testo_gioco="Eroe resistente.",
        )
        cp_eroe_b = CartaPosseduta.objects.create(personaggio=self.pg_b, carta=eroe_b)
        attaccante = self._carta_in_mano("Attaccante", 1, "atk2")
        mazzo_ids = [str(attaccante.id)] + [
            str(self._carta_in_mano(f"N{i}", 1, f"n{i}").id) for i in range(14)
        ]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        key_b = _pg_key(self.pg_b)
        duello.stato_gioco[key_a]["eroi"][0] = str(attaccante.id)
        duello.stato_gioco[key_b]["eroi"][0] = str(cp_eroe_b.id)
        duello.stato_gioco[key_b]["salute_eroi"] = [3, None]
        duello.save()

        esegui_azione_duello(
            duello.id, self.pg_a, "attacca",
            {"slot_eroe": 0, "bersaglio_eroe_slot": 0},
        )
        duello.refresh_from_db()
        lato_b = duello.stato_gioco[key_b]
        self.assertEqual(lato_b["eroi"][0], str(cp_eroe_b.id))
        self.assertEqual(lato_b["salute_eroi"][0], 2)

    def test_on_play_colpo_influenza(self):
        script = colpo_influenza_effect_script_template()
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="COLPO",
            nome="Colpo [X]",
            testo_regola="Infligge [X] all'influenza.",
            effect_script=script,
        )
        evt = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-EVT",
            nome="Evento colpo",
            tipo=CARTA_TIPO_EVENTO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=0,
            testo_gioco="Colpo 2 all'avversario.",
        )
        cp_evt = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=evt)
        mazzo_ids = [str(cp_evt.id)] + [
            str(self._carta_in_mano(f"E{i}", 1, f"e{i}").id) for i in range(14)
        ]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            influenza_sfidante=20,
            influenza_sfidato=20,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["mano"] = [str(cp_evt.id)]
        duello.stato_gioco[key_a]["energia"] = 5
        duello.save()

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "gioca_carta",
            {"carta_posseduta_id": str(cp_evt.id)},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.influenza_sfidato, 18)

    def test_on_play_catena_doppio_colpo(self):
        """Due occorrenze della stessa keyword on_play si risolvono in sequenza."""
        script = colpo_influenza_effect_script_template()
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="COLPO",
            nome="Colpo [X]",
            testo_regola="Infligge [X] all'influenza.",
            effect_script=script,
        )
        evt = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-EVT-CHAIN",
            nome="Doppio colpo",
            tipo=CARTA_TIPO_EVENTO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=0,
            testo_gioco="Colpo 1. Colpo 2.",
        )
        cp_evt = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=evt)
        mazzo_ids = [str(cp_evt.id)] + [
            str(self._carta_in_mano(f"E{i}", 1, f"ec{i}").id) for i in range(14)
        ]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            influenza_sfidante=20,
            influenza_sfidato=20,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["mano"] = [str(cp_evt.id)]
        duello.stato_gioco[key_a]["energia"] = 5
        duello.save()

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "gioca_carta",
            {"carta_posseduta_id": str(cp_evt.id)},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.influenza_sfidato, 17)
        self.assertEqual(len(duello.stato_gioco.get("effect_queue") or []), 0)

    def test_on_play_rigenerazione_energia(self):
        script = rigenerazione_energia_effect_script_template()
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="RIGENERAZIONE",
            nome="Rigenerazione [X]",
            testo_regola="Guadagni [X] energia.",
            effect_script=script,
        )
        evt = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-REG",
            nome="Evento energia",
            tipo=CARTA_TIPO_EVENTO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=0,
            testo_gioco="Rigenerazione 3.",
        )
        cp_evt = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=evt)
        mazzo_ids = [str(cp_evt.id)] + [
            str(self._carta_in_mano(f"R{i}", 1, f"r{i}").id) for i in range(14)
        ]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["mano"] = [str(cp_evt.id)]
        duello.stato_gioco[key_a]["energia"] = 2
        duello.save()

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "gioca_carta",
            {"carta_posseduta_id": str(cp_evt.id)},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco[key_a]["energia"], 5)

    def test_on_play_ferita_scelta_eroe(self):
        script = danno_eroe_effect_script_template()
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="FERITA",
            nome="Ferita [X]",
            testo_regola="Scegli eroe avversario, [X] danni.",
            effect_script=script,
        )
        eroe_b = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-VITTIMA",
            nome="Vittima",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=4,
        )
        cp_eroe_b = CartaPosseduta.objects.create(personaggio=self.pg_b, carta=eroe_b)
        evt = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-FERITA",
            nome="Colpo mirato",
            tipo=CARTA_TIPO_EVENTO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=0,
            testo_gioco="Ferita 2.",
        )
        cp_evt = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=evt)
        mazzo_ids = [str(cp_evt.id)] + [
            str(self._carta_in_mano(f"F{i}", 1, f"f{i}").id) for i in range(14)
        ]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        key_b = _pg_key(self.pg_b)
        duello.stato_gioco[key_a]["mano"] = [str(cp_evt.id)]
        duello.stato_gioco[key_a]["energia"] = 5
        duello.stato_gioco[key_b]["eroi"][0] = str(cp_eroe_b.id)
        duello.stato_gioco[key_b]["salute_eroi"] = [4, None]
        duello.save()

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "gioca_carta",
            {"carta_posseduta_id": str(cp_evt.id)},
        )
        vista_a = get_duello_per_giocatore(duello.id, self.pg_a)
        self.assertEqual(vista_a["effect_pending"]["choice_kind"], "hero")
        self.assertIn("opponent_hero_0", [r["target"] for r in vista_a["effect_pending"]["eligible_hero_targets"]])

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "effect_choice",
            {"choice_id": "bersaglio", "hero_target": "opponent_hero_0"},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco[key_b]["salute_eroi"][0], 2)
        self.assertEqual(duello.stato_gioco[key_b]["eroi"][0], str(cp_eroe_b.id))

    def test_on_play_guscio_assegna_segnalini(self):
        from personaggi.carte_effect_script import guscio_effect_script_template

        script = guscio_effect_script_template()
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="GUSCIO",
            nome="Guscio [X]",
            testo_regola="Ottiene [X] Guscio.",
            effect_script=script,
        )
        eroe = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-GUSCIO",
            nome="Corazzato",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=3,
            testo_gioco="Guscio 2.",
        )
        cp_eroe = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=eroe)
        mazzo_ids = [str(cp_eroe.id)] + [
            str(self._carta_in_mano(f"G{i}", 1, f"g{i}").id) for i in range(14)
        ]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["mano"] = [str(cp_eroe.id)]
        duello.stato_gioco[key_a]["energia"] = 5
        duello.save()

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "gioca_carta",
            {"carta_posseduta_id": str(cp_eroe.id), "slot_eroe": 0},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco[key_a]["guscio_eroi"][0], 2)

    def test_sinergia_pesca_con_due_eroi(self):
        from personaggi.carte_effect_script import sinergia_pesca_effect_script_template

        script = sinergia_pesca_effect_script_template()
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="SIN_PESCA",
            nome="Sinergia [X]",
            testo_regola="Con 2+ Sinergia: Pesca [X].",
            effect_script=script,
        )
        eroe1 = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-SIN-1",
            nome="Alleato A",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=2,
            testo_gioco="Sinergia 1.",
        )
        eroe2 = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-SIN-2",
            nome="Alleato B",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=2,
            testo_gioco="Compagno che combatte in sinergia",
        )
        cp1 = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=eroe1)
        cp2 = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=eroe2)
        extra = []
        for i in range(10):
            c = CartaCollezionabile.objects.create(
                campagna=self.campagna,
                codice=f"FX-SD{i}",
                nome=f"Deck {i}",
                tipo=CARTA_TIPO_PERSONAGGIO,
                energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE,
                costo_gioco=1,
            )
            extra.append(CartaPosseduta.objects.create(personaggio=self.pg_a, carta=c))
        mazzo_ids = [str(cp.id) for cp in extra[:15]]
        while len(mazzo_ids) < 15:
            mazzo_ids.append(str(extra[0].id))

        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids[:15],
            mazzo_sfidato_ids=mazzo_ids[:15],
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        mano_prima = len(duello.stato_gioco[key_a]["mano"])
        duello.stato_gioco[key_a]["eroi"][0] = str(cp1.id)
        duello.stato_gioco[key_a]["eroi"][1] = str(cp2.id)
        duello.stato_gioco[key_a]["mazzo"] = [str(cp.id) for cp in extra]
        duello.save()

        _avvia_turno_con_effetti(duello, self.pg_a)
        duello.refresh_from_db()
        mano_dopo = len(duello.stato_gioco[key_a]["mano"])
        # +1 pesca turno base +1 Sinergia (solo eroe1 ha keyword nel testo)
        self.assertEqual(mano_dopo, mano_prima + 2)


class CarteEffectTurnTriggerTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="tr_a", password="x")
        self.user_b = User.objects.create_user(username="tr_b", password="x")
        self.campagna = Campagna.objects.create(slug="tr-camp", nome="TR", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_OPEN, abilitata=True,
        )
        tipo = TipologiaPersonaggio.objects.create(nome="Umano")
        self.pg_a = Personaggio.objects.create(
            nome="Alpha", proprietario=self.user_a, campagna=self.campagna, tipologia=tipo,
        )
        self.pg_b = Personaggio.objects.create(
            nome="Beta", proprietario=self.user_b, campagna=self.campagna, tipologia=tipo,
        )

    def test_on_turn_start_pesca_da_luogo(self):
        from personaggi.carte_collezionabili_models import CARTA_TIPO_LUOGO
        from personaggi.carte_duello_service import _avvia_turno_con_effetti
        from personaggi.carte_effect_script import pesca_effect_script_template

        script = pesca_effect_script_template()
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="PESCA",
            nome="Pesca [X]",
            testo_regola="Pesca [X] carte.",
            effect_script=script,
        )
        luogo = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-LUOGO",
            nome="Santuario",
            tipo=CARTA_TIPO_LUOGO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=2,
            testo_gioco="All'inizio del tuo turno: Pesca 1.",
        )
        cp_luogo = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=luogo)
        extra = []
        for i in range(10):
            c = CartaCollezionabile.objects.create(
                campagna=self.campagna,
                codice=f"FX-D{i}",
                nome=f"Deck {i}",
                tipo=CARTA_TIPO_PERSONAGGIO,
                energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE,
                costo_gioco=1,
            )
            extra.append(CartaPosseduta.objects.create(personaggio=self.pg_a, carta=c))
        mazzo_ids = [str(cp.id) for cp in extra[:15]]
        while len(mazzo_ids) < 15:
            mazzo_ids.append(str(extra[0].id))

        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids[:15],
            mazzo_sfidato_ids=mazzo_ids[:15],
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        mano_prima = len(duello.stato_gioco[key_a]["mano"])
        duello.stato_gioco["terra"] = {
            "carta_posseduta_id": str(cp_luogo.id),
            "giocatore_id": key_a,
        }
        duello.stato_gioco[key_a]["mazzo"] = [str(cp.id) for cp in extra]
        duello.save()

        _avvia_turno_con_effetti(duello, self.pg_a)
        duello.refresh_from_db()
        mano_dopo = len(duello.stato_gioco[key_a]["mano"])
        # +1 pesca turno base +1 keyword Pesca
        self.assertEqual(mano_dopo, mano_prima + 2)

    def test_on_turn_start_catena_due_carte_campo(self):
        """Luogo + eroe con Pesca: entrambi gli effetti si accodano e risolvono."""
        from personaggi.carte_collezionabili_models import CARTA_TIPO_LUOGO
        from personaggi.carte_effect_script import pesca_effect_script_template

        script = pesca_effect_script_template()
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="PESCA",
            nome="Pesca [X]",
            testo_regola="Pesca [X] carte.",
            effect_script=script,
        )
        luogo = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-LUOGO-2",
            nome="Fonte",
            tipo=CARTA_TIPO_LUOGO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=2,
            testo_gioco="Pesca 1.",
        )
        eroe = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="FX-EROE-PESCA",
            nome="Oracolo",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=2,
            testo_gioco="All'inizio del tuo turno: Pesca 1.",
        )
        cp_luogo = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=luogo)
        cp_eroe = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=eroe)
        extra = []
        for i in range(12):
            c = CartaCollezionabile.objects.create(
                campagna=self.campagna,
                codice=f"FX-C{i}",
                nome=f"Deck {i}",
                tipo=CARTA_TIPO_PERSONAGGIO,
                energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE,
                costo_gioco=1,
            )
            extra.append(CartaPosseduta.objects.create(personaggio=self.pg_a, carta=c))
        mazzo_ids = [str(cp.id) for cp in extra[:15]]
        while len(mazzo_ids) < 15:
            mazzo_ids.append(str(extra[0].id))

        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids[:15],
            mazzo_sfidato_ids=mazzo_ids[:15],
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        mano_prima = len(duello.stato_gioco[key_a]["mano"])
        duello.stato_gioco["terra"] = {
            "carta_posseduta_id": str(cp_luogo.id),
            "giocatore_id": key_a,
        }
        duello.stato_gioco[key_a]["eroi"][0] = str(cp_eroe.id)
        duello.stato_gioco[key_a]["mazzo"] = [str(cp.id) for cp in extra]
        duello.save()

        _avvia_turno_con_effetti(duello, self.pg_a)
        duello.refresh_from_db()
        mano_dopo = len(duello.stato_gioco[key_a]["mano"])
        # +1 pesca turno base +2 keyword (luogo + eroe)
        self.assertEqual(mano_dopo, mano_prima + 3)
        self.assertEqual(len(duello.stato_gioco.get("effect_queue") or []), 0)
