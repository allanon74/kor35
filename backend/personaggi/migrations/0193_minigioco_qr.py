import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0192_peso_influencer"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MinigiocoQrConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sync_id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("attivo", models.BooleanField(default=False)),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("sliding_puzzle", "Sliding puzzle"),
                            ("memory", "Memory"),
                            ("rotate_tiles", "Tessere rotabili"),
                        ],
                        default="sliding_puzzle",
                        max_length=32,
                    ),
                ),
                (
                    "difficolta",
                    models.PositiveSmallIntegerField(
                        default=2,
                        help_text="1=facile … 4=difficile (dimensione griglia dipende dal tipo).",
                    ),
                ),
                (
                    "immagine",
                    models.ImageField(
                        blank=True,
                        help_text="Immagine quadrata per puzzle/memory/rotate.",
                        null=True,
                        upload_to="minigioco_qr/%Y/%m/",
                    ),
                ),
                (
                    "requisiti_attivazione",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Se vuoto, minigioco sempre attivo (se attivo=True). Altrimenti JSON requisiti come manifesti.",
                    ),
                ),
                ("messaggio_pre", models.TextField(blank=True, default="")),
                ("messaggio_vittoria", models.TextField(blank=True, default="")),
                (
                    "timer_secondi",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Timer opzionale in secondi. Vuoto = nessun timer.",
                        null=True,
                    ),
                ),
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
                (
                    "qr_code",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="configurazione_minigioco",
                        to="personaggi.qrcode",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configurazione minigioco QR",
                "verbose_name_plural": "Configurazioni minigioco QR",
            },
        ),
        migrations.CreateModel(
            name="MinigiocoQrBlocco",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("bloccato_at", models.DateTimeField(auto_now_add=True)),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="minigioco_qr_blocchi",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "qr_code",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="minigioco_blocchi",
                        to="personaggi.qrcode",
                    ),
                ),
            ],
            options={
                "verbose_name": "Blocco minigioco QR",
                "verbose_name_plural": "Blocchi minigioco QR",
            },
        ),
        migrations.CreateModel(
            name="MinigiocoQrSession",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tipo", models.CharField(max_length=32)),
                ("difficolta", models.PositiveSmallIntegerField(default=2)),
                ("seed", models.PositiveIntegerField(default=0)),
                ("stato_gioco", models.JSONField(blank=True, default=dict)),
                ("immagine_url", models.CharField(blank=True, default="", max_length=500)),
                ("scadenza_at", models.DateTimeField(blank=True, null=True)),
                (
                    "stato",
                    models.CharField(
                        choices=[
                            ("in_corso", "In corso"),
                            ("completato", "Completato"),
                            ("scaduto_attiva", "Scaduto — QR attivato"),
                            ("scaduto_blocca", "Scaduto — QR bloccato"),
                            ("scaduto_reset", "Scaduto — reset"),
                        ],
                        default="in_corso",
                        max_length=32,
                    ),
                ),
                ("completato_at", models.DateTimeField(blank=True, null=True)),
                ("avviato_at", models.DateTimeField(auto_now_add=True)),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="minigioco_qr_sessions",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "qr_code",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="minigioco_sessions",
                        to="personaggi.qrcode",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="minigioco_qr_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Sessione minigioco QR",
                "verbose_name_plural": "Sessioni minigioco QR",
            },
        ),
        migrations.AddConstraint(
            model_name="minigiocoqrblocco",
            constraint=models.UniqueConstraint(
                fields=("personaggio", "qr_code"),
                name="personaggi_minigiocoqrblocco_pg_qr_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="minigiocoqrsession",
            index=models.Index(
                fields=["personaggio", "qr_code", "stato"],
                name="personaggi_m_persona_6a8f2d_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="minigiocoqrsession",
            index=models.Index(
                fields=["qr_code", "stato"],
                name="personaggi_m_qr_code_7b1c4e_idx",
            ),
        ),
    ]
