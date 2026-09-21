from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from gestione_plot.missioni_service import applica_fattore_korp, calcola_ricompensa_base
from gestione_plot.models import Evento, Missione, MissioneEvento
from personaggi.campagna_moduli import MODULO_ACCESSO_OPEN, MODULO_TASKS, apply_moduli_accesso
from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_PLAYER,
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
    Personaggio,
    TipologiaPersonaggio,
)

User = get_user_model()


class _FakeMissione:
    def __init__(self, **kwargs):
        self.reward_crediti = kwargs.get("reward_crediti", Decimal("100"))
        self.reward_prestigio = kwargs.get("reward_prestigio", 10)
        self.premio_solo_primo = kwargs.get("premio_solo_primo", False)
        self.malus_non_primo_crediti = kwargs.get("malus_non_primo_crediti", Decimal("0"))
        self.malus_non_primo_prestigio = kwargs.get("malus_non_primo_prestigio", 0)
        self.bonus_successive_crediti = kwargs.get("bonus_successive_crediti", Decimal("0"))
        self.bonus_successive_prestigio = kwargs.get("bonus_successive_prestigio", 0)
        self.esclusiva = kwargs.get("esclusiva", False)
        self.korp_id = kwargs.get("korp_id")
        self.allineamento = kwargs.get("allineamento", "GRIGIA")


class MissioniRewardCalcTests(SimpleTestCase):
    def test_primo_piena_ricompensa(self):
        cr, pr = calcola_ricompensa_base(_FakeMissione(), is_primo=True)
        self.assertEqual(cr, Decimal("100.00"))
        self.assertEqual(pr, 10)

    def test_solo_primo_azzera_successivi(self):
        cr, pr = calcola_ricompensa_base(_FakeMissione(premio_solo_primo=True), is_primo=False)
        self.assertEqual(cr, Decimal("0.00"))
        self.assertEqual(pr, 0)

    def test_malus_e_bonus_successivi(self):
        m = _FakeMissione(
            malus_non_primo_crediti=Decimal("20"),
            malus_non_primo_prestigio=3,
            bonus_successive_crediti=Decimal("5"),
            bonus_successive_prestigio=1,
        )
        cr, pr = calcola_ricompensa_base(m, is_primo=False)
        self.assertEqual(cr, Decimal("85.00"))
        self.assertEqual(pr, 8)


class MissioniRiepilogoLogicTests(SimpleTestCase):
    """Verifica classificazione non-korp: generiche + altre KORP non esclusive."""

    def test_classificazione_non_korp(self):
        # Pure unit: replica la regola senza DB
        missioni = [
            _FakeMissione(korp_id=1, esclusiva=False, reward_crediti=Decimal("10")),
            _FakeMissione(korp_id=2, esclusiva=False, reward_crediti=Decimal("20")),
            _FakeMissione(korp_id=2, esclusiva=True, reward_crediti=Decimal("50")),
            _FakeMissione(korp_id=None, esclusiva=False, reward_crediti=Decimal("5")),
        ]
        korp_id = 1
        di = [m for m in missioni if m.korp_id == korp_id]
        non = [m for m in missioni if m.korp_id != korp_id and not m.esclusiva]
        self.assertEqual(len(di), 1)
        self.assertEqual(sum(m.reward_crediti for m in non), Decimal("25"))  # 20 + 5, non 50 esclusiva


