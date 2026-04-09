import uuid
from django.db import migrations, models
import django.db.models.deletion


def populate_public_slug(apps, schema_editor):
    SocialPost = apps.get_model("social", "SocialPost")
    for post in SocialPost.objects.filter(public_slug__isnull=True):
        post.public_slug = uuid.uuid4().hex[:16]
        post.save(update_fields=["public_slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialpost",
            name="public_slug",
            field=models.SlugField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.RunPython(populate_public_slug, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="socialpost",
            name="public_slug",
            field=models.SlugField(blank=True, max_length=64, unique=True),
        ),
        migrations.CreateModel(
            name="SocialCommentTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("comment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tags", to="social.socialcomment")),
                ("personaggio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tagged_in_social_comments", to="personaggi.personaggio")),
            ],
            options={
                "verbose_name": "Tag Commento Social",
                "verbose_name_plural": "Tag Commento Social",
                "unique_together": {("comment", "personaggio")},
            },
        ),
        migrations.CreateModel(
            name="SocialPostTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("personaggio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tagged_in_social_posts", to="personaggi.personaggio")),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tags", to="social.socialpost")),
            ],
            options={
                "verbose_name": "Tag Post Social",
                "verbose_name_plural": "Tag Post Social",
                "unique_together": {("post", "personaggio")},
            },
        ),
    ]
