"""Citazioni @ InstaFame: parsing e notifiche."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch

from personaggi.models import Campagna, Personaggio
from social.models import SocialProfile, extract_mentioned_personaggi_ids
from social.mention_notifications import format_mention_message, notify_instafame_mentions


class MentionExtractionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="mention_user", password="test")
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True
        )
        cls.cited = Personaggio.objects.create(nome="Vance Premium", proprietario=cls.user, campagna=cls.campagna)
        SocialProfile.objects.create(personaggio=cls.cited, nickname="Vance Premium 🦚")

    def test_extract_by_numeric_id(self):
        ids = extract_mentioned_personaggi_ids(f"Ciao @{self.cited.id}!")
        self.assertIn(self.cited.id, ids)

    def test_extract_by_nickname_with_underscores(self):
        ids = extract_mentioned_personaggi_ids("Hey @Vance_Premium")
        self.assertIn(self.cited.id, ids)


class MentionNotificationTests(TestCase):
    def test_format_message(self):
        msg = format_mention_message("Alice", "Bob", "post")
        self.assertEqual(msg, "Alice ha citato Bob in un post di InstaFame.")

    @patch("personaggi.notify.notify_user")
    def test_push_to_owner(self, mock_notify):
        User = get_user_model()
        owner = User.objects.create_user(username="cited_owner", password="test")
        citer_user = User.objects.create_user(username="citer", password="test")
        campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True
        )
        citer = Personaggio.objects.create(nome="Citante", proprietario=citer_user, campagna=campagna)
        cited = Personaggio.objects.create(nome="Citato", proprietario=owner, campagna=campagna)

        notify_instafame_mentions(citer, [cited.id], "comment")

        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.args[0], owner)
        kwargs = mock_notify.call_args.kwargs
        self.assertEqual(kwargs["category"], "social")
        self.assertIn("Citante ha citato Citato", kwargs["body"])
