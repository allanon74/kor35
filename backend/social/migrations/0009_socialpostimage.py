import uuid

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import social.models


def migrate_legacy_post_images(apps, schema_editor):
    SocialPost = apps.get_model("social", "SocialPost")
    SocialPostImage = apps.get_model("social", "SocialPostImage")
    for post in SocialPost.objects.exclude(immagine="").exclude(immagine__isnull=True):
        if SocialPostImage.objects.filter(post_id=post.id).exists():
            continue
        SocialPostImage.objects.create(
            post_id=post.id,
            immagine=post.immagine,
            ordine=0,
            created_at=post.created_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("social", "0008_influencer_likes"),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialPostImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("immagine", models.ImageField(upload_to=social.models.social_post_image_upload_to)),
                ("ordine", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="post_images",
                        to="social.socialpost",
                    ),
                ),
            ],
            options={
                "verbose_name": "Immagine post social",
                "verbose_name_plural": "Immagini post social",
                "ordering": ["ordine", "id"],
                "unique_together": {("post", "ordine")},
            },
        ),
        migrations.RunPython(migrate_legacy_post_images, migrations.RunPython.noop),
    ]