class MissioniFattoreKorpTests(SimpleTestCase):
    def _missione(self, *, korp_id, fattore):
        m = _FakeMissione(korp_id=korp_id)
        m.korp = type("Korp", (), {"fattore_task": fattore})()
        return m

    @patch("gestione_plot.missioni_service.personaggio_ha_korp", return_value=True)
    def test_sovrapagata_solo_fattore_maggiore_di_uno(self, _mock):
        m = self._missione(korp_id=1, fattore=Decimal("2.00"))
        cr, pr, is_bonus, fat = applica_fattore_korp(m, object(), Decimal("10"), 4)
        self.assertEqual(cr, Decimal("20.00"))
        self.assertEqual(pr, 8)
        self.assertTrue(is_bonus)
        self.assertEqual(fat, Decimal("2.00"))

    @patch("gestione_plot.missioni_service.personaggio_ha_korp", return_value=True)
    def test_stessa_korp_fattore_uno_non_evidenzia(self, _mock):
        m = self._missione(korp_id=1, fattore=Decimal("1.00"))
        cr, pr, is_bonus, fat = applica_fattore_korp(m, object(), Decimal("10"), 4)
        self.assertEqual(cr, Decimal("10.00"))
        self.assertEqual(pr, 4)
        self.assertFalse(is_bonus)
        self.assertEqual(fat, Decimal("1.00"))

    @patch("gestione_plot.missioni_service.personaggio_ha_korp", return_value=False)
    def test_altra_korp_nessun_bonus(self, _mock):
        m = self._missione(korp_id=2, fattore=Decimal("3.00"))
        cr, pr, is_bonus, fat = applica_fattore_korp(m, object(), Decimal("10"), 4)
        self.assertEqual(cr, Decimal("10.00"))
        self.assertFalse(is_bonus)
        self.assertEqual(fat, Decimal("1.00"))

    def test_task_generica_nessun_bonus(self):
        m = _FakeMissione(korp_id=None)
        cr, pr, is_bonus, fat = applica_fattore_korp(m, object(), Decimal("10"), 4)
        self.assertEqual(cr, Decimal("10.00"))
        self.assertFalse(is_bonus)
        self.assertEqual(fat, Decimal("1.00"))


