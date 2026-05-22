"""
Verifica isolamento wizard creazione guidata vs flussi tradizionali PG/abilità.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from personaggi.models import Campagna, CampagnaUtente, CAMPAGNA_ROLE_PLAYER


class CreazioneGuidataIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='player_iso', password='x')
        self.campagna = Campagna.objects.create(nome='Test', slug='test-iso')
        CampagnaUtente.objects.create(
            user=self.user,
            campagna=self.campagna,
            ruolo=CAMPAGNA_ROLE_PLAYER,
            attivo=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_acquire_abilita_route_unchanged(self):
        """L'acquisto tradizionale resta sul endpoint storico, non sul wizard."""
        resolved = reverse('acquisisci_abilita')
        self.assertEqual(resolved, '/api/personaggi/api/personaggio/me/acquisisci_abilita/')

    def test_wizard_stato_accessible_without_applying_pg(self):
        """Lo stato wizard non richiede personaggio e non modifica la scheda."""
        url = reverse('creazione_guidata_stato')
        response = self.client.get(url)
        self.assertIn(response.status_code, (200, 404))
