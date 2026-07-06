"""Test tag carte — catalogo, staff API, effetti duello."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_MARZIALE,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_EVENTO,
    CARTA_TIPO_PERSONAGGIO,
    CartaCollezionabile,
    CartaPosseduta,
    ConfigurazioneCarteCollezionabili,
    CARTE_ACCESSO_OPEN,
    DUELLO_STATO_IN_CORSO,
    DuelloCarte,
    KeywordCarta,
    TagCarta,
)
from personaggi.carte_duello_service import (
    _inizializza_stato_gioco,
    _pg_key,
    _stats_eroe_slot,
    esegui_azione_duello,
)
from personaggi.carte_effect_script import (
    cavalleria_effect_script_template,
    crociata_effect_script_template,
    validate_effect_script,
)
from personaggi.models import Campagna, Personaggio, TipologiaPersonaggio

User = get_user_model()


class TagCartaStaffApiTests(APITestCase):
    url = "/api/personaggi/api/staff/carte/tags/"

    def setUp(self):
        from personaggi.models import CAMPAGNA_ROLE_MASTER, CampagnaUtente

        self.user = User.objects.create_user(username="tag_staff", password="x")
        self.campagna = Campagna.objects.create(slug="tag-test", nome="Tag Test", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_OPEN, abilitata=True,
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.user, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )
        self.client.force_authenticate(user=self.user)

    def test_create_and_assign_tag_to_carta(self):
        resp = self.client.post(
            self.url,
            {
                "codice": "CAVALIERE",
                "nome": "Cavaliere",
                "descrizione": "Unità montata o cavalleria.",
                "colore": "#c9a227",
                "attiva": True,
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        tag_id = resp.data["id"]

        carta = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="TAG-PG-1",
            nome="Ser Galahad",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=2,
            attacco=2,
            salute=3,
        )
        cat_url = "/api/personaggi/api/staff/carte/catalogo/"
        patch = self.client.patch(
            f"{cat_url}{carta.id}/",
            {"tag_ids": [tag_id]},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        carta.refresh_from_db()
        self.assertEqual(carta.tags.count(), 1)
        self.assertEqual(carta.tags.first().codice, "CAVALIERE")


class TagEffectScriptTemplateTests(TestCase):
    def test_cavalleria_e_crociata_template_validi(self):
        validate_effect_script(cavalleria_effect_script_template())
        validate_effect_script(crociata_effect_script_template())


class TagDuelloEffectTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="tag_a", password="x")
        self.user_b = User.objects.create_user(username="tag_b", password="x")
        self.campagna = Campagna.objects.create(slug="tag-duel", nome="Tag Duel", attiva=True)
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
        self.tag_cav = TagCarta.objects.create(
            campagna=self.campagna, codice="CAVALIERE", nome="Cavaliere",
        )
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="CAVALLERIA",
            nome="Cavalleria [X]",
            testo_regola="I tuoi Cavalieri prendono +[X] Forza e +[X] Robustezza.",
            effect_script=cavalleria_effect_script_template(),
        )
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="CROCIATA",
            nome="Crociata",
            testo_regola="Distruggi tutti i personaggi che non sono Cavalieri.",
            effect_script=crociata_effect_script_template(),
        )

    def _carta_pg(self, nome, codice, *, tags=None, testo="", personaggio=None):
        pg = personaggio or self.pg_a
        c = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice=codice,
            nome=nome,
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=2,
            salute=3,
            testo_gioco=testo,
        )
        if tags:
            c.tags.set(tags)
        return CartaPosseduta.objects.create(personaggio=pg, carta=c)

    def test_cavalleria_buffa_cavalieri(self):
        cav = self._carta_pg("Cavaliere", "CAV-1", tags=[self.tag_cav])
        ped = self._carta_pg("Pedone", "PED-1")
        evt = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="EVT-CAV",
            nome="Ordine cavalleria",
            tipo=CARTA_TIPO_EVENTO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=0,
            testo_gioco="Cavalleria 1.",
        )
        cp_evt = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=evt)
        filler = [
            str(self._carta_pg(f"F{i}", f"F{i}").id) for i in range(14)
        ]
        mazzo = [str(cp_evt.id)] + filler

        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo,
            mazzo_sfidato_ids=mazzo,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["mano"] = [str(cp_evt.id)]
        duello.stato_gioco[key_a]["energia"] = 5
        duello.stato_gioco[key_a]["eroi"][0] = str(cav.id)
        duello.stato_gioco[key_a]["eroi"][1] = str(ped.id)
        duello.stato_gioco[key_a]["salute_eroi"] = [3, 3]
        duello.save()

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "gioca_carta",
            {"carta_posseduta_id": str(cp_evt.id)},
        )
        duello.refresh_from_db()
        lato = duello.stato_gioco[key_a]
        stats_cav = _stats_eroe_slot(duello, self.pg_a, lato, 0)
        stats_ped = _stats_eroe_slot(duello, self.pg_a, lato, 1)
        self.assertEqual(stats_cav["forza"], 3)
        self.assertEqual(stats_cav["robustezza"], 4)
        self.assertEqual(stats_ped["forza"], 2)
        self.assertEqual(stats_ped["robustezza"], 3)

    def test_crociata_distrugge_non_cavalieri(self):
        cav = self._carta_pg("Cavaliere", "CAV-2", tags=[self.tag_cav])
        ped_a = self._carta_pg("Pedone A", "PED-A")
        ped_b = self._carta_pg("Pedone B", "PED-B", personaggio=self.pg_b)
        evt = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="EVT-CRO",
            nome="Crociata",
            tipo=CARTA_TIPO_EVENTO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=0,
            testo_gioco="Crociata.",
        )
        cp_evt = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=evt)
        filler = [str(self._carta_pg(f"X{i}", f"X{i}").id) for i in range(14)]
        mazzo = [str(cp_evt.id)] + filler

        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo,
            mazzo_sfidato_ids=mazzo,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a, key_b = _pg_key(self.pg_a), _pg_key(self.pg_b)
        duello.stato_gioco[key_a]["mano"] = [str(cp_evt.id)]
        duello.stato_gioco[key_a]["energia"] = 5
        duello.stato_gioco[key_a]["eroi"][0] = str(cav.id)
        duello.stato_gioco[key_a]["eroi"][1] = str(ped_a.id)
        duello.stato_gioco[key_b]["eroi"][0] = str(ped_b.id)
        duello.save()

        esegui_azione_duello(
            duello.id,
            self.pg_a,
            "gioca_carta",
            {"carta_posseduta_id": str(cp_evt.id)},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco[key_a]["eroi"][0], str(cav.id))
        self.assertIsNone(duello.stato_gioco[key_a]["eroi"][1])
        self.assertIsNone(duello.stato_gioco[key_b]["eroi"][0])
