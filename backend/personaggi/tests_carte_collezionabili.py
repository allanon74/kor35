"""
Test carte collezionabili — bustine, reliquiario, validazione mazzo, accesso 3 stati.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from personaggi.carte_collezionabili_models import (
    BustinaCarte,
    ConfigurazioneCarteCollezionabili,
    CARTA_ENERGIA_MARZIALE,
    CARTA_ENERGIA_SACRA,
    CARTA_ENERGIA_TECNOLOGICA,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_PERSONAGGIO,
    CARTE_ACCESSO_OFF,
    CARTE_ACCESSO_OPEN,
    CARTE_ACCESSO_TEST,
    CartaCollezionabile,
    CartaPosseduta,
    EspansioneCarte,
    KeywordCarta,
    ReliquiarioSlot,
)
from personaggi.carte_collezionabili_service import (
    _pool_carte,
    apri_bustina,
    build_collezione_payload,
    equip_reliquio,
    is_carte_collezionabili_abilitate,
    get_tema_energie_carte,
    lista_keywords_campagna,
    personaggio_puo_accedere_carte,
    valida_mazzo_duello,
)
from personaggi.models import AURA, Campagna, Personaggio, Punteggio, TipologiaPersonaggio
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class CarteCollezionabiliServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carte_test", password="test")
        self.campagna = Campagna.objects.create(slug="kor35-test", nome="Kor35 Test", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OPEN,
            abilitata=True,
        )
        self.tipologia = TipologiaPersonaggio.objects.create(nome="Umano", giocante=True)
        self.tipologia_png = TipologiaPersonaggio.objects.create(nome="PNG Staff", giocante=False)
        self.espansione = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Set Test",
            slug="test-set",
        )
        self.pg = Personaggio.objects.create(
            nome="Tester",
            proprietario=self.user,
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        self.png_staff = Personaggio.objects.create(
            nome="PNG Staff",
            proprietario=self.user,
            campagna=self.campagna,
            tipologia=self.tipologia_png,
        )
        self.pg.modifica_crediti(Decimal("5000"), "Setup test")

        for sigla, nome, colore in [
            ("AMZ", "Aura Marziale Test", "#4C36F5"),
            ("ATE", "Aura Tecnologica Test", "#FAF610"),
            ("AIN", "Aura Innata Test", "#C79E0B"),
            ("AMA", "Aura Magica Test", "#000000"),
            ("ASA", "Aura Sacra Test", "#FFFFFF"),
            ("APS", "Aura Psionica Test", "#EFAAFF"),
            ("AAR", "Aura Arcana Test", "#92FA88"),
        ]:
            Punteggio.objects.get_or_create(
                sigla=sigla,
                defaults={"nome": nome, "tipo": AURA, "colore": colore},
            )

        for i in range(10):
            CartaCollezionabile.objects.create(
                campagna=self.campagna,
                codice=f"TEST-{i:03d}",
                nome=f"Carta {i}",
                tipo=CARTA_TIPO_PERSONAGGIO,
                energia=CARTA_ENERGIA_MARZIALE if i % 2 == 0 else CARTA_ENERGIA_SACRA,
                rarita=CARTA_RARITA_COMUNE,
                attacco=2,
                salute=3,
                set_collezione="test-set",
                espansione=self.espansione,
            )

        self.bustina = BustinaCarte.objects.create(
            campagna=self.campagna,
            nome="Bustina test",
            costo_crediti=Decimal("500"),
            carte_per_bustina=5,
            set_collezione="test-set",
            espansione=self.espansione,
        )

    def test_apri_bustina(self):
        crediti_prima = self.pg.crediti
        result = apri_bustina(self.pg, self.bustina.id)
        self.pg.refresh_from_db()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["carte"]), 5)
        self.assertEqual(self.pg.carte_possedute.count(), 5)
        self.assertEqual(self.pg.crediti, crediti_prima - Decimal("500"))

    def test_equip_reliquio(self):
        cp = CartaPosseduta.objects.create(
            personaggio=self.pg,
            carta=CartaCollezionabile.objects.first(),
        )
        payload = equip_reliquio(self.pg, 0, str(cp.id))
        self.assertEqual(payload["reliquiario"]["0"], str(cp.id))
        slot = ReliquiarioSlot.objects.get(personaggio=self.pg, slot_index=0)
        self.assertEqual(slot.carta_posseduta_id, cp.id)

    def test_build_collezione(self):
        cp = CartaPosseduta.objects.create(
            personaggio=self.pg,
            carta=CartaCollezionabile.objects.first(),
        )
        equip_reliquio(self.pg, 1, str(cp.id))
        payload = build_collezione_payload(self.pg)
        self.assertEqual(len(payload["carte"]), 1)
        self.assertIn("legami_attivi", payload)
        self.assertTrue(payload["puo_accedere"])

    def test_valida_mazzo_insufficiente(self):
        carte = []
        for i in range(5):
            c = CartaCollezionabile.objects.create(
                campagna=self.campagna,
                codice=f"MAZZO-{i}",
                nome=f"Mazzo {i}",
                tipo=CARTA_TIPO_PERSONAGGIO,
                energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE,
            )
            cp = CartaPosseduta.objects.create(personaggio=self.pg, carta=c)
            carte.append(str(cp.id))
        ok, errs = valida_mazzo_duello(carte, self.pg)
        self.assertFalse(ok)
        self.assertTrue(any("15" in e for e in errs))

    def test_crediti_insufficienti(self):
        self.pg.modifica_crediti(-self.pg.crediti, "Azzera")
        with self.assertRaises(ValidationError):
            apri_bustina(self.pg, self.bustina.id)

    def test_accesso_off(self):
        ConfigurazioneCarteCollezionabili.objects.filter(campagna=self.campagna).update(
            accesso_modo=CARTE_ACCESSO_OFF,
            abilitata=False,
        )
        self.assertFalse(is_carte_collezionabili_abilitate(self.campagna))
        self.assertFalse(personaggio_puo_accedere_carte(self.pg))
        payload = build_collezione_payload(self.pg)
        self.assertFalse(payload["puo_accedere"])
        with self.assertRaises(ValidationError):
            apri_bustina(self.pg, self.bustina.id)

    def test_accesso_test_solo_png_staff(self):
        ConfigurazioneCarteCollezionabili.objects.filter(campagna=self.campagna).update(
            accesso_modo=CARTE_ACCESSO_TEST,
            abilitata=False,
        )
        self.assertTrue(is_carte_collezionabili_abilitate(self.campagna))
        self.assertFalse(personaggio_puo_accedere_carte(self.pg))
        self.assertTrue(personaggio_puo_accedere_carte(self.png_staff))
        payload_pg = build_collezione_payload(self.pg)
        self.assertFalse(payload_pg["puo_accedere"])
        payload_png = build_collezione_payload(self.png_staff)
        self.assertTrue(payload_png["puo_accedere"])
        self.png_staff.modifica_crediti(Decimal("5000"), "Setup PNG")
        with self.assertRaises(ValidationError):
            apri_bustina(self.pg, self.bustina.id)
        result = apri_bustina(self.png_staff, self.bustina.id)
        self.assertEqual(result["status"], "ok")

    def test_pool_bustina_filtra_per_espansione(self):
        altra_esp = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Altra espansione",
            slug="altra-esp",
        )
        CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="ALT-001",
            nome="Carta altra espansione",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_TECNOLOGICA,
            rarita=CARTA_RARITA_COMUNE,
            espansione=altra_esp,
        )
        pool = _pool_carte(self.bustina)
        self.assertTrue(pool)
        self.assertTrue(all(c.espansione_id == self.espansione.id for c in pool))

    def test_progress_espansioni(self):
        cp = CartaPosseduta.objects.create(
            personaggio=self.pg,
            carta=CartaCollezionabile.objects.first(),
        )
        payload = build_collezione_payload(self.pg)
        self.assertTrue(any(p["slug"] == "test-set" for p in payload.get("progress_espansioni", [])))

    def test_tema_energie_da_db(self):
        tema = get_tema_energie_carte()
        self.assertIn("MAR", tema)
        self.assertEqual(tema["MAR"]["sigla"], "AMZ")
        self.assertTrue(tema["MAR"]["colore"])
        self.assertIn("TEC", tema)
        self.assertEqual(tema["TEC"]["sigla"], "ATE")

    def test_keywords_in_collezione_payload(self):
        KeywordCarta.objects.create(
            campagna=self.campagna,
            codice="EVOCAZIONE",
            nome="Evocazione",
            testo_regola="Metti in gioco una carta dalla mano.",
            reminder_breve="dalla mano",
            priorita=10,
        )
        payload = build_collezione_payload(self.pg)
        self.assertEqual(len(payload["keywords"]), 1)
        self.assertEqual(payload["keywords"][0]["codice"], "EVOCAZIONE")
        self.assertEqual(lista_keywords_campagna(self.campagna)[0]["nome"], "Evocazione")


class KeywordCartaStaffApiTests(APITestCase):
    url = "/api/personaggi/api/staff/carte/keywords/"

    def setUp(self):
        from personaggi.models import CAMPAGNA_ROLE_MASTER, CampagnaUtente

        self.user = User.objects.create_user(username="kw_staff", password="x")
        self.campagna = Campagna.objects.create(slug="kw-test", nome="KW Test", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OPEN,
            abilitata=True,
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.user, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )
        self.client.force_authenticate(user=self.user)

    def test_create_and_list_keyword(self):
        resp = self.client.post(
            self.url,
            {
                "codice": "RAPIDAMENTE",
                "nome": "Rapidamente",
                "testo_regola": "Puoi giocare questa carta come se fosse un'azione veloce.",
                "reminder_breve": "azione veloce",
                "priorita": 5,
                "attiva": True,
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["codice"], "RAPIDAMENTE")

        list_resp = self.client.get(self.url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        items = list_resp.data if isinstance(list_resp.data, list) else list_resp.data.get("results", [])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["nome"], "Rapidamente")

    def test_create_keyword_parametrizzata(self):
        resp = self.client.post(
            self.url,
            {
                "codice": "MUTAZIONE",
                "nome": "Mutazione [X]",
                "testo_regola": (
                    "Quando questo personaggio si esaurisce, sostituiscilo con una carta fino a costo [X]."
                ),
                "attiva": True,
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["nome"], "Mutazione [X]")


class KeywordCartaParametriTests(TestCase):
    def test_mutazione_parametrica(self):
        from personaggi.carte_keyword_utils import (
            match_keyword_parametrizzata,
            substituisci_parametri_keyword,
        )

        template = "Mutazione [X]"
        regola = "Quando questo personaggio si esaurisce, sostituiscilo con una carta fino a costo [X]."
        m = match_keyword_parametrizzata(template, "Alla morte: Mutazione 0 sul campo.", 12)
        self.assertIsNotNone(m)
        self.assertEqual(m["matched"], "Mutazione 0")
        self.assertEqual(m["params"]["X"], "0")
        risolto = substituisci_parametri_keyword(regola, m["params"])
        self.assertIn("costo 0", risolto)
        self.assertNotIn("[X]", risolto)

    def test_keyword_model_parametrizzata(self):
        kw = KeywordCarta(
            campagna=Campagna.objects.create(slug="kw-par", nome="KW Par", attiva=True),
            codice="MUTAZIONE",
            nome="Mutazione [X]",
            testo_regola="Quando questo personaggio si esaurisce, sostituiscilo con una carta fino a costo [X].",
        )
        self.assertTrue(kw.is_parametrizzata())
