# Generated manually for auto recupero risorse pool

import uuid

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0120_risorse_statistiche_pool"),
    ]

    operations = [
        migrations.AddField(
            model_name="statistica",
            name="auto_recupero_attivo",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo su una risorsa pool, avvia il recupero periodico quando il valore scende sotto il massimo.",
                verbose_name="Recupero automatico attivo",
            ),
        ),
        migrations.AddField(
            model_name="statistica",
            name="auto_recupero_intervallo_secondi",
            field=models.PositiveIntegerField(
                default=300,
                help_text="Ogni quanti secondi viene recuperato lo step configurato.",
                verbose_name="Intervallo recupero (sec)",
            ),
        ),
        migrations.AddField(
            model_name="statistica",
            name="auto_recupero_step",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Quanti punti recuperare ad ogni tick.",
                verbose_name="Step recupero",
            ),
        ),
        migrations.CreateModel(
            name="RecuperoRisorsaAttivo",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("statistica_sigla", models.CharField(db_index=True, max_length=3)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("next_tick_at", models.DateTimeField(db_index=True)),
                ("interval_seconds", models.PositiveIntegerField(default=300)),
                ("step", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recuperi_risorsa_attivi",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Recupero risorsa attivo",
                "verbose_name_plural": "Recuperi risorsa attivi",
                "unique_together": {("personaggio", "statistica_sigla")},
            },
        ),
    ]
