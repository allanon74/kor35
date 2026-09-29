"""Login QR delle console ingegneria e scientifica sulla sigla impostata nello staff."""
from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from personaggi.models import Personaggio, PersonaggioStatisticaBase, Statistica
from pilotaggio.models import PilotConsoleLoginTicket, PilotRuntimeConfig


def _personaggio(nome, sigla, valore):
    user = User.objects.create_user(username=f"u_{nome}", password="x")
    pg = Personaggio.objects.create(nome=nome, proprietario=user)
    stat, _ = Statistica.objects.update_or_create(
        sigla=sigla,
        defaults={"nome": sigla, "parametro": sigla.lower()},
    )
    PersonaggioStatisticaBase.objects.update_or_create(
        personaggio=pg,
        statistica=stat,
        defaults={"valore_base": valore},
    )
    if hasattr(pg, "_punteggi_base_cache"):
        del pg._punteggi_base_cache
    return user, pg


def _cfg(**fields):
    cfg = PilotRuntimeConfig.get_solo()
    for key, value in fields.items():
        setattr(cfg, key, value)
    cfg.save()
    return cfg


@override_settings(PILOT_CONSOLE_ENABLED=True)
class StationConsoleAuthTests(TestCase):
    def setUp(self):
        _cfg(
            compattatore_console_abilitata=True,
            compattatore_login_richiesto=True,
            compattatore_stat_accesso_sigla="0IN",
            scientifica_console_abilitata=True,
            scientifica_login_richiesto=True,
            scientifica_stat_accesso_sigla="0SC",
            login_required_console=True,
        )
        self.console = APIClient()

    def test_station_payload_usa_sigle_runtime(self):
        _cfg(
            compattatore_stat_accesso_sigla="ABX",
            scientifica_stat_accesso_sigla="QSC",
            comunicazioni_console_abilitata=True,
            comunicazioni_stat_accesso_sigla="0CO",
        )
        res = self.console.get("/api/pilot/station/consoles/")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["ingegneria"]["sigla"], "ABX")
        self.assertEqual(body["ingegneria"]["requisito"], "ABX > 0")
        self.assertEqual(body["ingegneria"]["screen"], "compattatore")
        self.assertTrue(body["ingegneria"]["enabled"])
        self.assertEqual(body["scientifica"]["sigla"], "QSC")
        self.assertEqual(body["scientifica"]["requisito"], "QSC > 0")
        self.assertEqual(body["scientifica"]["screen"], "scientifica")
        self.assertEqual(body["comunicazioni"]["sigla"], "0CO")
        self.assertEqual(body["comunicazioni"]["requisito"], "0CO > 0")
        self.assertEqual(body["comunicazioni"]["screen"], "comunicazioni")
        self.assertTrue(body["comunicazioni"]["enabled"])

    def test_ticket_ingegneria_rifiuta_solo_navigazione(self):
        user, _pg = _personaggio("SoloPilota", "0PI", 3)
        phone = APIClient()
        phone.force_authenticate(user=user)
        create = self.console.post("/api/pilot/compattatore/auth/console-ticket/", {}, format="json")
        self.assertEqual(create.status_code, 201, create.content)
        payload = create.json()
        self.assertEqual(payload["ruolo"], "ingegneria")
        self.assertEqual(payload["stat_sigla"], "0IN")
        ticket = PilotConsoleLoginTicket.objects.get(pk=payload["ticket_id"])
        self.assertEqual(ticket.ruolo, "ingegneria")
        claim = phone.get(
            f"/api/pilot/auth/console-ticket/{payload['ticket_id']}/claim/?c={payload['codice']}",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(claim.status_code, 403, claim.content)
        self.assertIn("0IN", claim.json()["error"])

    def test_ticket_ingegneria_accetta_sigla_configurata(self):
        _cfg(compattatore_stat_accesso_sigla="ABX")
        user, pg = _personaggio("Ingegnere", "ABX", 1)
        phone = APIClient()
        phone.force_authenticate(user=user)
        create = self.console.post("/api/pilot/compattatore/auth/console-ticket/", {}, format="json")
        self.assertEqual(create.status_code, 201, create.content)
        payload = create.json()
        self.assertEqual(payload["stat_sigla"], "ABX")
        claim = phone.get(
            f"/api/pilot/auth/console-ticket/{payload['ticket_id']}/claim/?c={payload['codice']}",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(claim.status_code, 200, claim.content)
        self.assertEqual(claim.json()["pilota"]["id"], pg.pk)
        status_res = self.console.get(
            f"/api/pilot/auth/console-ticket/{payload['ticket_id']}/status/?c={payload['codice']}"
        )
        self.assertEqual(status_res.status_code, 200, status_res.content)
        self.assertEqual(status_res.json()["status"], "authorized")
        self.assertIn("token", status_res.json())

    def test_ticket_scientifica_ignora_abilita_ingegneria(self):
        user, _pg = _personaggio("IngegnereNoLab", "0IN", 4)
        phone = APIClient()
        phone.force_authenticate(user=user)
        create = self.console.post("/api/pilot/scientifica/auth/console-ticket/", {}, format="json")
        self.assertEqual(create.status_code, 201, create.content)
        payload = create.json()
        claim = phone.get(
            f"/api/pilot/auth/console-ticket/{payload['ticket_id']}/claim/?c={payload['codice']}",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(claim.status_code, 403, claim.content)
        self.assertIn("0SC", claim.json()["error"])

    def test_scientifica_senza_login_non_chiede_la_statistica(self):
        _cfg(scientifica_login_richiesto=False)
        _personaggio("SenzaLab", "0PI", 2)
        issued = self.console.post("/api/pilot/scientifica/auth/auto-login/", {}, format="json")
        self.assertEqual(issued.status_code, 200, issued.content)
        token = issued.json()["token"]
        state = self.console.get(
            "/api/pilot/scientifica/state/",
            HTTP_AUTHORIZATION=f"PilotToken {token}",
        )
        self.assertEqual(state.status_code, 200, state.content)
        self.assertTrue(state.json()["abilitato"])

    def test_console_spenta_non_emette_ticket(self):
        _cfg(compattatore_console_abilitata=False)
        res = self.console.post("/api/pilot/compattatore/auth/console-ticket/", {}, format="json")
        self.assertEqual(res.status_code, 403, res.content)
        enabled = self.console.get("/api/pilot/compattatore/console-enabled/")
        self.assertEqual(enabled.status_code, 200, enabled.content)
        self.assertFalse(enabled.json()["enabled"])
        self.assertEqual(enabled.json()["compattatore_stat_accesso_sigla"], "0IN")
