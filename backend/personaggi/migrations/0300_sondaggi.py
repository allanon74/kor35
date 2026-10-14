import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("personaggi", "0299_pool_effect_inventario"),
    ]

    operations = [
        migrations.CreateModel(
            name="Sondaggio",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("titolo", models.CharField(max_length=200)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("google_form_url", models.URLField(max_length=500)),
                ("google_form_id", models.CharField(db_index=True, max_length=128)),
                ("domande", models.JSONField(blank=True, default=list)),
                ("avvisi", models.JSONField(blank=True, default=list)),
                (
                    "attivo",
                    models.BooleanField(
                        default=False,
                        help_text="Se attivo, i giocatori della campagna vedono il sondaggio nell'app.",
                    ),
                ),
                (
                    "consenti_modifica",
                    models.BooleanField(
                        default=False,
                        help_text="Se attivo, il giocatore può aggiornare la propria risposta.",
                    ),
                ),
                (
                    "inoltra_email",
                    models.BooleanField(
                        default=True,
                        help_text="Se il modulo Google raccoglie l'email, invia quella dell'account.",
                    ),
                ),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sondaggi",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sondaggio",
                "verbose_name_plural": "Sondaggi",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RispostaSondaggio",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("risposte", models.JSONField(blank=True, default=dict)),
                ("google_inviato_at", models.DateTimeField(blank=True, null=True)),
                ("google_claim_at", models.DateTimeField(blank=True, null=True)),
                ("google_errore", models.CharField(blank=True, default="", max_length=500)),
                (
                    "personaggio",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="risposte_sondaggio",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "sondaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="risposte",
                        to="personaggi.sondaggio",
                    ),
                ),
                (
                    "utente",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="risposte_sondaggio",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Risposta sondaggio",
                "verbose_name_plural": "Risposte sondaggio",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="sondaggio",
            constraint=models.UniqueConstraint(
                fields=("campagna", "google_form_id"),
                name="sondaggio_campagna_form_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="rispostasondaggio",
            constraint=models.UniqueConstraint(
                fields=("sondaggio", "personaggio"),
                name="risposta_sondaggio_pg_uniq",
            ),
        ),
    ]
