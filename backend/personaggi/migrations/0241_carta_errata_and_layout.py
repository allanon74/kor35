import uuid

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0240_carte_governance_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartacollezionabile",
            name="layout_versione",
            field=models.CharField(
                choices=[("STD", "Standard"), ("FULL", "Full-size borderless")],
                default="STD",
                help_text="Layout visuale carta (standard/full-size).",
                max_length=4,
            ),
        ),
        migrations.CreateModel(
            name="CartaErrata",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("effective_from", models.DateTimeField(db_index=True)),
                ("attiva", models.BooleanField(db_index=True, default=True)),
                ("titolo", models.CharField(blank=True, default="", max_length=120)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("testo_gioco_override", models.TextField(blank=True, default="")),
                ("costo_gioco_override", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("attacco_override", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("salute_override", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "iniziativa_override",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        validators=[django.core.validators.MaxValueValidator(5)],
                    ),
                ),
                ("effect_scripts_override", models.JSONField(blank=True, default=list)),
                (
                    "campagna",
                    models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="carte_errata", to="personaggi.campagna"),
                ),
                (
                    "carta",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="errata", to="personaggi.cartacollezionabile"),
                ),
            ],
            options={
                "verbose_name": "Errata carta",
                "verbose_name_plural": "Errata carte",
                "ordering": ["-effective_from", "-updated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="cartaerrata",
            index=models.Index(fields=["campagna", "effective_from", "attiva"], name="personaggi_campagn_6eebf1_idx"),
        ),
    ]
