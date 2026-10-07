"""Test innesco timer: attivazione, broadcast destinatari, ripristino active timers."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from personaggi.models import (
    InnescoTimer,
    Personaggio,
    QrCode,
    TipologiaPersonaggio,
)
from personaggi import qr_logic


class InnescoTimerBehaviorTests(TestCase):
    def setUp(self):
        self.tipo = TipologiaPersonaggio.objects.create(nome="Giocante", giocante=True)
        self.user = User.objects.create_user(username="innuser", password="pass")
        self.user2 = User.objects.create_user(username="innuser2", password="pass")
        self.pg = Personaggio.objects.create(
            nome="PG Inn", proprietario=self.user, tipologia=self.tipo
        )
        self.pg2 = Personaggio.objects.create(
            nome="PG Inn 2", proprietario=self.user2, tipologia=self.tipo
        )
        self.innesco = InnescoTimer.objects.create(
            nome="Allarme Globale",
            testo="Boom",
            durata_secondi=90,
            max_cariche=0,
            modalita_target=InnescoTimer.INNESCO_TARGET_GLOBAL,
        )
        self.qr = QrCode.objects.create(vista=self.innesco)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("personaggi.qr_logic._broadcast_timer_innesco")
    def test_scan_innesco_broadcast_include_tutti_giocanti(self, mock_broadcast):
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "timer_innesco")
        self.assertTrue(r.data["dati"]["scadenza"])
        mock_broadcast.assert_called_once()
        kwargs = mock_broadcast.call_args.kwargs
        self.assertEqual(kwargs["nome"], "Allarme Globale")
        self.assertEqual(kwargs["istanza"], "Istanza 1")
        ids = set(kwargs["recipient_personaggio_ids"])
        self.assertIn(self.pg.id, ids)
        self.assertIn(self.pg2.id, ids)

    @patch("personaggi.qr_logic._broadcast_timer_innesco")
    def test_active_timers_ripristina_innesco_per_altro_pg(self, mock_broadcast):
        payload, err = qr_logic.attiva_innesco_timer_per_personaggio(self.pg, self.innesco)
        self.assertIsNone(err)
        self.assertIsNotNone(payload)

        rows_self = qr_logic.active_innesco_timer_rows_for_personaggio(self.pg)
        rows_other = qr_logic.active_innesco_timer_rows_for_personaggio(self.pg2)
        self.assertEqual(len(rows_self), 1)
        self.assertEqual(len(rows_other), 1)
        self.assertEqual(rows_other[0]["nome"], "Allarme Globale")
        self.assertFalse(rows_other[0]["notifica_push"])  # push server-side allo scadere

        client2 = APIClient()
        client2.force_authenticate(self.user2)
        r = client2.get(
            "/api/personaggi/api/timers/active/",
            {"personaggio_id": self.pg2.id},
        )
        self.assertEqual(r.status_code, 200)
        nomi = [row["nome"] for row in r.data]
        self.assertIn("Allarme Globale", nomi)

    def test_scaduto_resta_finche_il_giocatore_non_preme_ok(self):
        payload, err = qr_logic.attiva_innesco_timer_per_personaggio(self.pg, self.innesco)
        self.assertIsNone(err)
        from personaggi.innesco_timer_ops import ack_innesco_timer_scaduto
        from personaggi.models import StatoInnescoTimerPersonaggio

        fine = timezone.now() - timedelta(seconds=5)
        StatoInnescoTimerPersonaggio.objects.filter(
            personaggio=self.pg, innesco_timer=self.innesco
        ).update(data_fine=fine)
        InnescoTimer.objects.filter(pk=self.innesco.pk).update(
            broadcast_data_fine=fine,
            broadcast_push_inviata=False,
        )
        rows = qr_logic.active_innesco_timer_rows_for_personaggio(self.pg2)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["scaduto"])
        self.assertEqual(rows[0]["id"], f"innesco:{self.innesco.pk}")

        ack_innesco_timer_scaduto(self.pg2, self.innesco, fine)
        self.assertEqual(qr_logic.active_innesco_timer_rows_for_personaggio(self.pg2), [])

        client2 = APIClient()
        client2.force_authenticate(self.user2)
        self.innesco.refresh_from_db()
        # Nuova scadenza non ancora confermata da user2 è già ackata sopra.
        # Una seconda attivazione deve ricomparire finché non c'è un nuovo Ok.
        InnescoTimer.objects.filter(pk=self.innesco.pk).update(
            broadcast_data_fine=timezone.now() - timedelta(seconds=2),
            broadcast_push_inviata=False,
        )
        rows_new = qr_logic.active_innesco_timer_rows_for_personaggio(self.pg2)
        self.assertEqual(len(rows_new), 1)
        r = client2.post(
            "/api/personaggi/api/timers/active/ack/",
            {
                "personaggio_id": self.pg2.id,
                "innesco_id": self.innesco.id,
                "data_fine": rows_new[0]["data_fine"],
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(qr_logic.active_innesco_timer_rows_for_personaggio(self.pg2), [])

    @patch("personaggi.timer_expiry_push._send_webpush_to_users")
    def test_dispatch_push_scadenza_a_proprietari(self, mock_send):
        from personaggi.timer_expiry_push import dispatch_expired_innesco_pushes

        mock_send.return_value = 2
        qr_logic.attiva_innesco_timer_per_personaggio(self.pg, self.innesco)
        InnescoTimer.objects.filter(pk=self.innesco.pk).update(
            broadcast_data_fine=timezone.now() - timedelta(seconds=1),
            broadcast_push_inviata=False,
        )
        stats = dispatch_expired_innesco_pushes()
        self.assertEqual(stats["dispatched"], 1)
        mock_send.assert_called_once()
        user_ids = set(mock_send.call_args.args[0])
        self.assertIn(self.user.id, user_ids)
        self.assertIn(self.user2.id, user_ids)
        self.innesco.refresh_from_db()
        self.assertTrue(self.innesco.broadcast_push_inviata)

    def test_dispatch_non_ripete_push(self):
        from personaggi.timer_expiry_push import dispatch_expired_innesco_pushes

        InnescoTimer.objects.filter(pk=self.innesco.pk).update(
            broadcast_data_fine=timezone.now() - timedelta(seconds=1),
            broadcast_push_inviata=True,
        )
        with patch("personaggi.timer_expiry_push._send_webpush_to_users") as mock_send:
            stats = dispatch_expired_innesco_pushes()
            self.assertEqual(stats["dispatched"], 0)
            mock_send.assert_not_called()

    def test_target_korp_evento_e_lista_personaggi(self):
        from personaggi.models import (
            Korp,
            PersonaggioCarrieraMembership,
            TIER_3,
            TipoCarriera,
        )
        from gestione_plot.models import Evento

        tipo_korp, _ = TipoCarriera.objects.get_or_create(codice="korp", defaults={"nome": "KORP"})
        korp = Korp.objects.create(
            nome="KORP Timer Test",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=tipo_korp,
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg2,
            carriera=korp,
            tipo_carriera=tipo_korp,
        )
        self.innesco.modalita_target = InnescoTimer.INNESCO_TARGET_KORP
        self.innesco.save()
        self.innesco.target_korps.add(korp)

        payload, err = qr_logic.attiva_innesco_timer_per_personaggio(self.pg, self.innesco)
        self.assertIsNone(err)
        ids = set(payload["recipient_personaggio_ids"])
        self.assertIn(self.pg2.id, ids)
        self.assertNotIn(self.pg.id, ids)
        self.assertEqual(qr_logic.active_innesco_timer_rows_for_personaggio(self.pg), [])
        self.assertEqual(len(qr_logic.active_innesco_timer_rows_for_personaggio(self.pg2)), 1)

        now = timezone.now()
        evento = Evento.objects.create(
            titolo="Evento timer",
            data_inizio=now,
            data_fine=now + timedelta(days=1),
        )
        evento.partecipanti.add(self.pg)
        self.innesco.modalita_target = InnescoTimer.INNESCO_TARGET_EVENTO
        self.innesco.target_evento = evento
        self.innesco.save()
        payload, err = qr_logic.attiva_innesco_timer_per_personaggio(self.pg2, self.innesco)
        self.assertIsNone(err)
        ids = set(payload["recipient_personaggio_ids"])
        self.assertIn(self.pg.id, ids)
        self.assertNotIn(self.pg2.id, ids)

        self.innesco.modalita_target = InnescoTimer.INNESCO_TARGET_PERSONAGGI
        self.innesco.target_evento = None
        self.innesco.save()
        self.innesco.target_personaggi.set([self.pg2])
        payload, err = qr_logic.attiva_innesco_timer_per_personaggio(self.pg, self.innesco)
        self.assertIsNone(err)
        ids = set(payload["recipient_personaggio_ids"])
        self.assertEqual(ids, {self.pg2.id})

    def test_istanze_hanno_qr_e_countdown_separati_e_condividono_i_dati(self):
        from personaggi.innesco_timer_ops import aggiungi_istanze, propaga_campi_gruppo

        extra = aggiungi_istanze(self.innesco, 1)[0]
        self.assertEqual(str(extra.gruppo_id), str(self.innesco.gruppo_id))
        self.assertNotEqual(extra.pk, self.innesco.pk)
        qr_extra = QrCode.objects.create(vista=extra)

        r = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.innesco.refresh_from_db()
        extra.refresh_from_db()
        self.assertIsNotNone(self.innesco.broadcast_data_fine)
        self.assertIsNone(extra.broadcast_data_fine)
        self.assertEqual(qr_extra.vista_id, extra.pk)

        self.innesco.nome = "Allarme rinominato"
        self.innesco.durata_secondi = 30
        self.innesco.save()
        propaga_campi_gruppo(self.innesco)
        extra.refresh_from_db()
        self.innesco.etichetta_istanza = "QR nord"
        self.innesco.save(update_fields=["etichetta_istanza", "updated_at"])
        payload, err = qr_logic.attiva_innesco_timer_per_personaggio(self.pg, self.innesco)
        self.assertIsNone(err)
        self.assertEqual(payload["nome"], "Allarme rinominato")
        self.assertEqual(payload["istanza"], "QR nord")
        rows = qr_logic.active_innesco_timer_rows_for_personaggio(self.pg2)
        self.assertEqual(rows[0]["istanza"], "QR nord")
        self.assertEqual(rows[0]["nome"], "Allarme rinominato")

        self.assertEqual(extra.nome, "Allarme rinominato")
        self.assertEqual(extra.durata_secondi, 30)
        self.assertIsNone(extra.broadcast_data_fine)


class InnescoTimerCaricheGiornoTests(TestCase):
    """Residuo giornaliero condiviso dall'istanza, regolabile dallo staff."""

    def setUp(self):
        self.tipo = TipologiaPersonaggio.objects.create(nome="Giocante cariche", giocante=True)
        self.user = User.objects.create_user(username="cariche-pg", password="pass")
        self.user2 = User.objects.create_user(username="cariche-pg2", password="pass")
        self.staff = User.objects.create_superuser(username="cariche-staff", password="pass", email="c@example.com")
        self.pg = Personaggio.objects.create(nome="PG Cariche", proprietario=self.user, tipologia=self.tipo)
        self.pg2 = Personaggio.objects.create(nome="PG Cariche 2", proprietario=self.user2, tipologia=self.tipo)
        self.innesco = InnescoTimer.objects.create(
            nome="Timer a cariche",
            durata_secondi=30,
            max_cariche=2,
            modalita_target=InnescoTimer.INNESCO_TARGET_GLOBAL,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.staff_client = APIClient()
        self.staff_client.force_authenticate(self.staff)

    def _scan(self, personaggio=None):
        return qr_logic.attiva_innesco_timer_per_personaggio(personaggio or self.pg, self.innesco)

    def test_due_giocatori_condividono_il_residuo_del_giorno(self):
        payload, err = self._scan(self.pg)
        self.assertIsNone(err)
        self.assertIsNotNone(payload)
        self.innesco.refresh_from_db()
        self.assertEqual(self.innesco.cariche_residue, 1)
        self.assertEqual(self.innesco.cariche_giorno, timezone.localdate())

        payload, err = self._scan(self.pg2)
        self.assertIsNone(err)
        self.innesco.refresh_from_db()
        self.assertEqual(self.innesco.cariche_residue, 0)

        payload, err = self._scan(self.pg)
        self.assertIsNone(payload)
        self.assertIn("oggi", err)
        self.innesco.refresh_from_db()
        self.assertEqual(self.innesco.cariche_residue, 0)

    def test_staff_aggiunge_e_toglie_il_residuo_di_oggi(self):
        self._scan(self.pg)
        self._scan(self.pg2)
        r = self.staff_client.post(
            f"/api/personaggi/api/staff/innesco-timer/{self.innesco.id}/cariche/",
            {"delta": 1},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["cariche_residue_oggi"], 1)
        payload, err = self._scan(self.pg)
        self.assertIsNone(err)
        self.assertIsNotNone(payload)

        r = self.staff_client.post(
            f"/api/personaggi/api/staff/innesco-timer/{self.innesco.id}/cariche/",
            {"delta": -1},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["cariche_residue_oggi"], 0)
        r = self.staff_client.post(
            f"/api/personaggi/api/staff/innesco-timer/{self.innesco.id}/cariche/",
            {"delta": -1},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["cariche_residue_oggi"], 0)

        r = self.staff_client.post(
            f"/api/personaggi/api/staff/innesco-timer/{self.innesco.id}/cariche/",
            {"delta": 5},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["cariche_residue_oggi"], 5)

        r = self.client.post(
            f"/api/personaggi/api/staff/innesco-timer/{self.innesco.id}/cariche/",
            {"delta": 1},
            format="json",
        )
        self.assertEqual(r.status_code, 403)
        r = self.staff_client.post(
            f"/api/personaggi/api/staff/innesco-timer/{self.innesco.id}/cariche/",
            {"delta": 0},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_lista_staff_non_scrive_il_residuo(self):
        r = self.staff_client.get("/api/personaggi/api/staff/innesco-timer/")
        self.assertEqual(r.status_code, 200, r.content)
        rows = r.data if isinstance(r.data, list) else r.data.get("results", [])
        row = next(item for item in rows if item["id"] == self.innesco.id)
        self.assertEqual(row["cariche_residue_oggi"], 2)
        self.innesco.refresh_from_db()
        self.assertIsNone(self.innesco.cariche_residue)
        self.assertIsNone(self.innesco.cariche_giorno)

    def test_nuovo_giorno_riparte_dal_massimo(self):
        self.innesco.cariche_residue = 0
        self.innesco.cariche_giorno = timezone.localdate() - timedelta(days=1)
        self.innesco.save(update_fields=["cariche_residue", "cariche_giorno", "updated_at"])
        payload, err = self._scan()
        self.assertIsNone(err)
        self.innesco.refresh_from_db()
        self.assertEqual(self.innesco.cariche_giorno, timezone.localdate())
        self.assertEqual(self.innesco.cariche_residue, 1)

    def test_istanze_non_condividono_il_residuo(self):
        from personaggi.innesco_timer_ops import aggiungi_istanze, propaga_campi_gruppo

        altra = aggiungi_istanze(self.innesco, 1)[0]
        self._scan()
        self._scan(self.pg2)
        self.innesco.refresh_from_db()
        altra.refresh_from_db()
        self.assertEqual(self.innesco.cariche_residue, 0)
        self.assertIsNone(altra.cariche_residue)

        payload, err = qr_logic.attiva_innesco_timer_per_personaggio(self.pg, altra)
        self.assertIsNone(err)
        altra.refresh_from_db()
        self.assertEqual(altra.cariche_residue, 1)
        self.innesco.refresh_from_db()
        self.assertEqual(self.innesco.cariche_residue, 0)

        self.innesco.nome = "Timer rinominato"
        self.innesco.save()
        propaga_campi_gruppo(self.innesco)
        altra.refresh_from_db()
        self.assertEqual(altra.nome, "Timer rinominato")
        self.assertEqual(altra.cariche_residue, 1)

    def test_cariche_illimitate_non_hanno_residuo(self):
        self.innesco.max_cariche = 0
        self.innesco.save(update_fields=["max_cariche", "updated_at"])
        for _ in range(3):
            payload, err = self._scan()
            self.assertIsNone(err)
            self.assertIsNotNone(payload)
        self.innesco.refresh_from_db()
        self.assertIsNone(self.innesco.cariche_residue)
        r = self.staff_client.post(
            f"/api/personaggi/api/staff/innesco-timer/{self.innesco.id}/cariche/",
            {"delta": 1},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("illimitate", r.data["error"])

    def test_rigenerazione_personale_non_scala_il_residuo_se_bloccata(self):
        self.innesco.rigenera_cariche_ogni_secondi = 3600
        self.innesco.save(update_fields=["rigenera_cariche_ogni_secondi", "updated_at"])
        self.assertIsNone(self._scan(self.pg)[1])
        self.assertIsNone(self._scan(self.pg)[1])
        self.innesco.refresh_from_db()
        self.assertEqual(self.innesco.cariche_residue, 0)
        r = self.staff_client.post(
            f"/api/personaggi/api/staff/innesco-timer/{self.innesco.id}/cariche/",
            {"delta": 1},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        payload, err = self._scan(self.pg)
        self.assertIsNone(payload)
        self.assertIn("rigenerazione", err)
        self.innesco.refresh_from_db()
        self.assertEqual(self.innesco.cariche_residue, 1)
        payload, err = self._scan(self.pg2)
        self.assertIsNone(err)
        self.innesco.refresh_from_db()
        self.assertEqual(self.innesco.cariche_residue, 0)