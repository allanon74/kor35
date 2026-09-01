"""Firma social InstaFame: profilo, post e rubriche."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from personaggi.models import Campagna, Personaggio
from social.author_display import social_firma_for_personaggio
from social.models import SocialPost, SocialProfile
from social.models_rubriche import RUBRICA_ARTICOLO_PUBBLICATO, Rubrica, RubricaArticolo
from social.serializers import SocialPostSerializer, SocialProfileSerializer
from social.serializers_rubriche import RubricaArticoloListSerializer


class SocialFirmaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.user = User.objects.create_user(username="firma_user", password="test")
        cls.personaggio = Personaggio.objects.create(
            nome="Autore Firma", proprietario=cls.user, campagna=cls.campagna
        )
        cls.profile, _ = SocialProfile.objects.get_or_create(personaggio=cls.personaggio)
        cls.factory = APIRequestFactory()

    def test_serializer_salva_firma_testo(self):
        serializer = SocialProfileSerializer(
            self.profile, data={"firma_testo": "— Firmato dal bosco"}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertEqual(instance.firma_testo, "— Firmato dal bosco")

    def test_helper_firma_vuota_senza_campi(self):
        self.profile.firma_testo = ""
        self.profile.firma_banner = None
        self.profile.save(update_fields=["firma_testo", "firma_banner", "updated_at"])
        firma = social_firma_for_personaggio(self.personaggio)
        self.assertEqual(firma["testo"], "")
        self.assertIsNone(firma["banner"])

    def test_post_serializer_esporta_firma_autore(self):
        self.profile.firma_testo = "Viva KOR35"
        self.profile.save(update_fields=["firma_testo", "updated_at"])
        post = SocialPost.objects.create(
            autore=self.personaggio,
            titolo="Annuncio",
            testo="Contenuto breve",
        )
        request = self.factory.get("/api/social/posts/")
        data = SocialPostSerializer(post, context={"request": request}).data
        self.assertEqual(data["autore_firma_testo"], "Viva KOR35")
        self.assertIsNone(data["autore_firma_banner"])

    def test_articolo_rubrica_esporta_firma_solo_con_autore_personaggio(self):
        rubrica = Rubrica.objects.create(nome="Test Firma Rubrica")
        self.profile.firma_testo = "Redazione Vex"
        self.profile.save(update_fields=["firma_testo", "updated_at"])
        articolo = RubricaArticolo.objects.create(
            rubrica=rubrica,
            titolo="Scoop",
            corpo="<p>Test</p>",
            stato=RUBRICA_ARTICOLO_PUBBLICATO,
            autore_personaggio=self.personaggio,
        )
        request = self.factory.get("/api/social/rubriche-articoli/")
        data = RubricaArticoloListSerializer(articolo, context={"request": request}).data
        self.assertEqual(data["autore_firma_testo"], "Redazione Vex")

        articolo.firma_libera = "Redazione Anonima"
        articolo.autore_personaggio = None
        articolo.save(update_fields=["firma_libera", "autore_personaggio", "updated_at"])
        data_libera = RubricaArticoloListSerializer(articolo, context={"request": request}).data
        self.assertEqual(data_libera["autore_firma_testo"], "")
        self.assertIsNone(data_libera["autore_firma_banner"])
