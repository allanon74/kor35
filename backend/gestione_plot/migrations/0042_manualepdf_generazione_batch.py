import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0041_manualepdf_stile"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManualePdfBatchJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "In attesa"),
                        ("running", "In esecuzione"),
                        ("completed", "Completato"),
                        ("partial", "Completato con errori"),
                        ("failed", "Fallito"),
                    ],
                    db_index=True,
                    default="pending",
                    max_length=20,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("triggered_by_email", models.CharField(blank=True, max_length=254)),
                ("results", models.JSONField(blank=True, default=list)),
                ("error_message", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Job batch manuali PDF",
                "verbose_name_plural": "Job batch manuali PDF",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ManualePdfGenerazione",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("generato_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("success", models.BooleanField(default=False)),
                ("error_message", models.TextField(blank=True)),
                ("pagine_count", models.PositiveIntegerField(default=0)),
                ("capitoli_count", models.PositiveIntegerField(default=0)),
                ("file_size_bytes", models.PositiveBigIntegerField(default=0)),
                ("file_path", models.CharField(blank=True, max_length=500)),
                ("stile_preset", models.CharField(blank=True, max_length=40)),
                ("stile_snapshot", models.JSONField(blank=True, default=dict)),
                ("triggered_by_email", models.CharField(blank=True, max_length=254)),
                ("durata_ms", models.PositiveIntegerField(default=0)),
                ("manuale", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="generazioni",
                    to="gestione_plot.manualepdf",
                )),
            ],
            options={
                "verbose_name": "Generazione manuale PDF",
                "verbose_name_plural": "Generazioni manuali PDF",
                "ordering": ["-generato_at"],
            },
        ),
    ]
