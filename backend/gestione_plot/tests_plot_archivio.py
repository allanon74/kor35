"""Archivio plot: sola consultazione e uscita dal gioco live."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from gestione_plot.eventi_pubblici import eventi_pubblici_queryset
from gestione_plot.models import Evento, GiornoEvento
from gestione_plot.plot_archivio import unisci_target_plot
from personaggi.transazioni_evento import get_evento_aperto_corso

User = get_user_model()


class UnisciTargetPlotTests(APITestCase):
    def test_mantiene_i_collegamenti_archiviati(self):
        esistenti = {1: False, 2: True}
        target = {2: False, 3: True}
        out = unisci_target_plot(esistenti, target, archiviati_ids=[1, 3])
        self.assertEqual(out, {1: False, 2: False})


class PlotArchivioApiTests(APITestCase):
    def setUp(self):
        self.master = User.objects.create_superuser("master_archivio", "a@test.local", "x")
        now = timezone.now()
        self.vecchio = Evento.objects.create(
            titolo="Plot vecchio",
            data_inizio=now - timedelta(days=40),
            data_fine=now - timedelta(days=38),
            started_at=now - timedelta(days=40),
        )
        self.aperto = Evento.objects.create(
            titolo="Plot aperto",
            data_inizio=now - timedelta(hours=2),
            data_fine=now + timedelta(days=1),
        )
        self.client.force_authenticate(user=self.master)

    def test_archivia_blocca_le_modifiche_e_ripristina(self):
        resp = self.client.post(f"/api/plot/api/eventi/{self.vecchio.id}/archivia/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIsNotNone(resp.data["archiviato_at"])

        patch = self.client.patch(
            f"/api/plot/api/eventi/{self.vecchio.id}/",
            {"titolo": "Cambiato"},
            format="json",
        )
        self.assertEqual(patch.status_code, 400, patch.data)
        self.assertIn("consultazione", str(patch.data).lower())
        self.vecchio.refresh_from_db()
        self.assertEqual(self.vecchio.titolo, "Plot vecchio")

        delete = self.client.delete(f"/api/plot/api/eventi/{self.vecchio.id}/")
        self.assertEqual(delete.status_code, 400, getattr(delete, "data", delete.content))

        giorno = self.client.post(
            "/api/plot/api/giorni/",
            {
                "evento": self.vecchio.id,
                "titolo": "Giorno",
                "sinossi_breve": "x",
                "data_ora_inizio": timezone.now().isoformat(),
                "data_ora_fine": (timezone.now() + timedelta(hours=2)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(giorno.status_code, 400, giorno.data)
        self.assertIn("consultazione", str(giorno.data).lower())

        inizia = self.client.post(f"/api/plot/api/eventi/{self.vecchio.id}/inizia/", {}, format="json")
        self.assertEqual(inizia.status_code, 400, inizia.data)

        opzioni = self.client.get("/api/plot/api/eventi/opzioni/")
        self.assertEqual(opzioni.status_code, 200, opzioni.data)
        ids = {row["id"] for row in opzioni.data}
        self.assertNotIn(self.vecchio.id, ids)
        self.assertIn(self.aperto.id, ids)

        ripristina = self.client.post(
            f"/api/plot/api/eventi/{self.vecchio.id}/ripristina/",
            {},
            format="json",
        )
        self.assertEqual(ripristina.status_code, 200, ripristina.data)
        self.assertIsNone(ripristina.data["archiviato_at"])
        patch_ok = self.client.patch(
            f"/api/plot/api/eventi/{self.vecchio.id}/",
            {"titolo": "Di nuovo attivo"},
            format="json",
        )
        self.assertEqual(patch_ok.status_code, 200, patch_ok.data)

    def test_giorno_esistente_non_si_modifica(self):
        now = timezone.now()
        giorno = GiornoEvento.objects.create(
            evento=self.vecchio,
            titolo="Sabato",
            sinossi_breve="note",
            data_ora_inizio=now,
            data_ora_fine=now + timedelta(hours=4),
        )
        self.client.post(f"/api/plot/api/eventi/{self.vecchio.id}/archivia/", {}, format="json")
        resp = self.client.patch(
            f"/api/plot/api/giorni/{giorno.id}/",
            {"titolo": "Nuovo"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        giorno.refresh_from_db()
        self.assertEqual(giorno.titolo, "Sabato")

    def test_archiviato_esce_da_pubblico_e_dal_live(self):
        now = timezone.now()
        self.vecchio.data_inizio = now - timedelta(days=7)
        self.vecchio.data_fine = now - timedelta(days=5)
        self.vecchio.started_at = now - timedelta(days=7)
        self.vecchio.ended_at = None
        self.vecchio.save()
        self.assertEqual(get_evento_aperto_corso().id, self.vecchio.id)
        self.assertTrue(eventi_pubblici_queryset().filter(pk=self.vecchio.id).exists())

        self.client.post(f"/api/plot/api/eventi/{self.vecchio.id}/archivia/", {}, format="json")
        self.assertEqual(get_evento_aperto_corso().id, self.aperto.id)
        self.assertFalse(eventi_pubblici_queryset().filter(pk=self.vecchio.id).exists())
        self.assertTrue(eventi_pubblici_queryset().filter(pk=self.aperto.id).exists())
