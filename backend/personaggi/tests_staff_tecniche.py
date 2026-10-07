"""Staff hub personaggi: tecniche possedute (infusioni, tessiture, cerimoniali)."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    Cerimoniale,
    Infusione,
    InfusioneCaratteristica,
    Personaggio,
    Punteggio,
    Tessitura,
    TessituraEffettoRuntime,
    TipologiaPersonaggio,
)


class StaffTecnichePosseduteTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff_tecniche", password="x", is_staff=True, is_superuser=True
        )
        self.client.force_authenticate(user=self.staff)
        self.tipo = TipologiaPersonaggio.objects.create(nome="PG Tecniche", giocante=True)
        self.pg = Personaggio.objects.create(nome="PG Tecniche", tipologia=self.tipo)
        self.aura = Punteggio.objects.create(nome="Aura Staff Tec", sigla="ASTX", tipo=AURA)
        self.base = f"/api/personaggi/api/staff/personaggi/{self.pg.id}"

    def _infusione(self, nome="Infusione staff"):
        return Infusione.objects.create(nome=nome, aura_richiesta=self.aura, testo="x")

    def test_detail_include_liste_vuote(self):
        res = self.client.get(f"{self.base}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        body = res.json()
        self.assertEqual(body.get("infusioni_possedute"), [])
        self.assertEqual(body.get("tessiture_possedute"), [])
        self.assertEqual(body.get("cerimoniali_posseduti"), [])

    def test_omaggio_e_revoca_senza_rimborso(self):
        inf = self._infusione()
        self.pg.modifica_crediti(Decimal("40"), "seed")

        res_add = self.client.post(
            f"{self.base}/assegna-tecnica/",
            {"tipo": "infusione", "tecnica_id": inf.id, "omaggio": True, "motivo": "Plot"},
            format="json",
        )
        self.assertEqual(res_add.status_code, status.HTTP_200_OK, res_add.content)
        possedute = res_add.json().get("infusioni_possedute") or []
        self.assertEqual(len(possedute), 1)
        self.assertEqual(possedute[0]["id"], inf.id)
        self.assertEqual(possedute[0]["nome"], inf.nome)
        self.assertEqual(possedute[0]["costo_crediti_pagato"], "0.00")
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.crediti, Decimal("40"))

        res_rm = self.client.post(
            f"{self.base}/rimuovi-tecnica/",
            {"tipo": "infusione", "tecnica_id": inf.id, "motivo": "Correzione"},
            format="json",
        )
        self.assertEqual(res_rm.status_code, status.HTTP_200_OK, res_rm.content)
        self.assertEqual(res_rm.json().get("infusioni_possedute"), [])
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.crediti, Decimal("40"))

    def test_acquisto_addebita_e_revoca_rimborsa(self):
        inf = self._infusione("Infusione a pagamento")
        self.pg.modifica_crediti(Decimal("10"), "seed")
        with patch(
            "personaggi.tecniche_personaggio_ops.calcola_costo_tecnica_acquisto",
            return_value=25,
        ):
            res_fail = self.client.post(
                f"{self.base}/assegna-tecnica/",
                {"tipo": "infusione", "tecnica_id": inf.id, "omaggio": False, "motivo": "Acquisto"},
                format="json",
            )
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST, res_fail.content)
        self.assertIn("Crediti insufficienti", res_fail.json().get("detail", ""))

        self.pg.modifica_crediti(Decimal("30"), "integrazione")
        with patch(
            "personaggi.tecniche_personaggio_ops.calcola_costo_tecnica_acquisto",
            return_value=25,
        ):
            res_ok = self.client.post(
                f"{self.base}/assegna-tecnica/",
                {"tipo": "infusione", "tecnica_id": inf.id, "motivo": "Acquisto"},
                format="json",
            )
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK, res_ok.content)
        row = (res_ok.json().get("infusioni_possedute") or [])[0]
        self.assertEqual(row["costo_crediti_pagato"], "25.00")
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.crediti, Decimal("15"))

        res_rm = self.client.post(
            f"{self.base}/rimuovi-tecnica/",
            {"tipo": "infusione", "tecnica_id": inf.id, "motivo": "Reso"},
            format="json",
        )
        self.assertEqual(res_rm.status_code, status.HTTP_200_OK, res_rm.content)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.crediti, Decimal("40"))

    def test_acquisto_rispetta_requisiti_omaggio_li_ignora(self):
        car = Punteggio.objects.create(nome="Forza Staff", sigla="FSS", tipo=CARATTERISTICA)
        inf = self._infusione("Infusione alta")
        InfusioneCaratteristica.objects.create(infusione=inf, caratteristica=car, valore=3)

        res_buy = self.client.post(
            f"{self.base}/assegna-tecnica/",
            {"tipo": "infusione", "tecnica_id": inf.id, "omaggio": False},
            format="json",
        )
        self.assertEqual(res_buy.status_code, status.HTTP_400_BAD_REQUEST, res_buy.content)
        self.assertIn("Livello", res_buy.json().get("detail", ""))

        res_gift = self.client.post(
            f"{self.base}/assegna-tecnica/",
            {"tipo": "infusione", "tecnica_id": inf.id, "omaggio": True, "motivo": "PNG"},
            format="json",
        )
        self.assertEqual(res_gift.status_code, status.HTTP_200_OK, res_gift.content)
        row = res_gift.json()["infusioni_possedute"][0]
        self.assertEqual(row["livello"], 3)
        self.assertEqual(row["aura"], self.aura.nome)

    def test_catalogo_esclude_possedute_e_copre_i_tre_tipi(self):
        inf = self._infusione("Visibile")
        altra = self._infusione("Nascosta")
        self.pg.infusioni_possedute.add(altra)
        tes = Tessitura.objects.create(nome="Tessitura staff", aura_richiesta=self.aura, testo="t")
        cer = Cerimoniale.objects.create(
            nome="Cerimoniale staff", aura_richiesta=self.aura, testo="c", liv=2
        )

        res_inf = self.client.get(f"{self.base}/tecniche-catalogo/?tipo=infusione")
        self.assertEqual(res_inf.status_code, status.HTTP_200_OK, res_inf.content)
        ids = {row["id"] for row in res_inf.json()}
        self.assertIn(inf.id, ids)
        self.assertNotIn(altra.id, ids)

        res_tes = self.client.post(
            f"{self.base}/assegna-tecnica/",
            {"tipo": "tessitura", "tecnica_id": tes.id, "omaggio": True},
            format="json",
        )
        self.assertEqual(res_tes.status_code, status.HTTP_200_OK, res_tes.content)
        self.assertEqual(res_tes.json()["tessiture_possedute"][0]["nome"], tes.nome)

        res_cer = self.client.post(
            f"{self.base}/assegna-tecnica/",
            {"tipo": "cerimoniale", "tecnica_id": cer.id, "omaggio": True},
            format="json",
        )
        self.assertEqual(res_cer.status_code, status.HTTP_200_OK, res_cer.content)
        self.assertEqual(res_cer.json()["cerimoniali_posseduti"][0]["livello"], 2)

        res_bad = self.client.get(f"{self.base}/tecniche-catalogo/?tipo=pippo")
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_revoca_tessitura_chiude_runtime_attivo(self):
        tes = Tessitura.objects.create(nome="Tessitura runtime", aura_richiesta=self.aura, testo="t")
        self.client.post(
            f"{self.base}/assegna-tecnica/",
            {"tipo": "tessitura", "tecnica_id": tes.id, "omaggio": True},
            format="json",
        )
        runtime = TessituraEffettoRuntime.objects.create(
            personaggio=self.pg,
            tessitura=tes,
            fine=timezone.now() + timedelta(hours=1),
            is_attivo=True,
        )
        res = self.client.post(
            f"{self.base}/rimuovi-tecnica/",
            {"tipo": "tessitura", "tecnica_id": tes.id, "motivo": "Stop"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        runtime.refresh_from_db()
        self.assertFalse(runtime.is_attivo)
        self.assertEqual(runtime.motivo_fine, "staff_revoca")

    def test_revoca_durante_evento(self):
        from gestione_plot.models import Evento

        inf = self._infusione("Durante evento")
        now = timezone.now()
        Evento.objects.create(
            titolo="Evento in corso",
            data_inizio=now - timedelta(hours=1),
            data_fine=now + timedelta(hours=4),
        )
        self.client.post(
            f"{self.base}/assegna-tecnica/",
            {"tipo": "infusione", "tecnica_id": inf.id, "omaggio": True},
            format="json",
        )
        res = self.client.post(
            f"{self.base}/rimuovi-tecnica/",
            {"tipo": "infusione", "tecnica_id": inf.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        self.assertEqual(res.json().get("infusioni_possedute"), [])

    def test_non_staff_non_puo_assegnare(self):
        utente = User.objects.create_user(username="giocatore_tec", password="x")
        self.client.force_authenticate(user=utente)
        inf = self._infusione()
        res = self.client.post(
            f"{self.base}/assegna-tecnica/",
            {"tipo": "infusione", "tecnica_id": inf.id, "omaggio": True},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, res.content)
