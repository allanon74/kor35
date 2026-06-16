from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0192_peso_influencer"),
        ("social", "0007_socialprofile_nickname"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialpost",
            name="likes_base",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Like iniziali simulati (statici) alla creazione del post.",
            ),
        ),
        migrations.AddField(
            model_name="socialcomment",
            name="likes_base",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Like iniziali simulati (statici) alla creazione del commento.",
            ),
        ),
        migrations.AddField(
            model_name="sociallike",
            name="peso_like",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Peso statico del like (simulazione popolazione).",
            ),
        ),
        migrations.CreateModel(
            name="SocialCommentLike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                (
                    "peso_like",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Peso statico del like al commento.",
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "autore",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_comment_likes",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "comment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="likes",
                        to="social.socialcomment",
                    ),
                ),
            ],
            options={
                "verbose_name": "Like Commento Social",
                "verbose_name_plural": "Like Commenti Social",
                "ordering": ["-created_at", "-id"],
                "unique_together": {("comment", "autore")},
            },
        ),
    ]