class MissioniVisibilitaApiTests(APITestCase):
    """Evento partito + PG iscritto + task attiva per evento."""

    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug="tasks-vis",
            nome="Tasks visibilità",
            attiva=True,
        )
        apply_moduli_accesso(self.campagna, {MODULO_TASKS: MODULO_ACCESSO_OPEN})
        self.player = User.objects.create_user("player_tasks_vis", password="x")
        self.other = User.objects.create_user("other_tasks_vis", password="x")
        self.master = User.objects.create_user("master_tasks_vis", password="x")
        self.staffer = User.objects.create_user("staffer_tasks_vis", password="x")
        for user, ruolo in (
            (self.player, CAMPAGNA_ROLE_PLAYER),
            (self.other, CAMPAGNA_ROLE_PLAYER),
            (self.master, CAMPAGNA_ROLE_MASTER),
            (self.staffer, CAMPAGNA_ROLE_STAFFER),
        ):
            CampagnaUtente.objects.create(campagna=self.campagna, user=user, ruolo=ruolo, attivo=True)
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="Giocante tasks vis",
            giocante=True,
        )
        self.pg = Personaggio.objects.create(
            nome="PG Tasks",
            proprietario=self.player,
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        self.pg_other = Personaggio.objects.create(
            nome="PG Altro",
            proprietario=self.other,
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Evento tasks vis",
            data_inizio=now - timedelta(hours=1),
            data_fine=now + timedelta(days=1),
        )
        self.missione = Missione.objects.create(
            titolo="Recupera il relitto",
            descrizione="Segreta",
            attiva=True,
        )
        self.link = MissioneEvento.objects.create(
            missione=self.missione,
            evento=self.evento,
            attiva=True,
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _get(self, user, url):
        self._auth(user)
        return self.client.get(url, HTTP_X_CAMPAGNA=self.campagna.slug)

    def _post(self, user, url, data):
        self._auth(user)
        return self.client.post(url, data, format="json", HTTP_X_CAMPAGNA=self.campagna.slug)

    def _mie(self, user, pg):
        return self._get(user, f"/api/plot/api/missioni/mie/?personaggio={pg.id}")

    def test_giocatore_non_vede_catalogo(self):
        resp = self._get(self.player, "/api/plot/api/missioni/")
        self.assertEqual(resp.status_code, 403)

    def test_mie_vuoto_se_evento_non_partito(self):
        self.evento.partecipanti.add(self.pg)
        resp = self._mie(self.player, self.pg)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_mie_vuoto_se_pg_non_iscritto(self):
        self.evento.started_at = timezone.now()
        self.evento.save(update_fields=["started_at", "updated_at"])
        resp = self._mie(self.player, self.pg)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_tab_evento_attivo_false_se_non_iscritto(self):
        self.evento.started_at = timezone.now()
        self.evento.save(update_fields=["started_at", "updated_at"])
        resp = self._get(
            self.player,
            f"/api/plot/api/missioni/evento-attivo/?personaggio={self.pg.id}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["attivo"])
        self.assertFalse(resp.json()["iscritto"])

    def test_mie_visibile_se_partito_e_iscritto(self):
        self.evento.started_at = timezone.now()
        self.evento.save(update_fields=["started_at", "updated_at"])
        self.evento.partecipanti.add(self.pg)
        resp = self._mie(self.player, self.pg)
        self.assertEqual(resp.status_code, 200)
        rows = resp.json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["titolo"], "Recupera il relitto")

    def test_mie_nasconde_task_disattiva_evento(self):
        self.evento.started_at = timezone.now()
        self.evento.save(update_fields=["started_at", "updated_at"])
        self.evento.partecipanti.add(self.pg)
        self.link.attiva = False
        self.link.save(update_fields=["attiva", "updated_at"])
        resp = self._mie(self.player, self.pg)
        self.assertEqual(resp.json(), [])

    def test_default_link_e_attivo(self):
        link = MissioneEvento.objects.create(
            missione=Missione.objects.create(titolo="Seconda", attiva=True),
            evento=self.evento,
        )
        self.assertTrue(link.attiva)

    def test_staffer_toggle_attiva_evento(self):
        resp = self._post(
            self.staffer,
            f"/api/plot/api/missioni/{self.missione.id}/set-attiva-evento/",
            {"evento_id": self.evento.id, "attiva": False},
        )
        self.assertEqual(resp.status_code, 200)
        self.link.refresh_from_db()
        self.assertFalse(self.link.attiva)
        resp_on = self._post(
            self.staffer,
            f"/api/plot/api/missioni/{self.missione.id}/set-attiva-evento/",
            {"evento_id": self.evento.id, "attiva": True},
        )
        self.assertEqual(resp_on.status_code, 200)
        self.link.refresh_from_db()
        self.assertTrue(self.link.attiva)

    def test_player_non_puo_toggle(self):
        resp = self._post(
            self.player,
            f"/api/plot/api/missioni/{self.missione.id}/set-attiva-evento/",
            {"evento_id": self.evento.id, "attiva": False},
        )
        self.assertEqual(resp.status_code, 403)

    def test_assegna_bloccata_se_disattiva(self):
        self.evento.started_at = timezone.now()
        self.evento.save(update_fields=["started_at", "updated_at"])
        self.evento.partecipanti.add(self.pg)
        self.link.attiva = False
        self.link.save(update_fields=["attiva", "updated_at"])
        resp = self._post(
            self.staffer,
            "/api/plot/api/missioni/assegna-risoluzione/",
            {
                "missione_id": str(self.missione.id),
                "evento_id": self.evento.id,
                "personaggio_id": self.pg.id,
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("disattivata", resp.json()["detail"].lower())

    def test_assegna_bloccata_se_non_iscritto(self):
        self.evento.started_at = timezone.now()
        self.evento.save(update_fields=["started_at", "updated_at"])
        resp = self._post(
            self.staffer,
            "/api/plot/api/missioni/assegna-risoluzione/",
            {
                "missione_id": str(self.missione.id),
                "evento_id": self.evento.id,
                "personaggio_id": self.pg.id,
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("iscritto", resp.json()["detail"].lower())

    def test_master_crea_con_attiva_false_per_evento(self):
        resp = self._post(
            self.master,
            "/api/plot/api/missioni/",
            {
                "titolo": "Nascosta all'inizio",
                "eventi_links": [{"evento_id": self.evento.id, "attiva": False}],
            },
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        mid = resp.json()["id"]
        link = MissioneEvento.objects.get(missione_id=mid, evento=self.evento)
        self.assertFalse(link.attiva)
        eventi = resp.json()["eventi"]
        self.assertEqual(len(eventi), 1)
        self.assertFalse(eventi[0]["attiva"])

    def test_evento_tasks_staff(self):
        resp = self._get(
            self.staffer,
            f"/api/plot/api/missioni/evento-tasks/?evento={self.evento.id}",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["tasks"]), 1)
        self.assertTrue(data["tasks"][0]["attiva"])

