# Generated manually for CarrieraAbilita default perks

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0217_personaggio_foto_costume"),
    ]

    operations = [
        migrations.CreateModel(
            name="CarrieraAbilita",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "sync_id",
                    models.UUIDField(blank=True, default=uuid.uuid4, editable=False, null=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                (
                    "is_default",
                    models.BooleanField(
                        default=True,
                        help_text="Se attivo, l'abilità viene aggiunta ai personaggi con membership attiva su questa carriera/KORP.",
                        verbose_name="Assegna in automatico ai membri",
                    ),
                ),
                ("ordine", models.PositiveIntegerField(default=0)),
                (
                    "abilita",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="abilita_carriera",
                        to="personaggi.abilita",
                    ),
                ),
                (
                    "carriera",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="carriere_abilita",
                        to="personaggi.carriera",
                    ),
                ),
            ],
            options={
                "verbose_name": "Abilità Carriera",
                "verbose_name_plural": "Abilità Carriere",
                "ordering": ["ordine", "abilita__nome"],
                "unique_together": {("carriera", "abilita")},
            },
        ),
        migrations.AddField(
            model_name="carriera",
            name="abilita",
            field=models.ManyToManyField(
                blank=True,
                related_name="carriere_collegate",
                through="personaggi.CarrieraAbilita",
                to="personaggi.abilita",
            ),
        ),
        migrations.AlterField(
            model_name="personaggioabilita",
            name="origine",
            field=models.CharField(
                choices=[
                    ("acquisto", "Acquisto"),
                    ("era_default", "Era (default)"),
                    ("regione_default", "Regione (default)"),
                    ("carriera_default", "Carriera/KORP (default)"),
                ],
                default="acquisto",
                max_length=20,
            ),
        ),
    ]
