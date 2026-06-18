from datetime import timedelta

from django.db import migrations
from django.utils import timezone


STORY_TTL_HOURS = 24


def backfill_story_expires_at(apps, schema_editor):
    SocialStory = apps.get_model("social", "SocialStory")
    ttl = timedelta(hours=STORY_TTL_HOURS)
    for story in SocialStory.objects.filter(expires_at__isnull=True).iterator():
        base = story.created_at or timezone.now()
        story.expires_at = base + ttl
        story.save(update_fields=["expires_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0009_socialpostimage"),
    ]

    operations = [
        migrations.RunPython(backfill_story_expires_at, migrations.RunPython.noop),
    ]
