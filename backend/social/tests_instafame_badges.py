from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from personaggi.models import (
    Campagna,
    Carica,
    Carriera,
    Personaggio,
    PersonaggioCarrieraMembership,
    TIER_3,
    TipoCarriera,
)
from social.author_display import social_cariche_for_personaggio
from social.models import SocialPost
from social.serializers import SocialPostSerializer
from rest_framework.test import APIRequestFactory


class InstafameBadgeCaricheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="badge_user", password="x")
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.tipo_prof, _ = TipoCarriera.objects.get_or_create(codice="professione", defaults={"nome": "Professione"})
        cls.carriera = Carriera.objects.create(
            nome="Carriera Badge",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_prof,
        )
        cls.carica_pub = Carica.objects.create(carriera=cls.carriera, nome="Capo visibile", ordine=1)
        cls.carica_hidden = Carica.objects.create(carriera=cls.carriera, nome="Capo nascosto", ordine=2)
        cls.author = Personaggio.objects.create(
            nome="Autore Badge",
            campagna=cls.campagna,
            badge_instafame="DIAMOND",
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=cls.author,
            carriera=cls.carriera,
            tipo_carriera=cls.tipo_prof,
            carica=cls.carica_pub,
            visibile_social=True,
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=cls.author,
            carriera=cls.carriera,
            tipo_carriera=cls.tipo_prof,
            carica=cls.carica_hidden,
            visibile_social=False,
            data_da=timezone.now(),
        )
        cls.post = SocialPost.objects.create(
            autore=cls.author,
            titolo="Post badge",
            testo="x",
            visibilita="PUB",
        )

    def test_social_cariche_respects_visibile_flag(self):
        rows = social_cariche_for_personaggio(self.author)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["carica_nome"], "Capo visibile")

    def test_post_serializer_exposes_author_badge(self):
        factory = APIRequestFactory()
        request = factory.get("/api/social/posts/")
        data = SocialPostSerializer(self.post, context={"request": request}).data
        self.assertEqual(data["autore_badge_instafame"], "DIAMOND")
