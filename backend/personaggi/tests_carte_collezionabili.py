"""
Test carte collezionabili — bustine, reliquiario, validazione mazzo, accesso 3 stati.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from personaggi.carte_collezionabili_models import (
    BustinaCarte,
    ConfigurazioneCarteCollezionabili,
    CARTA_ENERGIA_INNATA,
    CARTA_ENERGIA_MAGICA,
    CARTA_ENERGIA_MARZIALE,
    CARTA_ENERGIA_SACRA,
    CARTA_ENERGIA_TECNOLOGICA,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_EVENTO,
    CARTA_TIPO_LUOGO,
    CARTA_TIPO_OGGETTO,
    CARTA_TIPO_PERSONAGGIO,
    CARTE_ACCESSO_OFF,
    CARTE_ACCESSO_OPEN,
    CARTE_ACCESSO_TEST,
    CartaCollezionabile,
    CartaPosseduta,
    EspansioneCarte,
    KeywordCarta,
    MAZZO_DUELLO_SIZE,
    ReliquiarioSlot,
)
from personaggi.carte_collezionabili_service import (
    _pool_carte,
    apri_bustina,
    build_collezione_payload,
    descrizione_regole_mazzo_duello,
    equip_reliquio,
    is_carte_collezionabili_abilitate,
    get_tema_energie_carte,
    lista_keywords_campagna,
    personaggio_puo_accedere_carte,
    salva_mazzo_duello,
    valida_leader_duello,
    valida_mazzo_duello,
    valida_setup_duello,
)
from personaggi.carte_errata_runtime import gameplay_view
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

    def test_apri_bustina_bloccata_fuori_finestra_vendita(self):
        self.espansione.in_vendita = False
        self.espansione.vendita_dal = timezone.now()
        self.espansione.save(update_fields=["in_vendita", "vendita_dal", "updated_at"])
        with self.assertRaises(ValidationError):
            apri_bustina(self.pg, self.bustina.id)

    def test_equip_reliquio(self):
        cp = CartaPosseduta.objects.create(
            personaggio=self.pg,
            carta=CartaCollezionabile.objects.first(),
        )
        payload = equip_reliquio(self.pg, 0, str(cp.id))
        self.assertEqual(payload["reliquiario"]["0"], str(cp.id))
        slot = ReliquiarioSlot.objects.get(personaggio=self.pg, slot_index=0)
        self.assertEqual(slot.carta_posseduta_id, cp.id)

    def test_equip_reliquio_stessa_carta_catalogo(self):
        carta = CartaCollezionabile.objects.first()
        cp1 = CartaPosseduta.objects.create(personaggio=self.pg, carta=carta)
        cp2 = CartaPosseduta.objects.create(personaggio=self.pg, carta=carta)
        equip_reliquio(self.pg, 0, str(cp1.id))
        with self.assertRaises(ValidationError):
            equip_reliquio(self.pg, 1, str(cp2.id))

    def test_build_collezione(self):
        cp = CartaPosseduta.objects.create(
            personaggio=self.pg,
            carta=CartaCollezionabile.objects.first(),
        )
        equip_reliquio(self.pg, 1, str(cp.id))
        payload = build_collezione_payload(self.pg)
        self.assertEqual(len(payload["carte"]), 1)
        self.assertIn("legami_attivi", payload)
        self.assertIn("regole_mazzo", payload)
        self.assertGreaterEqual(len(payload["regole_mazzo"]), 5)
        self.assertTrue(payload["puo_accedere"])

    def test_build_collezione_nasconde_carte_espansione_disattiva(self):
        cp = CartaPosseduta.objects.create(
            personaggio=self.pg,
            carta=CartaCollezionabile.objects.first(),
        )
        self.assertIsNotNone(cp.id)
        self.espansione.attiva = False
        self.espansione.save(update_fields=["attiva", "updated_at"])
        payload = build_collezione_payload(self.pg)
        self.assertEqual(len(payload["carte"]), 0)

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


class BustinaCarteStaffApiTests(APITestCase):
    url = "/api/personaggi/api/staff/carte/bustine/"

    def setUp(self):
        from personaggi.bustina_carte_avista import ensure_bustina_qr
        from personaggi.models import CAMPAGNA_ROLE_MASTER, CampagnaUtente

        self.user = User.objects.create_user(username="bust_staff", password="x")
        self.campagna = Campagna.objects.create(slug="bust-test", nome="Bust Test", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OPEN,
            abilitata=True,
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.user, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )
        self.espansione = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Demo",
            slug="demo-bust",
            attiva=True,
        )
        self.bustina = BustinaCarte.objects.create(
            campagna=self.campagna,
            espansione=self.espansione,
            nome="Bustina test",
            costo_crediti=50,
            carte_per_bustina=5,
            attiva=True,
        )
        ensure_bustina_qr(self.bustina)
        self.client.force_authenticate(user=self.user)

    def test_list_bustine_serializza_qr_stringa(self):
        resp = self.client.get(self.url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0]["qr_code_id"], str)
        self.assertTrue(items[0]["qr_code_id"])


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


class EspansioneCarteStaffApiTests(APITestCase):
    url = "/api/personaggi/api/staff/carte/espansioni/"

    def setUp(self):
        from personaggi.models import CAMPAGNA_ROLE_MASTER, CampagnaUtente

        self.user = User.objects.create_user(username="esp_staff", password="x")
        self.campagna = Campagna.objects.create(slug="esp-test", nome="ESP Test", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OPEN,
            abilitata=True,
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.user, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )
        self.client.force_authenticate(user=self.user)

    def test_create_senza_campagna_payload(self):
        resp = self.client.post(
            self.url,
            {
                "nome": "Espansione test",
                "slug": "espansione-test",
                "attiva": True,
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["nome"], "Espansione test")

    def test_create_slug_duplicato_400(self):
        EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Esistente",
            slug="dup-slug",
        )
        resp = self.client.post(
            self.url,
            {"nome": "Altro", "slug": "dup-slug", "attiva": True},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("slug", resp.data)

    def test_create_vendita_vuote_non_400(self):
        resp = self.client.post(
            self.url,
            {
                "nome": "Finestra vendita",
                "slug": "finestra-vendita",
                "vendita_dal": "",
                "vendita_al": "",
                "attiva": True,
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class CartaCatalogoOpenLockApiTests(APITestCase):
    base_url = "/api/personaggi/api/staff/carte/catalogo/"

    def setUp(self):
        from personaggi.models import CAMPAGNA_ROLE_MASTER, CampagnaUtente

        self.user = User.objects.create_user(username="open_lock_staff", password="x")
        self.campagna = Campagna.objects.create(slug="open-lock", nome="OPEN Lock", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OPEN,
            abilitata=True,
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.user, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )
        self.carta = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="LOCK-001",
            nome="Carta Lock",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            testo_gioco="Base",
            testo_reliquiario="Rel base",
            attacco=1,
            salute=1,
        )
        self.client.force_authenticate(user=self.user)

    def test_open_blocca_modifica_gameplay(self):
        resp = self.client.patch(
            f"{self.base_url}{self.carta.id}/",
            {"testo_gioco": "Nuovo testo gameplay"},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("OPEN", str(resp.data))

    def test_open_permette_modifica_reliquiario(self):
        resp = self.client.patch(
            f"{self.base_url}{self.carta.id}/",
            {"testo_reliquiario": "Nuovo reliquiario"},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.carta.refresh_from_db()
        self.assertEqual(self.carta.testo_reliquiario, "Nuovo reliquiario")


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


class CarteEsempioSeedTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="seed-carte", nome="Seed Carte", attiva=True)

    def test_seed_carte_esempio_idempotente(self):
        from personaggi.carte_collezionabili_models import CARTA_TIPO_EVENTO, CARTA_TIPO_LUOGO, CARTA_TIPO_OGGETTO, CARTA_TIPO_PERSONAGGIO
        from personaggi.carte_esempio_seed import seed_carte_esempio

        stats1 = seed_carte_esempio(campagna_slug="seed-carte")
        self.assertEqual(stats1["carte_create"], 20)
        self.assertGreaterEqual(stats1["keywords_create"], 5)

        stats2 = seed_carte_esempio(campagna_slug="seed-carte", skip_if_complete=True)
        self.assertTrue(stats2["skipped"])

        self.assertEqual(
            CartaCollezionabile.objects.filter(campagna=self.campagna).count(),
            20,
        )
        self.assertEqual(
            CartaCollezionabile.objects.filter(
                campagna=self.campagna, tipo=CARTA_TIPO_PERSONAGGIO
            ).count(),
            10,
        )
        self.assertEqual(
            CartaCollezionabile.objects.filter(
                campagna=self.campagna, tipo=CARTA_TIPO_OGGETTO
            ).count(),
            2,
        )
        self.assertEqual(
            CartaCollezionabile.objects.filter(
                campagna=self.campagna, tipo=CARTA_TIPO_EVENTO
            ).count(),
            6,
        )
        self.assertEqual(
            CartaCollezionabile.objects.filter(
                campagna=self.campagna, tipo=CARTA_TIPO_LUOGO
            ).count(),
            2,
        )
        esp = EspansioneCarte.objects.get(campagna=self.campagna, slug="sette-elegie-demo")
        self.assertEqual(esp.carte.count(), 20)
        self.assertTrue(
            KeywordCarta.objects.filter(campagna=self.campagna, codice="COLPO").exists()
        )
        bustina = BustinaCarte.objects.get(campagna=self.campagna, nome="Sette Elegie — bustina demo")
        self.assertEqual(bustina.espansione.slug, "sette-elegie-demo")
        self.assertEqual(bustina.carte_per_bustina, 5)
        self.assertIsNotNone(bustina.qr_code_id)


class ValidazioneMazzoDuelloTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mazzo_val", password="x")
        self.campagna = Campagna.objects.create(slug="mazzo-val", nome="Mazzo Val", attiva=True)
        tipo = TipologiaPersonaggio.objects.create(nome="Umano")
        self.pg = Personaggio.objects.create(
            nome="Tester",
            proprietario=self.user,
            campagna=self.campagna,
            tipologia=tipo,
        )

    def _carta(self, codice, tipo, energia, nome=None):
        c = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice=codice,
            nome=nome or codice,
            tipo=tipo,
            energia=energia,
            rarita=CARTA_RARITA_COMUNE,
            attacco=2 if tipo == CARTA_TIPO_PERSONAGGIO else None,
            salute=2 if tipo == CARTA_TIPO_PERSONAGGIO else None,
            costo_gioco=1,
        )
        return CartaPosseduta.objects.create(personaggio=self.pg, carta=c)

    def _mazzo_valido_ids(self):
        specs = (
            [(CARTA_TIPO_PERSONAGGIO, CARTA_ENERGIA_MARZIALE)] * 4
            + [(CARTA_TIPO_PERSONAGGIO, CARTA_ENERGIA_SACRA)] * 4
            + [(CARTA_TIPO_LUOGO, CARTA_ENERGIA_SACRA)] * 2
            + [(CARTA_TIPO_EVENTO, CARTA_ENERGIA_SACRA)] * 3
            + [(CARTA_TIPO_OGGETTO, CARTA_ENERGIA_MARZIALE)] * 2
        )
        return [str(self._carta(f"MV-{i}", t, e).id) for i, (t, e) in enumerate(specs)]

    def _leader_id(self):
        return str(
            self._carta(
                f"MV-LEADER-{id(self)}",
                CARTA_TIPO_PERSONAGGIO,
                CARTA_ENERGIA_MARZIALE,
                nome="Leader test",
            ).id
        )

    def test_mazzo_valido_regolamento(self):
        ok, errs = valida_setup_duello(self._mazzo_valido_ids(), self._leader_id(), self.pg)
        self.assertTrue(ok, errs)

    def test_descrizione_regole_non_vuota(self):
        regole = descrizione_regole_mazzo_duello()
        self.assertGreaterEqual(len(regole), 5)
        self.assertTrue(any("8" in r for r in regole))

    def test_troppo_pochi_personaggi(self):
        ids = self._mazzo_valido_ids()
        extra_evt1 = str(self._carta("EVT-X1", CARTA_TIPO_EVENTO, CARTA_ENERGIA_SACRA).id)
        extra_evt2 = str(self._carta("EVT-X2", CARTA_TIPO_EVENTO, CARTA_ENERGIA_SACRA).id)
        bad = [extra_evt1, extra_evt2] + ids[2:]
        ok, errs = valida_mazzo_duello(bad, self.pg)
        self.assertFalse(ok)
        self.assertTrue(any("Personaggi" in e for e in errs))

    def test_troppe_terre(self):
        ids = self._mazzo_valido_ids()
        extra_luo1 = str(self._carta("LUO-3", CARTA_TIPO_LUOGO, CARTA_ENERGIA_SACRA).id)
        extra_luo2 = str(self._carta("LUO-4", CARTA_TIPO_LUOGO, CARTA_ENERGIA_SACRA).id)
        # 2 terre nel mazzo valido + 2 extra al posto di 1 effetto e 1 equip
        bad = ids[:11] + [extra_luo1, extra_luo2] + ids[13:]
        ok, errs = valida_mazzo_duello(bad, self.pg)
        self.assertFalse(ok)
        self.assertTrue(any("Terre" in e for e in errs))

    def test_troppe_aure(self):
        ids = []
        energie = [
            CARTA_ENERGIA_MARZIALE,
            CARTA_ENERGIA_TECNOLOGICA,
            CARTA_ENERGIA_INNATA,
            CARTA_ENERGIA_MAGICA,
        ]
        for i in range(MAZZO_DUELLO_SIZE):
            cp = self._carta(f"A4-{i}", CARTA_TIPO_PERSONAGGIO, energie[i % 4])
            ids.append(str(cp.id))
        ok, errs = valida_mazzo_duello(ids, self.pg)
        self.assertFalse(ok)
        self.assertTrue(any("aure" in e.lower() for e in errs))

    def test_manca_aura_soprannaturale(self):
        ids = [str(self._carta(f"NAT-{i}", CARTA_TIPO_PERSONAGGIO, CARTA_ENERGIA_MARZIALE).id)
               for i in range(MAZZO_DUELLO_SIZE)]
        ok, errs = valida_mazzo_duello(ids, self.pg)
        self.assertFalse(ok)
        self.assertTrue(any("Soprannaturale" in e for e in errs))

    def test_equip_senza_personaggio_aura(self):
        ids = self._mazzo_valido_ids()
        cp_mag = self._carta("OGG-MAG", CARTA_TIPO_OGGETTO, CARTA_ENERGIA_MAGICA)
        bad = ids[:14] + [str(cp_mag.id)]
        ok, errs = valida_mazzo_duello(bad, self.pg)
        self.assertFalse(ok)
        self.assertTrue(any("Equipaggiamento" in e and "Magica" in e for e in errs))

    def test_leader_obbligatorio(self):
        ok, errs = valida_leader_duello(None, self.pg)
        self.assertFalse(ok)
        self.assertTrue(any("Leader" in e for e in errs))

    def test_leader_non_nel_mazzo(self):
        ids = self._mazzo_valido_ids()
        ok, errs = valida_leader_duello(ids[0], self.pg, ids)
        self.assertFalse(ok)
        self.assertTrue(any("non può essere incluso" in e for e in errs))

    def test_salva_mazzo_con_leader(self):
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OPEN,
            abilitata=True,
        )
        leader_id = self._leader_id()
        res = salva_mazzo_duello(
            self.pg,
            self._mazzo_valido_ids(),
            leader_carta_posseduta_id=leader_id,
            nome="Test leader",
        )
        mazzo = next(m for m in res["mazzi"] if m["nome"] == "Test leader")
        self.assertEqual(mazzo["leader_carta_posseduta_id"], leader_id)

    def test_blocca_carta_bandita(self):
        ids = self._mazzo_valido_ids()
        cp = CartaPosseduta.objects.select_related("carta").get(pk=ids[0])
        cp.carta.bandita = True
        cp.carta.ban_reason = "Carta troppo dominante"
        cp.carta.save(update_fields=["bandita", "ban_reason", "updated_at"])
        ok, errs = valida_mazzo_duello(ids, self.pg)
        self.assertFalse(ok)
        self.assertTrue(any("bandita" in e.lower() for e in errs))

    def test_blocca_espansione_non_legale_duello(self):
        ids = self._mazzo_valido_ids()
        cp = CartaPosseduta.objects.select_related("carta__espansione").get(pk=ids[0])
        esp = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="No Duel",
            slug="no-duel",
            legale_duello=False,
        )
        cp.carta.espansione = esp
        cp.carta.save(update_fields=["espansione", "updated_at"])
        ok, errs = valida_mazzo_duello(ids, self.pg)
        self.assertFalse(ok)
        self.assertTrue(any("non legale" in e.lower() for e in errs))


class CartaErrataRuntimeTests(TestCase):
    def setUp(self):
        from django.utils import timezone
        from personaggi.carte_collezionabili_models import CartaErrata

        self.user = User.objects.create_user(username="errata_user", password="x")
        self.campagna = Campagna.objects.create(slug="errata-camp", nome="Errata Camp", attiva=True)
        self.carta = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="ERR-001",
            nome="Carta Errata",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=3,
            attacco=2,
            salute=4,
            iniziativa=1,
            testo_gioco="Testo originale",
        )
        CartaErrata.objects.create(
            campagna=self.campagna,
            carta=self.carta,
            effective_from=timezone.now(),
            titolo="Nerf",
            testo_gioco_override="Testo erratato",
            costo_gioco_override=1,
            attacco_override=1,
        )

    def test_gameplay_view_applica_errata_attiva(self):
        eff = gameplay_view(self.carta)
        self.assertEqual(eff["costo_gioco"], 1)
        self.assertEqual(eff["attacco"], 1)
        self.assertEqual(eff["testo_gioco"], "Testo erratato")
        self.assertIsNotNone(eff["errata"])
