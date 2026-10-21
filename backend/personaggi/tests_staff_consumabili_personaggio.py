"""Staff personaggi: aggiungi, modifica e togli consumabili, anche da tessitura."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from personaggi.models import (
    AURA,
    Campagna,
    ConsumabilePersonaggio,
    Personaggio,
    PersonaggioLog,
    Punteggio,
    Tessitura,
    TipologiaPersonaggio,
)


class StaffConsumabiliPersonaggioTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff-cons", password="x", is_staff=True, is_superuser=True
        )
        self.client.force_authenticate(user=self.staff)
        self.campagna = Campagna.objects.create(
            slug="kor35-staff-cons",
            nome="Kor35 Staff Consumabili",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        self.tipo = TipologiaPersonaggio.objects.create(nome="PG staff cons", giocante=True)
        self.pg = Personaggio.objects.create(
            nome="Giocatore consumabili",
            tipologia=self.tipo,
            campagna=self.campagna,
        )
        self.altro = Personaggio.objects.create(
            nome="Altro consumabili",
            tipologia=self.tipo,
            campagna=self.campagna,
        )
        self.aura = Punteggio.objects.create(nome="Aura staff cons", sigla="ASC", tipo=AURA)
        self.tess = Tessitura.objects.create(
            nome="Tinta di luna",
            testo="brilla",
            formula="{aura} + 1",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )
        self.headers = {"HTTP_X_CAMPAGNA": self.campagna.slug}
        self.base = f"/api/personaggi/api/staff/personaggi/{self.pg.id}"

    def test_crea_n_copie_da_tessitura_e_compongono_il_dettaglio(self):
        resp = self.client.post(
            f"{self.base}/aggiungi-consumabile/",
            {"tessitura_id": self.tess.id, "quantita": 3, "utilizzi_rimanenti": 2},
            format="json",
            **self.headers,
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(len(body["consumabili"]), 3)
        for row in body["consumabili"]:
            self.assertEqual(row["nome"], "Tinta di luna")
            self.assertEqual(row["descrizione"], "brilla")
            self.assertEqual(row["formula"], "{aura} + 1")
            self.assertEqual(row["utilizzi_rimanenti"], 2)
            self.assertEqual(row["tessitura_id"], self.tess.id)
        self.assertEqual(
            ConsumabilePersonaggio.objects.filter(personaggio=self.pg, tessitura=self.tess).count(),
            3,
        )
        self.assertTrue(
            PersonaggioLog.objects.filter(personaggio=self.pg, testo_log__icontains="creati 3").exists()
        )

    def test_aggiunta_manuale_modifica_e_rimozione(self):
        creato = self.client.post(
            f"{self.base}/aggiungi-consumabile/",
            {
                "nome": "Boccetta",
                "descrizione": "fatta a mano",
                "utilizzi_rimanenti": 1,
                "quantita": 1,
                "data_scadenza": "2026-12-01",
            },
            format="json",
            **self.headers,
        )
        self.assertEqual(creato.status_code, 201, creato.content)
        cid = creato.json()["consumabili"][0]["id"]

        aggiornato = self.client.post(
            f"{self.base}/aggiorna-consumabile/",
            {"consumabile_id": cid, "utilizzi_rimanenti": 5, "data_scadenza": "2027-01-15"},
            format="json",
            **self.headers,
        )
        self.assertEqual(aggiornato.status_code, 200, aggiornato.content)
        row = aggiornato.json()["consumabili"][0]
        self.assertEqual(row["utilizzi_rimanenti"], 5)
        self.assertEqual(row["data_scadenza"], "2027-01-15")

        rimosso = self.client.post(
            f"{self.base}/rimuovi-consumabile/",
            {"consumabile_id": cid},
            format="json",
            **self.headers,
        )
        self.assertEqual(rimosso.status_code, 200, rimosso.content)
        self.assertEqual(rimosso.json()["consumabili"], [])
        self.assertFalse(ConsumabilePersonaggio.objects.filter(pk=cid).exists())

    def test_non_tocca_i_consumabili_di_un_altro_personaggio(self):
        estraneo = ConsumabilePersonaggio.objects.create(
            personaggio=self.altro,
            nome="Non tuo",
            descrizione="x",
            utilizzi_rimanenti=1,
            data_scadenza=timezone.localdate() + timedelta(days=2),
        )
        resp = self.client.post(
            f"{self.base}/rimuovi-consumabile/",
            {"consumabile_id": estraneo.id},
            format="json",
            **self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(ConsumabilePersonaggio.objects.filter(pk=estraneo.id).exists())

    def test_catalogo_tessiture_include_la_tessitura_di_campagna(self):
        resp = self.client.get(f"{self.base}/catalogo-tessiture/", **self.headers)
        self.assertEqual(resp.status_code, 200, resp.content)
        ids = [row["id"] for row in resp.json()]
        self.assertIn(self.tess.id, ids)

    def test_quantita_fuori_scala_rifiutata(self):
        resp = self.client.post(
            f"{self.base}/aggiungi-consumabile/",
            {"tessitura_id": self.tess.id, "quantita": 0},
            format="json",
            **self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ConsumabilePersonaggio.objects.filter(personaggio=self.pg).exists())
