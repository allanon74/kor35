# Generated manually

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0181_carriere_unificate"),
    ]

    operations = [
        migrations.CreateModel(
            name="CarrieraTierSblocco",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, verbose_name="Codice Identificativo")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "carriera",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tier_sblocco_links",
                        to="personaggi.carriera",
                    ),
                ),
                (
                    "tier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="carriera_sblocco_links",
                        to="personaggi.tier",
                    ),
                ),
            ],
            options={
                "verbose_name": "Carriera – tier sblocco",
                "verbose_name_plural": "Carriere – tier sblocco",
                "unique_together": {("carriera", "tier")},
            },
        ),
        migrations.AddField(
            model_name="carriera",
            name="tiers_sblocco",
            field=models.ManyToManyField(
                blank=True,
                help_text="Tier di abilità acquistabili dai membri di questa carriera/KORP.",
                related_name="carriere_che_sbloccano",
                through="personaggi.CarrieraTierSblocco",
                to="personaggi.tier",
            ),
        ),
    ]
