from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0115_messaggio_allegati_snapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSocialPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "preferred_personaggio",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="preferred_by_users",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_preference",
                        to="auth.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Preferenza Social Utente",
                "verbose_name_plural": "Preferenze Social Utenti",
            },
        ),
    ]

