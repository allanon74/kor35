"""Visibilità feed InstaFame: KORP, campagna, personaggio attivo."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from personaggi.models import (
    Campagna,
    Korp,
    Personaggio,
    PersonaggioCarrieraMembership,
    TIER_3,
    TipoCarriera,
)
from social.models import SocialPost
from social.views import SocialPostViewSet


class InstafameKorpVisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="korp_vis_user", password="test")
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.tipo_korp, _ = TipoCarriera.objects.get_or_create(codice="korp", defaults={"nome": "KORP"})

        cls.korp_alfa = Korp.objects.create(
            nome="KORP Alfa Vis",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_korp,
        )
        cls.korp_beta = Korp.objects.create(
            nome="KORP Beta Vis",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_korp,
        )

        cls.viewer = Personaggio.objects.create(
            nome="Viewer Multi KORP",
            proprietario=cls.user,
            campagna=cls.campagna,
        )
        now = timezone.now()
        PersonaggioCarrieraMembership.objects.create(
            personaggio=cls.viewer,
            carriera=cls.korp_alfa,
            tipo_carriera=cls.tipo_korp,
            data_da=now - timedelta(days=30),
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=cls.viewer,
            carriera=cls.korp_beta,
            tipo_carriera=cls.tipo_korp,
            data_da=now - timedelta(days=1),
        )

        cls.author = Personaggio.objects.create(nome="Autore KORP", campagna=cls.campagna)
        cls.post_pub = SocialPost.objects.create(
            autore=cls.author,
            titolo="Pubblico",
            testo="tutti",
            visibilita="PUB",
        )
        cls.post_alfa = SocialPost.objects.create(
            autore=cls.author,
            titolo="Solo Alfa",
            testo="alfa",
            visibilita="KORP",
            korp_visibilita=cls.korp_alfa,
        )
        cls.post_beta = SocialPost.objects.create(
            autore=cls.author,
            titolo="Solo Beta",
            testo="beta",
            visibilita="KORP",
            korp_visibilita=cls.korp_beta,
        )

    def _list_ids(self, personaggio):
        factory = APIRequestFactory()
        view = SocialPostViewSet.as_view({"get": "list"})
        request = factory.get(f"/api/social/posts/?personaggio_id={personaggio.id}")
        request.META["HTTP_X_CAMPAGNA"] = "kor35"
        force_authenticate(request, user=self.user)
        response = view(request)
        self.assertEqual(response.status_code, 200)
        items = response.data.get("results", response.data)
        return {row["id"] for row in items}

    def test_viewer_with_multiple_korps_sees_all_matching_posts(self):
        ids = self._list_ids(self.viewer)
        self.assertIn(self.post_pub.id, ids)
        self.assertIn(self.post_alfa.id, ids)
        self.assertIn(self.post_beta.id, ids)

    def test_viewer_without_korp_sees_only_public(self):
        outsider = Personaggio.objects.create(
            nome="Senza KORP",
            proprietario=self.user,
            campagna=self.campagna,
        )
        ids = self._list_ids(outsider)
        self.assertIn(self.post_pub.id, ids)
        self.assertNotIn(self.post_alfa.id, ids)
        self.assertNotIn(self.post_beta.id, ids)

    def test_pub_post_visible_if_author_campagna_inactive_with_single_active_campaign(self):
        Campagna.objects.exclude(pk=self.campagna.pk).update(attiva=False)
        stale = Campagna.objects.create(slug="stale-camp-vis", nome="Stale", attiva=False)
        self.author.campagna = stale
        self.author.save(update_fields=["campagna"])
        ids = self._list_ids(self.viewer)
        self.assertIn(self.post_pub.id, ids)
