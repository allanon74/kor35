# Generated manually: pattern minigioco + default sezione staff

import django.db.models.deletion
import personaggi.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0258_minigioco_wire_tap_order"),
    ]

    operations = [
        migrations.CreateModel(
            name="MinigiocoPattern",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("nome", models.CharField(max_length=120)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("attivo", models.BooleanField(db_index=True, default=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        default=personaggi.models.get_default_campagna_id,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="minigioco_patterns",
                        to="personaggi.campagna",
                        db_index=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Pattern minigioco",
                "verbose_name_plural": "Pattern minigioco",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="MinigiocoPatternEntry",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("sliding_puzzle", "Sliding puzzle"),
                            ("memory", "Memory"),
                            ("rotate_tiles", "Tessere rotabili"),
                            ("simon", "Sequenza (Simon)"),
                            ("pattern_lock", "Pattern lock"),
                            ("pipe_connect", "Collega i tubi"),
                            ("wire_match", "Collega i fili"),
                            ("tap_order", "Tocca in ordine"),
                        ],
                        max_length=32,
                    ),
                ),
                ("peso", models.PositiveIntegerField(default=1, help_text="Peso relativo nell'estrazione (≥1).")),
                (
                    "difficolta",
                    models.PositiveSmallIntegerField(default=3, help_text="Difficoltà base 1–4 per questa entry."),
                ),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attivo", models.BooleanField(default=True)),
                (
                    "pattern",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="personaggi.minigiocopattern",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entry pattern minigioco",
                "verbose_name_plural": "Entry pattern minigioco",
                "ordering": ["ordine", "id"],
            },
        ),
        migrations.CreateModel(
            name="MinigiocoSezioneDefault",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "page_key",
                    models.CharField(
                        choices=[
                            ("manifesti", "Manifesti"),
                            ("nodi", "Nodi"),
                            ("innesco-timer", "Innesco timer"),
                            ("pilot-sottosistemi", "Pilot sottosistemi"),
                            ("pilot-eventi", "Pilot eventi"),
                        ],
                        db_index=True,
                        max_length=64,
                    ),
                ),
                (
                    "apply_to_new",
                    models.BooleanField(
                        default=False,
                        help_text="Se True, i nuovi QR associati in questa pagina staff ricevono il template.",
                    ),
                ),
                ("sezione_attiva", models.BooleanField(default=False)),
                ("attivo", models.BooleanField(default=False)),
                (
                    "tipi_abilitati",
                    models.JSONField(blank=True, default=personaggi.models._default_tipi_minigioco_qr),
                ),
                ("difficolta", models.PositiveSmallIntegerField(default=4)),
                ("requisiti_attivazione", models.JSONField(blank=True, default=list)),
                ("messaggio_accesso_negato", models.TextField(blank=True, default="")),
                ("esclusioni_minigioco", models.JSONField(blank=True, default=list)),
                ("regole_difficolta", models.JSONField(blank=True, default=list)),
                ("messaggio_pre", models.TextField(blank=True, default="")),
                ("messaggio_vittoria", models.TextField(blank=True, default="")),
                ("timer_secondi", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "timer_scadenza_azione",
                    models.CharField(
                        choices=[
                            ("attiva_qr", "Attiva il QR"),
                            ("blocca_qr", "Blocca il QR (non riattivabile)"),
                            ("reset_minigioco", "Reset minigioco"),
                        ],
                        default="reset_minigioco",
                        max_length=32,
                    ),
                ),
                ("usa_biblioteca_se_vuota", models.BooleanField(default=True)),
                (
                    "modalita_sblocco",
                    models.CharField(
                        choices=[
                            ("ogni_scansione", "Minigioco a ogni scansione"),
                            ("permanente", "Una volta risolto, per sempre"),
                            ("temporaneo", "Sblocco temporaneo (N secondi)"),
                        ],
                        default="permanente",
                        max_length=24,
                    ),
                ),
                ("sblocco_secondi", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        default=personaggi.models.get_default_campagna_id,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="minigioco_sezione_defaults",
                        to="personaggi.campagna",
                        db_index=True,
                    ),
                ),
                (
                    "pattern",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sezione_defaults",
                        to="personaggi.minigiocopattern",
                    ),
                ),
            ],
            options={
                "verbose_name": "Default sezione minigioco",
                "verbose_name_plural": "Default sezione minigioco",
            },
        ),
        migrations.AddConstraint(
            model_name="minigiocosezionedefault",
            constraint=models.UniqueConstraint(
                fields=("page_key", "campagna"),
                name="uniq_minigioco_sezione_default_page_campagna",
            ),
        ),
        migrations.AddField(
            model_name="minigiocoqrconfig",
            name="pattern",
            field=models.ForeignKey(
                blank=True,
                help_text="Se valorizzato, tipo/difficoltà vengono estratti dalle entry del pattern (non da tipi_abilitati).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="qr_configs",
                to="personaggi.minigiocopattern",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpool",
            name="minigioco_pattern",
            field=models.ForeignKey(
                blank=True,
                help_text="Pattern estrazione minigioco a monte del pool (override per-QR via MinigiocoQrConfig).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="random_qr_pools",
                to="personaggi.minigiocopattern",
            ),
        ),
    ]
