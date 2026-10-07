"""Cessione oggetti via messaggio: zaino intero, salvo innesti e mutazioni."""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from personaggi.models import (
    TIPO_OGGETTO_FISICO,
    TIPO_OGGETTO_INNESTO,
    TIPO_OGGETTO_MATERIA,
    TIPO_OGGETTO_MUTAZIONE,
    Campagna,
    Messaggio,
    Oggetto,
    Personaggio,
)


class MessaggioCessioneOggettiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={
                "nome": "KOR35",
                "is_default": True,
                "is_base": True,
                "attiva": True,
            },
        )
        cls.user = User.objects.create_user(username="mittente_msg", password="test")
        cls.user_dest = User.objects.create_user(username="dest_msg", password="test")
        cls.mittente = Personaggio.objects.create(
            nome="Mittente", proprietario=cls.user, campagna=cls.campagna
        )
        cls.destinatario = Personaggio.objects.create(
            nome="Destinatario", proprietario=cls.user_dest, campagna=cls.campagna
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _oggetto(self, *, nome, tipo, equip=False, slot_corpo=None):
        oggetto = Oggetto.objects.create(
            nome=nome,
            tipo_oggetto=tipo,
            is_equipaggiato=equip,
            slot_corpo=slot_corpo,
            attacco_base="",
        )
        oggetto.sposta_in_inventario(self.mittente)
        return oggetto

    def _invia(self, oggetti_ids):
        with patch(
            "personaggi.transazioni_evento.gioco_live_consentito", return_value=True
        ):
            return self.client.post(
                reverse("personaggi:messaggio-send"),
                {
                    "destinatario_id": self.destinatario.id,
                    "mittente_personaggio_id": self.mittente.id,
                    "titolo": "Ti mando questo",
                    "testo": "<p>tieni</p>",
                    "oggetti_ids": oggetti_ids,
                },
                format="json",
            )

    def test_oggetto_modificato_resta_assemblato(self):
        anello = self._oggetto(nome="Anello d'argento", tipo=TIPO_OGGETTO_FISICO)
        materia = self._oggetto(nome="Materia di Aureola Benedetta", tipo=TIPO_OGGETTO_MATERIA)
        materia.ospitato_su = anello
        materia.sposta_in_inventario(None)
        materia.ospitato_su = anello
        materia.save(update_fields=["ospitato_su", "updated_at"])

        resp = self._invia([anello.id])
        self.assertEqual(resp.status_code, 201, resp.content)

        anello.refresh_from_db()
        materia.refresh_from_db()
        self.assertEqual(anello.inventario_corrente.id, self.destinatario.id)
        self.assertIsNone(materia.inventario_corrente)
        self.assertEqual(materia.ospitato_su_id, anello.id)

        msg = Messaggio.objects.filter(mittente_personaggio=self.mittente).latest("id")
        snap = msg.oggetti_allegati_snapshot
        self.assertEqual(len(snap), 1)
        self.assertIn("Materia di Aureola Benedetta", snap[0]["nome"])
        self.assertEqual(snap[0]["modifiche"][0]["id"], materia.id)

    def test_materia_sciolta_e_cedibile(self):
        materia = self._oggetto(nome="Materia sciolta", tipo=TIPO_OGGETTO_MATERIA)
        resp = self._invia([materia.id])
        self.assertEqual(resp.status_code, 201, resp.content)
        materia.refresh_from_db()
        self.assertEqual(materia.inventario_corrente.id, self.destinatario.id)
        self.assertIsNone(materia.ospitato_su_id)

    def test_innesto_e_mutazione_non_sono_cedibili(self):
        innesto = self._oggetto(
            nome="Innesto", tipo=TIPO_OGGETTO_INNESTO, slot_corpo="HD1"
        )
        mutazione = self._oggetto(nome="Mutazione", tipo=TIPO_OGGETTO_MUTAZIONE)
        resp = self._invia([innesto.id, mutazione.id])
        self.assertEqual(resp.status_code, 400, resp.content)
        innesto.refresh_from_db()
        mutazione.refresh_from_db()
        self.assertEqual(innesto.inventario_corrente.id, self.mittente.id)
        self.assertEqual(mutazione.inventario_corrente.id, self.mittente.id)

    def test_equipaggiato_non_e_cedibile(self):
        arma = self._oggetto(nome="Pugnale", tipo=TIPO_OGGETTO_FISICO, equip=True)
        resp = self._invia([arma.id])
        self.assertEqual(resp.status_code, 400, resp.content)
        arma.refresh_from_db()
        self.assertEqual(arma.inventario_corrente.id, self.mittente.id)
        self.assertTrue(arma.is_equipaggiato)
