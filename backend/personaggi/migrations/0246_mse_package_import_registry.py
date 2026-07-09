import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0245_mse_style_assets_manifest"),
    ]

    operations = [
        migrations.CreateModel(
            name="CarteMsePackageImport",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "package_type",
                    models.CharField(
                        choices=[
                            ("mse-style", "MSE Style"),
                            ("mse-game", "MSE Game"),
                            ("mse-set", "MSE Set"),
                            ("mse-symbol-font", "MSE Symbol Font"),
                            ("mse-export-template", "MSE Export Template"),
                            ("mse-include", "MSE Include"),
                            ("mse-locale", "MSE Locale"),
                        ],
                        db_index=True,
                        max_length=24,
                    ),
                ),
                ("package_name", models.CharField(db_index=True, max_length=160)),
                ("source_priority", models.PositiveSmallIntegerField(db_index=True, default=999)),
                ("source_root", models.CharField(blank=True, default="", max_length=255)),
                ("source_path", models.CharField(blank=True, default="", max_length=255)),
                ("extracted_root", models.CharField(blank=True, default="", max_length=255)),
                ("parsed_meta", models.JSONField(blank=True, default=dict)),
                ("assets_manifest", models.JSONField(blank=True, default=list)),
                ("imported", models.BooleanField(db_index=True, default=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="carte_mse_packages",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "gioco_definizione",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mse_packages",
                        to="personaggi.cartegiocodefinizione",
                    ),
                ),
            ],
            options={
                "verbose_name": "Package MSE importato",
                "verbose_name_plural": "Package MSE importati",
                "ordering": ["package_type", "package_name"],
                "unique_together": {("campagna", "package_type", "package_name")},
            },
        ),
    ]

