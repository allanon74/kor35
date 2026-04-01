# Timer runtime unificato

import uuid

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0131_recuperorisorsaattivo_pause_started_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="TimerRuntime",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("end_at", models.DateTimeField(db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Attivo"),
                            ("paused", "In pausa"),
                            ("done", "Completato"),
                            ("cancelled", "Annullato"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=16,
                    ),
                ),
                (
                    "render_slot",
                    models.CharField(db_index=True, default="global_overlay", max_length=64),
                ),
                (
                    "scope_kind",
                    models.CharField(
                        choices=[
                            ("owner_only", "Solo owner"),
                            ("all", "Tutti"),
                            ("event_participants", "Partecipanti evento"),
                            ("guild", "Gilda"),
                            ("region", "Regione"),
                        ],
                        default="all",
                        max_length=32,
                    ),
                ),
                ("scope_payload", models.JSONField(blank=True, default=dict)),
                ("label", models.CharField(blank=True, default="", max_length=200)),
                ("description", models.TextField(blank=True, default="")),
                ("action_key", models.CharField(default="noop", max_length=64)),
                ("action_payload", models.JSONField(blank=True, default=dict)),
                ("is_master_timer", models.BooleanField(db_index=True, default=False)),
                ("source_kind", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("source_id", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("pause_started_at", models.DateTimeField(blank=True, null=True)),
                ("accumulated_pause_seconds", models.PositiveIntegerField(default=0)),
                (
                    "action_executed_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Ultima esecuzione idempotente dell'azione a scadenza.",
                        null=True,
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="timer_runtimes",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Timer runtime",
                "verbose_name_plural": "Timer runtime",
            },
        ),
        migrations.AddIndex(
            model_name="timerruntime",
            index=models.Index(fields=["personaggio", "status", "end_at"], name="personaggi__personag_2b47b4_idx"),
        ),
        migrations.AddIndex(
            model_name="timerruntime",
            index=models.Index(fields=["is_master_timer", "status"], name="personaggi__is_mast_9f8a1c_idx"),
        ),
        migrations.AddIndex(
            model_name="timerruntime",
            index=models.Index(fields=["render_slot", "status"], name="personaggi__render__7e2d9a_idx"),
        ),
        migrations.AddIndex(
            model_name="timerruntime",
            index=models.Index(fields=["status", "end_at"], name="personaggi__status_4c1e2b_idx"),
        ),
        migrations.AddIndex(
            model_name="timerruntime",
            index=models.Index(fields=["source_kind", "source_id"], name="personaggi__source__8a3d1e_idx"),
        ),
        migrations.AddConstraint(
            model_name="timerruntime",
            constraint=models.UniqueConstraint(
                condition=models.Q(source_id__gt="")
                & models.Q(status__in=["active", "paused"]),
                fields=("source_kind", "source_id"),
                name="uniq_timer_runtime_source_active",
            ),
        ),
    ]
