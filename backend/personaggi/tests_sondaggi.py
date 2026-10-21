"""Parser Google Form, API giocatore e copia sul foglio."""
import json
import os
from unittest.mock import patch
from urllib.parse import parse_qs

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    Campagna,
    CampagnaUtente,
    Personaggio,
    TipologiaPersonaggio,
)
from personaggi.sondaggi_google import (
    ErroreModuloGoogle,
    analizza_html_modulo,
    costruisci_corpo_invio,
    inoltra_risposta_a_google,
    normalizza_url_modulo,
)
from personaggi.sondaggi_models import RispostaSondaggio, Sondaggio
from personaggi.sondaggi_service import eroga_premi_mancanti, registra_risposta, valida_risposte

FORM_ID = "1FAIpQLSabcDEFghiJKLmnop"
FORM_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform?usp=sharing"


def _html_modulo():
    dati = [
        None,
        [
            "Dicci come è andata.",
            [
                [101, "Nome in gioco", None, 0, [[1475351979, None, 1]]],
                [102, "Note", None, 1, [[2001, None, 0]]],
                [103, "Ruolo", None, 2, [[3001, [["Tank", None], ["Healer", None]], 1]]],
                [104, "Turno", None, 3, [[4001, [["Mattina", None], ["Sera", None]], 0]]],
                [105, "Attività", None, 4, [[5001, [["Combattuto", None], ["Esplorato", None]], 1]]],
                [106, "Voto", None, 5, [[6001, None, 1, None, None, None, None, None, [1, 5], ["Male", "Bene"]]]],
                [107, "Data", None, 9, [[7001, None, 0]]],
                [108, "Ora", None, 10, [[8001, None, 0]]],
                [109, "Quasi fatto", "Ultimo blocco", 8, None],
                [111, "Missioni", None, 18, [[9101, [["1", None], ["2", None], ["3", None], ["4", None], ["5", None]], 1]]],
                [110, "Carica un file", None, 13, [[9001, None, 1]]],
            ],
            None,
            None,
            None,
            [0, 0],
            None,
            None,
            "Chiusura evento",
        ],
    ]
    return f"<html><script>var FB_PUBLIC_LOAD_DATA_ = {json.dumps(dati)};</script></html>"


