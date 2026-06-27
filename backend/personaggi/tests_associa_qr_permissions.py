"""Permessi e flusso associazione QR diretta (editor staff: nodi, manifesti, …)."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from gestione_plot.models import Quest, QuestVista
from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    Campagna,
    CampagnaUtente,
    Manifesto,
    Nodo,
    QrCode,
    Tessitura,
)


class AssociaQrDirettoPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="master_qr_perm", password="pass")
        User.objects.filter(pk=self.user.pk).update(is_staff=False)
        self.user.refresh_from_db()
        self.campagna = Campagna.objects.create(slug="kor35-qr-perm", nome="QR perm", attiva=True)
        CampagnaUtente.objects.create(
            campagna=self.campagna,
            user=self.user,
            ruolo=CAMPAGNA_ROLE_MASTER,
            attivo=True,
        )
        self.client.force_authenticate(self.user)
        self.headers = {"HTTP_X_CAMPAGNA": self.campagna.slug}

    def test_campagna_master_can_associa_qr_a_nodo(self):
        nodo = Nodo.objects.create(nome="Nodo assoc perm", testo="", tipo_nodo="MIN")
        qr = QrCode.objects.create()
        url = f"/api/personaggi/api/a-vista/{nodo.pk}/associa-qr/"
        r = self.client.post(url, {"qr_id": qr.id, "force": False}, format="json", **self.headers)
        self.assertEqual(r.status_code, 200, r.content)
        qr.refresh_from_db()
        self.assertEqual(qr.vista_id, nodo.pk)

    def test_non_staff_non_master_forbidden(self):
        outsider = User.objects.create_user(username="outsider_qr", password="pass")
        User.objects.filter(pk=outsider.pk).update(is_staff=False)
        self.client.force_authenticate(outsider)
        nodo = Nodo.objects.create(nome="Nodo deny", testo="", tipo_nodo="MIN")
        qr = QrCode.objects.create()
        url = f"/api/personaggi/api/a-vista/{nodo.pk}/associa-qr/"
        r = self.client.post(url, {"qr_id": qr.id}, format="json", **self.headers)
        self.assertEqual(r.status_code, 403)

    def _associa_diretto(self, avista_pk, qr):
        url = f"/api/personaggi/api/a-vista/{avista_pk}/associa-qr/"
        return self.client.post(url, {"qr_id": qr.id, "force": False}, format="json", **self.headers)

    def test_campagna_master_associa_manifesto_tessitura(self):
        manifesto = Manifesto.objects.create(nome="Man QR", testo="")
        tessitura = Tessitura.objects.create(nome="Tes QR", testo="")
        qr_m = QrCode.objects.create()
        qr_t = QrCode.objects.create()
        r1 = self._associa_diretto(manifesto.pk, qr_m)
        r2 = self._associa_diretto(tessitura.pk, qr_t)
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(r2.status_code, 200, r2.content)
        qr_m.refresh_from_db()
        qr_t.refresh_from_db()
        self.assertEqual(qr_m.vista_id, manifesto.pk)
        self.assertEqual(qr_t.vista_id, tessitura.pk)

    def test_associa_qr_già_usato_risponde_409(self):
        nodo_a = Nodo.objects.create(nome="Nodo A", testo="", tipo_nodo="MIN")
        nodo_b = Nodo.objects.create(nome="Nodo B", testo="", tipo_nodo="MIN")
        qr = QrCode.objects.create()
        r1 = self._associa_diretto(nodo_a.pk, qr)
        self.assertEqual(r1.status_code, 200, r1.content)
        r2 = self._associa_diretto(nodo_b.pk, qr)
        self.assertEqual(r2.status_code, 409, r2.content)
        self.assertTrue(r2.json().get("already_associated"))

    def test_force_spostamento_associazione(self):
        nodo_a = Nodo.objects.create(nome="Nodo force A", testo="", tipo_nodo="MIN")
        nodo_b = Nodo.objects.create(nome="Nodo force B", testo="", tipo_nodo="MIN")
        qr = QrCode.objects.create()
        self._associa_diretto(nodo_a.pk, qr)
        url = f"/api/personaggi/api/a-vista/{nodo_b.pk}/associa-qr/"
        r = self.client.post(url, {"qr_id": qr.id, "force": True}, format="json", **self.headers)
        self.assertEqual(r.status_code, 200, r.content)
        qr.refresh_from_db()
        self.assertEqual(qr.vista_id, nodo_b.pk)

    def test_plot_associa_qr_vista_quest_master(self):
        quest = Quest.objects.create(nome="Q test QR", descrizione="")
        manifesto = Manifesto.objects.create(nome="Man plot", testo="")
        vista = QuestVista.objects.create(
            quest=quest,
            nome="Vista plot QR",
            tipo="MAN",
            manifesto=manifesto,
        )
        qr = QrCode.objects.create()
        url = f"/api/plot/api/viste-setup/{vista.pk}/associa_qr/"
        r = self.client.post(url, {"qr_id": qr.id, "force": False}, format="json", **self.headers)
        self.assertEqual(r.status_code, 200, r.content)
        qr.refresh_from_db()
        self.assertEqual(qr.vista_id, manifesto.pk)
