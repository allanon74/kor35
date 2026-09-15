from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from gestione_plot.compiti_ics import build_compiti_ics
from gestione_plot.compiti_push import dispatch_compiti_scadenze
from gestione_plot.models import CalendarioFeedToken, StaffCompito, StaffCompitoAssegnazione
from personaggi.models import (
    CAMPAGNA_ROLE_HELPER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_PLAYER,
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
)

User = get_user_model()


class StaffCompitiApiTests(APITestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="compiti-cal", nome="Compiti Cal", attiva=True)
        self.master = User.objects.create_user(username="master_cal", password="x")
        self.staffer = User.objects.create_user(username="staff_cal", password="x")
        self.helper = User.objects.create_user(username="helper_cal", password="x")
        self.player = User.objects.create_user(username="player_cal", password="x")

        for user, ruolo in (
            (self.master, CAMPAGNA_ROLE_MASTER),
            (self.staffer, CAMPAGNA_ROLE_STAFFER),
            (self.helper, CAMPAGNA_ROLE_HELPER),
            (self.player, CAMPAGNA_ROLE_PLAYER),
        ):
            CampagnaUtente.objects.create(campagna=self.campagna, user=user, ruolo=ruolo, attivo=True)

        self.scadenza = timezone.now() + timedelta(hours=2)
        self.compito = StaffCompito.objects.create(
            campagna=self.campagna,
            titolo="Stampare volantini",
            descrizione="A3, 200 copie",
            scadenza=self.scadenza,
            preavviso_minuti=60,
            creato_da=self.master,
        )
        StaffCompitoAssegnazione.objects.create(compito=self.compito, user=self.helper)
        StaffCompitoAssegnazione.objects.create(compito=self.compito, user=self.staffer)

    def _auth(self, user, method, url, data=None):
        self.client.force_authenticate(user=user)
        return getattr(self.client, method)(
            url,
            data,
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )

    def test_master_crea_compito(self):
        scadenza = (timezone.now() + timedelta(days=1)).isoformat()
        resp = self._auth(
            self.master,
            "post",
            "/api/plot/api/calendario-compiti/",
            {
                "titolo": "Post Instagram",
                "descrizione": "Reel evento",
                "scadenza": scadenza,
                "preavviso_minuti": 1440,
                "assegnatari": [self.helper.id],
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["titolo"], "Post Instagram")
        self.assertEqual(len(resp.data["assegnazioni"]), 1)
        self.assertEqual(resp.data["assegnazioni"][0]["user"], self.helper.id)

    def test_staffer_non_puo_creare(self):
        resp = self._auth(
            self.staffer,
            "post",
            "/api/plot/api/calendario-compiti/",
            {
                "titolo": "Vietato",
                "scadenza": (timezone.now() + timedelta(days=1)).isoformat(),
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_helper_non_accede_dashboard_layout(self):
        resp = self._auth(self.helper, "get", "/api/plot/api/staff/dashboard-layout/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_helper_vede_solo_propri(self):
        altro = StaffCompito.objects.create(
            campagna=self.campagna,
            titolo="Solo master",
            scadenza=self.scadenza,
            creato_da=self.master,
        )
        StaffCompitoAssegnazione.objects.create(compito=altro, user=self.master)

        resp = self._auth(self.helper, "get", "/api/plot/api/calendario-compiti/miei/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titoli = {row["titolo"] for row in resp.data}
        self.assertIn("Stampare volantini", titoli)
        self.assertNotIn("Solo master", titoli)

    def test_player_non_vede_compiti(self):
        resp = self._auth(self.player, "get", "/api/plot/api/calendario-compiti/miei/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_helper_completa(self):
        resp = self._auth(self.helper, "post", f"/api/plot/api/calendario-compiti/{self.compito.id}/completa/", {})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        mine = resp.data["mia_assegnazione"]
        self.assertIsNotNone(mine["completato_at"])

    def test_ics_feed_con_token(self):
        token_row = CalendarioFeedToken.objects.create(user=self.helper)
        resp = self.client.get(f"/api/plot/api/calendario-compiti.ics?token={token_row.token}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/calendar", resp["Content-Type"])
        body = resp.content.decode("utf-8")
        self.assertIn("BEGIN:VCALENDAR", body)
        self.assertIn("Stampare volantini", body)
        self.assertIn("BEGIN:VALARM", body)

    def test_ics_token_mancante(self):
        resp = self.client.get("/api/plot/api/calendario-compiti.ics")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_build_ics_helper(self):
        rows = list(self.compito.assegnazioni.select_related("compito"))
        ics = build_compiti_ics(rows)
        self.assertIn("VEVENT", ics)

    @patch("gestione_plot.compiti_push.notify_compito_user", return_value=1)
    def test_dispatch_preavviso_e_scadenza(self, mock_notify):
        past = timezone.now() - timedelta(minutes=5)
        self.compito.scadenza = past
        self.compito.preavviso_minuti = 60
        self.compito.save()

        stats = dispatch_compiti_scadenze(now=timezone.now())
        self.assertGreaterEqual(stats["dispatched"], 1)
        self.assertTrue(mock_notify.called)

        helper_row = StaffCompitoAssegnazione.objects.get(compito=self.compito, user=self.helper)
        self.assertTrue(helper_row.push_preavviso_inviata)
        self.assertTrue(helper_row.push_scadenza_inviata)

        mock_notify.reset_mock()
        stats2 = dispatch_compiti_scadenze(now=timezone.now())
        self.assertEqual(stats2["dispatched"], 0)
        self.assertFalse(mock_notify.called)

    def test_helper_feed_token(self):
        resp = self._auth(self.helper, "get", "/api/plot/api/calendario-compiti/feed-token/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", resp.data)
        self.assertTrue(str(resp.data["path"]).endswith(str(resp.data["token"])))
        self.assertTrue(resp.data["include_compiti"])
        self.assertIn("calendario.ics", resp.data["path"])


class StaffCompitiAutomaticiApiTests(APITestCase):
    def setUp(self):
        from decimal import Decimal

        from personaggi.models import (
            AURA,
            Personaggio,
            PropostaTecnica,
            Punteggio,
            STATO_PROPOSTA_IN_VALUTAZIONE,
            TipologiaPersonaggio,
            TIPO_PROPOSTA_TESSITURA,
        )

        self.campagna = Campagna.objects.create(slug="compiti-auto", nome="Compiti Auto", attiva=True)
        self.master = User.objects.create_user(username="master_auto", password="x")
        self.staffer = User.objects.create_user(username="staff_auto", password="x")
        self.helper = User.objects.create_user(username="helper_auto", password="x")
        self.player = User.objects.create_user(username="player_auto", password="x")

        for user, ruolo in (
            (self.master, CAMPAGNA_ROLE_MASTER),
            (self.staffer, CAMPAGNA_ROLE_STAFFER),
            (self.helper, CAMPAGNA_ROLE_HELPER),
            (self.player, CAMPAGNA_ROLE_PLAYER),
        ):
            CampagnaUtente.objects.create(campagna=self.campagna, user=user, ruolo=ruolo, attivo=True)

        tipologia = TipologiaPersonaggio.objects.create(
            nome="Std auto test",
            crediti_iniziali=Decimal("1000"),
            caratteristiche_iniziali=10,
        )
        pg = Personaggio.objects.create(
            nome="Proponente",
            proprietario=self.player,
            tipologia=tipologia,
            campagna=self.campagna,
        )
        aura = Punteggio.objects.create(nome="Aura Auto", sigla="AAU", tipo=AURA)
        self.proposta = PropostaTecnica.objects.create(
            personaggio=pg,
            tipo=TIPO_PROPOSTA_TESSITURA,
            stato=STATO_PROPOSTA_IN_VALUTAZIONE,
            nome="Tessitura proposta",
            descrizione="da verificare",
            aura=aura,
        )

    def _auth(self, user, method, url, data=None):
        self.client.force_authenticate(user=user)
        return getattr(self.client, method)(
            url,
            data,
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )

    def test_master_configura_e_vede_task_automatica(self):
        from gestione_plot.models import COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES

        resp = self._auth(
            self.master,
            "put",
            "/api/plot/api/calendario-compiti/automatici/",
            {
                "items": [
                    {
                        "codice": COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES,
                        "assegnatari": [self.master.id],
                        "attivo": True,
                    }
                ]
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        tes = next(
            (r for r in resp.data["items"] if r["codice"] == COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES),
            None,
        )
        self.assertIsNotNone(tes)
        self.assertEqual(tes["conteggio"], 1)
        self.assertEqual([a["id"] for a in tes["assegnatari"]], [self.master.id])

        lista = self._auth(self.master, "get", "/api/plot/api/calendario-compiti/")
        self.assertEqual(lista.status_code, status.HTTP_200_OK)
        self.assertTrue(lista.data[0]["automatico"])
        self.assertEqual(lista.data[0]["titolo"], "Verifica tessiture: 1")
        self.assertTrue(str(lista.data[0]["id"]).startswith("auto:"))

    def test_assegnatario_vede_in_miei_non_assegnato_no(self):
        from gestione_plot.models import (
            COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES,
            StaffCompitoAutomatico,
            StaffCompitoAutomaticoAssegnazione,
        )

        config, _ = StaffCompitoAutomatico.objects.get_or_create(
            campagna=self.campagna,
            codice=COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES,
            defaults={"attivo": True},
        )
        StaffCompitoAutomaticoAssegnazione.objects.create(config=config, user=self.staffer)

        miei_staff = self._auth(self.staffer, "get", "/api/plot/api/calendario-compiti/miei/")
        self.assertEqual(miei_staff.status_code, status.HTTP_200_OK)
        auto = [r for r in miei_staff.data if r.get("automatico")]
        self.assertEqual(len(auto), 1)
        self.assertEqual(auto[0]["titolo"], "Verifica tessiture: 1")

        miei_master = self._auth(self.master, "get", "/api/plot/api/calendario-compiti/miei/")
        self.assertEqual(miei_master.status_code, status.HTTP_200_OK)
        self.assertEqual([r for r in miei_master.data if r.get("automatico")], [])

    def test_senza_proposte_non_appare(self):
        from gestione_plot.models import (
            COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES,
            StaffCompitoAutomatico,
            StaffCompitoAutomaticoAssegnazione,
        )
        from personaggi.models import STATO_PROPOSTA_APPROVATA

        config, _ = StaffCompitoAutomatico.objects.get_or_create(
            campagna=self.campagna,
            codice=COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES,
            defaults={"attivo": True},
        )
        StaffCompitoAutomaticoAssegnazione.objects.create(config=config, user=self.master)
        self.proposta.stato = STATO_PROPOSTA_APPROVATA
        self.proposta.save(update_fields=["stato", "updated_at"])

        lista = self._auth(self.master, "get", "/api/plot/api/calendario-compiti/")
        self.assertEqual(lista.status_code, status.HTTP_200_OK)
        self.assertEqual([r for r in lista.data if r.get("automatico")], [])

    def test_staffer_non_puo_configurare(self):
        from gestione_plot.models import COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES

        resp = self._auth(
            self.staffer,
            "put",
            "/api/plot/api/calendario-compiti/automatici/",
            {
                "items": [
                    {
                        "codice": COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES,
                        "assegnatari": [self.staffer.id],
                    }
                ]
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_automatico_prima_dei_manuali(self):
        from gestione_plot.models import (
            COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES,
            StaffCompito,
            StaffCompitoAssegnazione,
            StaffCompitoAutomatico,
            StaffCompitoAutomaticoAssegnazione,
        )

        config, _ = StaffCompitoAutomatico.objects.get_or_create(
            campagna=self.campagna,
            codice=COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES,
            defaults={"attivo": True},
        )
        StaffCompitoAutomaticoAssegnazione.objects.create(config=config, user=self.master)
        compito = StaffCompito.objects.create(
            campagna=self.campagna,
            titolo="Manuale",
            scadenza=timezone.now() + timedelta(hours=1),
            creato_da=self.master,
        )
        StaffCompitoAssegnazione.objects.create(compito=compito, user=self.master)

        lista = self._auth(self.master, "get", "/api/plot/api/calendario-compiti/")
        self.assertEqual(lista.status_code, status.HTTP_200_OK)
        self.assertTrue(lista.data[0]["automatico"])
        self.assertEqual(lista.data[1]["titolo"], "Manuale")
