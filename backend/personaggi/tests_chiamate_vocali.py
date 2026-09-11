"""Chiamate vocali personaggio↔personaggio e verso staff."""
import base64
import hashlib
import hmac
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, override_settings
from django.urls import resolve
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_PLAYER,
    Campagna,
    CampagnaUtente,
    ChiamataVocale,
    Personaggio,
)


class ChiamateVocaliApiTests(APITestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="voce-test", nome="Voce", attiva=True)
        self.u1 = User.objects.create_user(username="voce_a", password="x")
        self.u2 = User.objects.create_user(username="voce_b", password="x")
        self.staff = User.objects.create_user(username="voce_staff", password="x", is_staff=True)
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.u1, ruolo=CAMPAGNA_ROLE_PLAYER, attivo=True
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.u2, ruolo=CAMPAGNA_ROLE_PLAYER, attivo=True
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.staff, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )
        self.pg1 = Personaggio.objects.create(
            nome="Alice Voce", proprietario=self.u1, campagna=self.campagna
        )
        self.pg2 = Personaggio.objects.create(
            nome="Bob Voce", proprietario=self.u2, campagna=self.campagna
        )

    def test_ice_servers(self):
        self.client.force_authenticate(self.u1)
        resp = self.client.get("/api/personaggi/api/chiamate/ice-servers/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(resp.data["iceServers"])
        self.assertTrue(any("stun:" in str(s.get("urls")) for s in resp.data["iceServers"]))

    @override_settings(
        TURN_RELAY_ENABLED=True,
        TURN_AUTO_FROM_HOST=True,
        TURN_URLS=[],
        TURN_USERNAME="kor35turn",
        TURN_CREDENTIAL="kor35turnlocal",
        TURN_PORT=3478,
        TURN_AUTH_SECRET="",
        ALLOWED_HOSTS=["192.168.100.1", "testserver"],
    )
    def test_ice_servers_turn_from_host(self):
        self.client.force_authenticate(self.u1)
        resp = self.client.get(
            "/api/personaggi/api/chiamate/ice-servers/",
            HTTP_HOST="192.168.100.1",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        urls = [str(s.get("urls")) for s in resp.data["iceServers"]]
        self.assertTrue(
            any("turn:192.168.100.1:3478" in u for u in urls),
            urls,
        )
        turn_entries = [s for s in resp.data["iceServers"] if "turn:" in str(s.get("urls"))]
        self.assertTrue(turn_entries)
        self.assertEqual(turn_entries[0]["username"], "kor35turn")
        self.assertEqual(turn_entries[0]["credential"], "kor35turnlocal")

    @override_settings(
        TURN_RELAY_ENABLED=True,
        TURN_AUTO_FROM_HOST=True,
        TURN_URLS=[],
        TURN_AUTH_SECRET="s3cret-test-hmac",
        TURN_CREDENTIAL_TTL=3600,
        TURN_USERNAME="kor35turn",
        TURN_CREDENTIAL="should-not-appear",
        TURN_PORT=3478,
        ALLOWED_HOSTS=["www.kor35.it", "testserver"],
    )
    def test_ice_servers_turn_hmac_prod(self):
        self.client.force_authenticate(self.u1)
        resp = self.client.get(
            "/api/personaggi/api/chiamate/ice-servers/",
            HTTP_HOST="www.kor35.it",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        turn_entries = [s for s in resp.data["iceServers"] if "turn:" in str(s.get("urls"))]
        self.assertTrue(turn_entries)
        urls = [str(s.get("urls")) for s in turn_entries]
        self.assertTrue(any("turn:www.kor35.it:3478" in u for u in urls), urls)
        username = turn_entries[0]["username"]
        self.assertTrue(username.endswith(f":{self.u1.pk}"))
        expiry_s, _, uid_s = username.partition(":")
        self.assertTrue(expiry_s.isdigit())
        self.assertEqual(uid_s, str(self.u1.pk))
        digest = hmac.new(
            b"s3cret-test-hmac", username.encode("utf-8"), hashlib.sha1
        ).digest()
        self.assertEqual(turn_entries[0]["credential"], base64.b64encode(digest).decode("ascii"))
        self.assertNotEqual(turn_entries[0]["credential"], "should-not-appear")

    @patch("personaggi.chiamate_vocali._notifica_parti")
    @patch("personaggi.chiamate_vocali._push_invito")
    def test_pg_to_pg_accetta(self, _push, _ws):
        self.client.force_authenticate(self.u1)
        resp = self.client.post(
            "/api/personaggi/api/chiamate/",
            {"chiamante_id": self.pg1.id, "chiamato_id": self.pg2.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        call_id = resp.data["id"]
        self.assertEqual(resp.data["stato"], ChiamataVocale.STATO_RINGING)
        self.assertEqual(resp.data["ruolo"], "caller")

        self.client.force_authenticate(self.u2)
        acc = self.client.post(f"/api/personaggi/api/chiamate/{call_id}/accetta/", {}, format="json")
        self.assertEqual(acc.status_code, status.HTTP_200_OK, acc.data)
        self.assertEqual(acc.data["stato"], ChiamataVocale.STATO_IN_CORSO)
        self.assertEqual(acc.data["ruolo"], "callee")

        chiudi = self.client.post(f"/api/personaggi/api/chiamate/{call_id}/chiudi/", {}, format="json")
        self.assertEqual(chiudi.status_code, status.HTTP_200_OK, chiudi.data)
        self.assertEqual(chiudi.data["stato"], ChiamataVocale.STATO_TERMINATA)

    @patch("personaggi.chiamate_vocali._notifica_parti")
    @patch("personaggi.chiamate_vocali._push_invito")
    def test_non_puoi_chiamare_te_stesso(self, _push, _ws):
        self.client.force_authenticate(self.u1)
        resp = self.client.post(
            "/api/personaggi/api/chiamate/",
            {"chiamante_id": self.pg1.id, "chiamato_id": self.pg1.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("personaggi.chiamate_vocali._notifica_parti")
    @patch("personaggi.chiamate_vocali._push_invito")
    def test_verso_staff(self, _push, _ws):
        self.client.force_authenticate(self.u1)
        resp = self.client.post(
            "/api/personaggi/api/chiamate/",
            {"chiamante_id": self.pg1.id, "verso_staff": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        call_id = resp.data["id"]

        self.client.force_authenticate(self.staff)
        coda = self.client.get("/api/personaggi/api/chiamate/coda/")
        self.assertEqual(coda.status_code, status.HTTP_200_OK, coda.data)
        self.assertEqual(len(coda.data["results"]), 1)

        acc = self.client.post(f"/api/personaggi/api/chiamate/{call_id}/accetta/", {}, format="json")
        self.assertEqual(acc.status_code, status.HTTP_200_OK, acc.data)
        self.assertEqual(acc.data["stato"], ChiamataVocale.STATO_IN_CORSO)
        self.assertEqual(acc.data["accettata_da_username"], "voce_staff")

    @patch("personaggi.chiamate_vocali._notifica_parti")
    @patch("personaggi.chiamate_vocali._push_invito")
    def test_rifiuta(self, _push, _ws):
        self.client.force_authenticate(self.u1)
        resp = self.client.post(
            "/api/personaggi/api/chiamate/",
            {"chiamante_id": self.pg1.id, "chiamato_id": self.pg2.id},
            format="json",
        )
        call_id = resp.data["id"]
        self.client.force_authenticate(self.u2)
        rif = self.client.post(f"/api/personaggi/api/chiamate/{call_id}/rifiuta/", {}, format="json")
        self.assertEqual(rif.status_code, status.HTTP_200_OK, rif.data)
        self.assertEqual(rif.data["stato"], ChiamataVocale.STATO_RIFIUTATA)

    @patch("personaggi.chiamate_vocali._notifica_parti")
    @patch("personaggi.chiamate_vocali._push_invito")
    def test_modulo_off_blocca_avvio(self, _push, _ws):
        from personaggi.campagna_moduli import MODULO_ACCESSO_OFF, MODULO_CHIAMATE, apply_moduli_accesso

        apply_moduli_accesso(self.campagna, {MODULO_CHIAMATE: MODULO_ACCESSO_OFF})
        self.client.force_authenticate(self.u1)
        resp = self.client.post(
            "/api/personaggi/api/chiamate/",
            {"chiamante_id": self.pg1.id, "chiamato_id": self.pg2.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        ice = self.client.get(
            "/api/personaggi/api/chiamate/ice-servers/",
            HTTP_X_CAMPAGNA="voce-test",
        )
        self.assertEqual(ice.status_code, status.HTTP_403_FORBIDDEN)

    @patch("personaggi.chiamate_vocali._notifica_parti")
    @patch("personaggi.chiamate_vocali._push_invito")
    def test_storico_inviate_ricevute_perse(self, _push, _ws):
        self.client.force_authenticate(self.u1)
        avvio = self.client.post(
            "/api/personaggi/api/chiamate/",
            {"chiamante_id": self.pg1.id, "chiamato_id": self.pg2.id},
            format="json",
        )
        self.assertEqual(avvio.status_code, status.HTTP_201_CREATED, avvio.data)
        call = ChiamataVocale.objects.get(pk=avvio.data["id"])
        call.stato = ChiamataVocale.STATO_PERSA
        call.save(update_fields=["stato", "updated_at"])

        hist_caller = self.client.get(
            f"/api/personaggi/api/chiamate/storico/?personaggio_id={self.pg1.id}"
        )
        self.assertEqual(hist_caller.status_code, status.HTTP_200_OK, hist_caller.data)
        self.assertEqual(len(hist_caller.data["results"]), 1)
        self.assertEqual(hist_caller.data["results"][0]["direzione"], "inviata")
        self.assertEqual(hist_caller.data["results"][0]["esito"], "persa")

        self.client.force_authenticate(self.u2)
        hist_callee = self.client.get(
            f"/api/personaggi/api/chiamate/storico/?personaggio_id={self.pg2.id}"
        )
        self.assertEqual(hist_callee.status_code, status.HTTP_200_OK, hist_callee.data)
        self.assertEqual(hist_callee.data["results"][0]["direzione"], "ricevuta")
        self.assertEqual(hist_callee.data["results"][0]["esito"], "persa")
        self.assertEqual(hist_callee.data["results"][0]["peer_nome"], self.pg1.nome)


class ChiamateRoutingTests(SimpleTestCase):
    def test_rest_ice_coda_e_list_non_collidono(self):
        from personaggi import chiamate_views

        ice = resolve("/api/personaggi/api/chiamate/ice-servers/")
        self.assertIs(ice.func.view_class, chiamate_views.ChiamataIceServersView)
        coda = resolve("/api/personaggi/api/chiamate/coda/")
        self.assertIs(coda.func.view_class, chiamate_views.ChiamataVocaleCodaStaffView)
        storico = resolve("/api/personaggi/api/chiamate/storico/")
        self.assertIs(storico.func.view_class, chiamate_views.ChiamataVocaleStoricoView)
        lista = resolve("/api/personaggi/api/chiamate/")
        self.assertIs(lista.func.view_class, chiamate_views.ChiamataVocaleListCreateView)

    def test_ws_chiamate_con_e_senza_slash(self):
        from personaggi.routing import websocket_urlpatterns

        for path in ("ws/chiamate/", "ws/chiamate"):
            match = next((p.resolve(path) for p in websocket_urlpatterns if p.resolve(path)), None)
            self.assertIsNotNone(match, path)