class ParserSondaggioTests(SimpleTestCase):
    def test_normalizza_solo_link_pubblico(self):
        canonico, form_id = normalizza_url_modulo(FORM_URL)
        self.assertEqual(form_id, FORM_ID)
        self.assertTrue(canonico.endswith("/viewform"))
        with self.assertRaises(ErroreModuloGoogle):
            normalizza_url_modulo("https://evil.example/forms/d/e/abcdefghijklmnop/viewform")
        with self.assertRaises(ErroreModuloGoogle):
            normalizza_url_modulo("http://docs.google.com/forms/d/e/abcdefghijklmnop/viewform")
        with self.assertRaises(ErroreModuloGoogle):
            normalizza_url_modulo("https://docs.google.com/forms/d/abcdefghijklmnop/edit")

    def test_analizza_domande_e_avvisi(self):
        analisi = analizza_html_modulo(_html_modulo())
        self.assertEqual(analisi["titolo"], "Chiusura evento")
        self.assertEqual(analisi["descrizione"], "Dicci come è andata.")
        tipi = {d["titolo"]: d for d in analisi["domande"]}
        self.assertEqual(tipi["Nome in gioco"]["id"], "entry.1475351979")
        self.assertTrue(tipi["Nome in gioco"]["obbligatoria"])
        self.assertEqual(tipi["Ruolo"]["opzioni"], ["Tank", "Healer"])
        self.assertEqual(tipi["Voto"]["scala_min"], 1)
        self.assertEqual(tipi["Voto"]["scala_max_etichetta"], "Bene")
        self.assertEqual(tipi["Quasi fatto"]["tipo"], "sezione")
        self.assertEqual(tipi["Missioni"]["tipo"], "valutazione")
        self.assertTrue(tipi["Missioni"]["supportata"])
        self.assertTrue(tipi["Missioni"]["obbligatoria"])
        self.assertEqual(tipi["Missioni"]["opzioni"], ["1", "2", "3", "4", "5"])
        self.assertEqual(tipi["Missioni"]["scala_min"], 1)
        self.assertEqual(tipi["Missioni"]["scala_max"], 5)
        self.assertFalse(any("Missioni" in voce for voce in analisi["avvisi"]))
        self.assertFalse(tipi["Carica un file"]["supportata"])
        self.assertTrue(any("Carica un file" in voce for voce in analisi["avvisi"]))

    def test_valutazione_tre_stelle_e_default(self):
        dati = [
            None,
            [
                "",
                [
                    [1, "Breve", None, 18, [[11, [[1], [2], [3]], 0]]],
                    [2, "Vuota", None, 18, [[12, None, 0]]],
                ],
                None, None, None, [0, 0], None, None, "Voti",
            ],
        ]
        html = f"<html><script>var FB_PUBLIC_LOAD_DATA_ = {json.dumps(dati)};</script></html>"
        tipi = {d["titolo"]: d for d in analizza_html_modulo(html)["domande"]}
        self.assertEqual(tipi["Breve"]["opzioni"], ["1", "2", "3"])
        self.assertEqual(tipi["Breve"]["scala_max"], 3)
        self.assertEqual(tipi["Vuota"]["opzioni"], ["1", "2", "3", "4", "5"])
        self.assertTrue(tipi["Vuota"]["supportata"])

    def test_griglia_scelta_per_riga(self):
        dati = [
            None,
            [
                "",
                [
                    [1, "Come valuti le missioni legate ai voli della Mist Glider?", None, 7, [
                        [1059234330, [["Scadente"], ["Insufficiente"], ["Discreto"], ["Buono"], ["Ottimo"]], 1, ["Divertimento"], None, None, None, None, None, None, None, [0]],
                        [195821262, [["Scadente"], ["Insufficiente"], ["Discreto"], ["Buono"], ["Ottimo"]], 1, ["Qualità "], None, None, None, None, None, None, None, [0]],
                        [620368220, [["Scadente"], ["Insufficiente"], ["Discreto"], ["Buono"], ["Ottimo"]], 1, ["Immersione"], None, None, None, None, None, None, None, [0]],
                    ]],
                    [2, "Gli incontri con i PNG ti sono sembrati equilibrati e coerenti con la storia?", None, 7, [
                        [1510955258, [["per nulla"], ["poco"], ["discretamente"], ["molto"], ["perfettamente"]], 1, ["Equilibrio"]],
                        [1096896749, [["per nulla"], ["poco"], ["discretamente"], ["molto"], ["perfettamente"]], 1, ["Coerenza"]],
                    ]],
                ],
                None, None, None, [0, 0], None, None, "Feedback",
            ],
        ]
        html = f"<html><script>var FB_PUBLIC_LOAD_DATA_ = {json.dumps(dati)};</script></html>"
        analisi = analizza_html_modulo(html)
        tipi = {d["titolo"]: d for d in analisi["domande"]}
        voli = tipi["Come valuti le missioni legate ai voli della Mist Glider?"]
        png = tipi["Gli incontri con i PNG ti sono sembrati equilibrati e coerenti con la storia?"]
        self.assertEqual(voli["tipo"], "griglia")
        self.assertTrue(voli["supportata"])
        self.assertEqual([r["titolo"] for r in voli["righe"]], ["Divertimento", "Qualità", "Immersione"])
        self.assertEqual(voli["righe"][0]["id"], "entry.1059234330")
        self.assertEqual(voli["righe"][0]["opzioni"][3], "Buono")
        self.assertTrue(png["supportata"])
        self.assertEqual([r["titolo"] for r in png["righe"]], ["Equilibrio", "Coerenza"])
        self.assertFalse(analisi["avvisi"])
        risposte = {
            "entry.1059234330": "Buono",
            "entry.195821262": "Ottimo",
            "entry.620368220": "Discreto",
            "entry.1510955258": "molto",
            "entry.1096896749": "perfettamente",
        }
        pulite = valida_risposte(analisi["domande"], risposte)
        self.assertEqual(pulite["entry.195821262"], "Ottimo")
        with self.assertRaises(ValidationError):
            valida_risposte(analisi["domande"], {**risposte, "entry.1096896749": "forse"})
        coppie = costruisci_corpo_invio(analisi["domande"], risposte)
        self.assertIn(("entry.1059234330", "Buono"), coppie)
        self.assertIn(("entry.1096896749", "perfettamente"), coppie)

    def test_corpo_invio_caselle_ripetute(self):
        analisi = analizza_html_modulo(_html_modulo())
        coppie = costruisci_corpo_invio(
            analisi["domande"],
            {"entry.1475351979": "Ada", "entry.5001": ["Combattuto", "Esplorato"]},
            email="ada@example.com",
        )
        self.assertIn(("entry.1475351979", "Ada"), coppie)
        self.assertIn(("entry.5001", "Combattuto"), coppie)
        self.assertIn(("entry.5001", "Esplorato"), coppie)
        self.assertIn(("emailAddress", "ada@example.com"), coppie)
        self.assertIn(("pageHistory", "0,1"), coppie)

    def test_cronologia_pagine_include_le_sezioni_successive(self):
        domande = [
            {"id": "entry.1", "tipo": "testo_breve", "supportata": True},
            {"id": "sezione-1", "tipo": "sezione", "supportata": True},
            {"id": "entry.2", "tipo": "scelta_singola", "supportata": True},
            {"id": "sezione-2", "tipo": "sezione", "supportata": True},
            {"id": "entry.3", "tipo": "testo_lungo", "supportata": True},
            {"id": "entry.4", "tipo": "scala", "supportata": True},
        ]
        coppie = costruisci_corpo_invio(
            domande,
            {"entry.1": "Ada", "entry.2": "Sì", "entry.3": "Un momento lungo", "entry.4": "4"},
        )
        self.assertIn(("entry.1", "Ada"), coppie)
        self.assertIn(("entry.2", "Sì"), coppie)
        self.assertIn(("entry.3", "Un momento lungo"), coppie)
        self.assertIn(("entry.4", "4"), coppie)
        self.assertIn(("pageHistory", "0,1,2"), coppie)


class ApiSondaggioTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.create(
            slug="kor35-sondaggi",
            nome="Kor35 Sondaggi",
            attiva=True,
        )
        cls.tipologia = TipologiaPersonaggio.objects.create(nome="Standard Sondaggi")
        cls.staff = User.objects.create_user(username="sondaggi_staff", password="x", email="staff@example.com")
        cls.player = User.objects.create_user(username="sondaggi_player", password="x", email="ada@example.com")
        CampagnaUtente.objects.create(
            campagna=cls.campagna,
            user=cls.staff,
            ruolo=CAMPAGNA_ROLE_MASTER,
            attivo=True,
        )
        cls.personaggio = Personaggio.objects.create(
            nome="Ada",
            proprietario=cls.player,
            campagna=cls.campagna,
            tipologia=cls.tipologia,
        )

    def _importa(self):
        self.client.force_authenticate(self.staff)
        with patch("personaggi.sondaggi_service.scarica_html_modulo", return_value=_html_modulo()):
            risposta = self.client.post(
                "/api/personaggi/api/staff/sondaggi/",
                {"url": FORM_URL, "attivo": True},
                format="json",
                HTTP_X_CAMPAGNA=self.campagna.slug,
            )
        self.assertIn(risposta.status_code, (200, 201), risposta.content)
        return risposta.json()

    def _risposte_valide(self):
        return {
            "entry.1475351979": "Ada",
            "entry.3001": "Tank",
            "entry.5001": ["Esplorato"],
            "entry.6001": "4",
            "entry.9101": "5",
        }

    def test_import_rifiuta_host_estraneo_senza_rete(self):
        self.client.force_authenticate(self.staff)
        risposta = self.client.post(
            "/api/personaggi/api/staff/sondaggi/",
            {"url": "https://evil.example/forms/d/e/abcdefghijklmnop/viewform", "attivo": True},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(risposta.status_code, 400)
        self.assertEqual(Sondaggio.objects.count(), 0)

    def test_giocatore_compila_una_volta_e_staff_vede(self):
        creato = self._importa()
        self.client.force_authenticate(self.player)
        stato = self.client.get(
            f"/api/personaggi/api/sondaggi/?personaggio_id={self.personaggio.id}&breve=1"
        )
        self.assertEqual(stato.status_code, 200)
        self.assertTrue(stato.json()["visibile"])
        self.assertEqual(stato.json()["da_compilare"], 1)

        scelta = self.client.post(
            f"/api/personaggi/api/sondaggi/{creato['id']}/risposta/?personaggio_id={self.personaggio.id}",
            {"risposte": {**self._risposte_valide(), "entry.3001": "Mago"}},
            format="json",
        )
        self.assertEqual(scelta.status_code, 400)
        self.assertEqual(RispostaSondaggio.objects.count(), 0)

        invio = self.client.post(
            f"/api/personaggi/api/sondaggi/{creato['id']}/risposta/?personaggio_id={self.personaggio.id}",
            {"risposte": self._risposte_valide()},
            format="json",
        )
        self.assertEqual(invio.status_code, 201, invio.content)
        self.assertTrue(invio.json()["gia_risposto"])

        doppio = self.client.post(
            f"/api/personaggi/api/sondaggi/{creato['id']}/risposta/?personaggio_id={self.personaggio.id}",
            {"risposte": self._risposte_valide()},
            format="json",
        )
        self.assertEqual(doppio.status_code, 400)

        self.client.force_authenticate(self.staff)
        dettaglio = self.client.get(
            f"/api/personaggi/api/staff/sondaggi/{creato['id']}/",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(dettaglio.status_code, 200)
        corpo = dettaglio.json()
        self.assertEqual(corpo["risposte_totali"], 1)
        self.assertEqual(corpo["risposte"][0]["personaggio"], "Ada")
        self.assertEqual(corpo["risposte"][0]["risposte"]["entry.3001"], "Tank")
        self.assertTrue(any("Carica un file" in voce for voce in corpo["avvisi"]))

    def test_modifica_consentita_azzera_invio_google(self):
        creato = self._importa()
        sondaggio = Sondaggio.objects.get(pk=creato["id"])
        sondaggio.consenti_modifica = True
        sondaggio.save(update_fields=["consenti_modifica", "updated_at"])
        risposta, creata = registra_risposta(sondaggio, self.personaggio, self.player, self._risposte_valide())
        self.assertTrue(creata)
        risposta.google_inviato_at = risposta.created_at
        risposta.save(update_fields=["google_inviato_at", "updated_at"])
        aggiornata, creata = registra_risposta(
            sondaggio,
            self.personaggio,
            self.player,
            {**self._risposte_valide(), "entry.1475351979": "Ada Due"},
        )
        self.assertFalse(creata)
        self.assertIsNone(aggiornata.google_inviato_at)
        self.assertEqual(aggiornata.risposte["entry.1475351979"], "Ada Due")

    def test_scala_fuori_range(self):
        analisi = analizza_html_modulo(_html_modulo())
        with self.assertRaises(ValidationError):
            valida_risposte(analisi["domande"], {**self._risposte_valide(), "entry.6001": "9"})

    def test_valutazione_solo_livelli_del_modulo(self):
        analisi = analizza_html_modulo(_html_modulo())
        with self.assertRaises(ValidationError):
            valida_risposte(analisi["domande"], {**self._risposte_valide(), "entry.9101": "6"})
        pulite = valida_risposte(analisi["domande"], self._risposte_valide())
        self.assertEqual(pulite["entry.9101"], "5")

    def test_inoltro_solo_su_master(self):
        creato = self._importa()
        sondaggio = Sondaggio.objects.get(pk=creato["id"])
        risposta, _ = registra_risposta(sondaggio, self.personaggio, self.player, self._risposte_valide())
        with patch.dict(os.environ, {"KOR35_SYNC_NODE_ROLE": "replica"}), patch(
            "personaggi.sondaggi_google.requests.post"
        ) as post:
            self.assertEqual(inoltra_risposta_a_google(risposta.id), "saltato_nodo")
            post.assert_not_called()
        finto = type("R", (), {"status_code": 200, "text": "Grazie", "url": f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"})()
        with patch.dict(os.environ, {"KOR35_SYNC_NODE_ROLE": "master"}), patch(
            "personaggi.sondaggi_google.requests.post", return_value=finto
        ) as post:
            self.assertEqual(inoltra_risposta_a_google(risposta.id), "inviata")
            inviato = parse_qs(post.call_args.kwargs["data"])
            self.assertEqual(inviato["entry.1475351979"], ["Ada"])
            self.assertEqual(inviato["emailAddress"], ["ada@example.com"])
        risposta.refresh_from_db()
        self.assertIsNotNone(risposta.google_inviato_at)
        self.assertEqual(RispostaSondaggio.objects.filter(pk=risposta.pk, google_inviato_at__isnull=False).count(), 1)

    def test_premio_solo_al_primo_invio(self):
        creato = self._importa()
        self.client.force_authenticate(self.staff)
        patch = self.client.patch(
            f"/api/personaggi/api/staff/sondaggi/{creato['id']}/",
            {
                "premio_pc": 2,
                "premio_crediti_correnti": "10.50",
                "premio_crediti_deposito": "3",
                "consenti_modifica": True,
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(patch.status_code, 200, patch.content)
        self.assertEqual(patch.json()["premio_pc"], 2)
        self.assertEqual(patch.json()["premio_crediti_correnti"], "10.50")
        self.assertEqual(patch.json()["premio_crediti_deposito"], "3.00")

        rifiuto = self.client.patch(
            f"/api/personaggi/api/staff/sondaggi/{creato['id']}/",
            {"premio_pc": -1},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(rifiuto.status_code, 400)

        self.client.force_authenticate(self.player)
        invio = self.client.post(
            f"/api/personaggi/api/sondaggi/{creato['id']}/risposta/?personaggio_id={self.personaggio.id}",
            {"risposte": self._risposte_valide()},
            format="json",
        )
        self.assertEqual(invio.status_code, 201, invio.content)
        ricevuto = invio.json()["premio_ricevuto"]
        self.assertEqual(ricevuto["pc"], 2)
        self.assertEqual(ricevuto["crediti_correnti"], "10.50")
        self.assertEqual(ricevuto["crediti_deposito"], "3.00")
        pg = Personaggio.objects.get(pk=self.personaggio.pk)
        self.assertEqual(pg.crediti_corrente, Decimal("10.50"))
        self.assertEqual(pg.crediti_deposito, Decimal("3.00"))
        self.assertEqual(pg.movimenti_pc.filter(descrizione__startswith="Sondaggio").count(), 1)

        aggiorna = self.client.post(
            f"/api/personaggi/api/sondaggi/{creato['id']}/risposta/?personaggio_id={self.personaggio.id}",
            {"risposte": {**self._risposte_valide(), "entry.1475351979": "Ada Due"}},
            format="json",
        )
        self.assertEqual(aggiorna.status_code, 200, aggiorna.content)
        pg = Personaggio.objects.get(pk=self.personaggio.pk)
        self.assertEqual(pg.crediti_corrente, Decimal("10.50"))
        self.assertEqual(pg.movimenti_pc.filter(descrizione__startswith="Sondaggio").count(), 1)

    def test_premio_mancante_accreditato_dopo(self):
        creato = self._importa()
        sondaggio = Sondaggio.objects.get(pk=creato["id"])
        registra_risposta(sondaggio, self.personaggio, self.player, self._risposte_valide())
        sondaggio.premio_pc = 4
        sondaggio.premio_crediti_correnti = Decimal("1.00")
        sondaggio.save(update_fields=["premio_pc", "premio_crediti_correnti", "updated_at"])
        self.client.force_authenticate(self.staff)
        risposta = self.client.post(
            f"/api/personaggi/api/staff/sondaggi/{creato['id']}/premi/",
            {},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(risposta.status_code, 200, risposta.content)
        self.assertEqual(risposta.json()["premi_appena_erogati"], 1)
        self.assertEqual(risposta.json()["premi_mancanti"], 0)
        pg = Personaggio.objects.get(pk=self.personaggio.pk)
        self.assertEqual(pg.punti_caratteristica, 8 + 4)
        self.assertEqual(pg.crediti_corrente, Decimal("1.00"))
        di_nuovo = eroga_premi_mancanti(sondaggio)
        self.assertEqual(di_nuovo, 0)
