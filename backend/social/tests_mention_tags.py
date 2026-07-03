"""Tag @mention: sync da testo, signal post_save, edge sync senza notifiche."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from personaggi.models import Campagna, Personaggio
from social.mention_tags import (
    post_ids_needing_tag_resync,
    suppress_mention_notify,
    sync_post_tags,
)
from social.models import SocialPost, SocialPostTag


class MentionTagSyncTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="tag_sync_user", password="test")
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True
        )
        cls.autore = Personaggio.objects.create(nome="Autore Tag", proprietario=cls.user, campagna=cls.campagna)
        cls.cited_a = Personaggio.objects.create(nome="Citato A", proprietario=cls.user, campagna=cls.campagna)
        cls.cited_b = Personaggio.objects.create(nome="Citato B", proprietario=cls.user, campagna=cls.campagna)

    def test_post_save_creates_tags_from_text(self):
        post = SocialPost.objects.create(
            autore=self.autore,
            titolo="Titolo",
            testo=f"Ciao @{self.cited_a.id} e @{self.cited_b.id}",
        )
        tag_ids = set(SocialPostTag.objects.filter(post=post).values_list("personaggio_id", flat=True))
        self.assertEqual(tag_ids, {self.cited_a.id, self.cited_b.id})

    def test_post_ids_needing_tag_resync_detects_drift(self):
        post = SocialPost.objects.create(
            autore=self.autore,
            titolo="Drift",
            testo=f"@{self.cited_a.id}",
        )
        SocialPostTag.objects.filter(post=post).delete()
        self.assertIn(post.id, post_ids_needing_tag_resync())

    @patch("social.mention_notifications.notify_instafame_mentions")
    def test_sync_post_tags_respects_suppress_mention_notify(self, mock_notify):
        post = SocialPost.objects.create(
            autore=self.autore,
            titolo="No push",
            testo=f"@{self.cited_a.id}",
        )
        mock_notify.reset_mock()
        SocialPostTag.objects.filter(post=post).delete()
        with suppress_mention_notify():
            sync_post_tags(post, notify=True)
        mock_notify.assert_not_called()
        self.assertTrue(
            SocialPostTag.objects.filter(post=post, personaggio_id=self.cited_a.id).exists()
        )

    @patch("social.mention_notifications.notify_instafame_mentions")
    def test_sync_post_tags_notifies_new_mentions_by_default(self, mock_notify):
        post = SocialPost.objects.create(
            autore=self.autore,
            titolo="Push",
            testo="senza menzioni",
        )
        SocialPostTag.objects.filter(post=post).delete()
        mock_notify.reset_mock()
        post.testo = f"@{self.cited_a.id}"
        sync_post_tags(post, notify=True)
        mock_notify.assert_called_once()
