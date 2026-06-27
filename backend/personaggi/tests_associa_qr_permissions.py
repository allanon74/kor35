"""Permessi associazione QR diretta (editor staff: nodi, manifesti, …)."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    Campagna,
    CampagnaUtente,
    Nodo,
    QrCode,
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
