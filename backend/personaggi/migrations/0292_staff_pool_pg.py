import uuid
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import personaggi.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gestione_plot", "0054_missioneevento_attiva"),
        ("personaggi", "0291_tessitura_sezioni_condizionali"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessaggioModelloStaff",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("nome", models.CharField(max_length=120)),
                ("titolo", models.CharField(blank=True, default="", max_length=150)),
                ("testo", models.TextField(blank=True, default="")),
                (
                    "campagna",
                    models.ForeignKey(
                        default=personaggi.models.get_default_campagna_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="modelli_messaggio_staff",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "creato_da",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="modelli_messaggio_staff",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Modello messaggio staff",
                "verbose_name_plural": "Modelli messaggio staff",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="PersonaggioPool",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("nome", models.CharField(max_length=120)),
                (
                    "escludi_png",
                    models.BooleanField(
                        default=False,
                        help_text="Se attivo, l'elenco di selezione nasconde i personaggi non giocanti.",
                    ),
                ),
                (
                    "sorteggio_min",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Numero minimo di personaggi da estrarre (estremo incluso).",
                    ),
                ),
                (
                    "sorteggio_max",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Numero massimo di personaggi da estrarre. Se uguale al minimo, estrazione fissa.",
                    ),
                ),
                (
                    "fattore_peso",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0.8000"),
                        help_text=(
                            "Peso = fattore ^ sorteggi_pregressi. Default 0.8 (meno chance se già estratti). "
                            "1 = probabilità costante. >1 = più chance dopo ogni estrazione."
                        ),
                        max_digits=8,
                    ),
                ),
                ("messaggio_titolo", models.CharField(blank=True, default="", max_length=150)),
                (
                    "messaggio_testo",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Rich text con placeholder {{nome_personaggio}}, {{nome_giocatore}}, {{nome_evento}}, …",
                    ),
                ),
                (
                    "invio_prioritario",
                    models.BooleanField(
                        default=False,
                        help_text="Oltre all'inbox, overlay a schermo intero fino a «Ho letto e compreso» + allarme.",
                    ),
                ),
                (
                    "campagna",
                    models.ForeignKey(
                        default=personaggi.models.get_default_campagna_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pool_personaggi",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Pool personaggi (sorteggio)",
                "verbose_name_plural": "Pool personaggi (sorteggio)",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="PersonaggioPoolMembro",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attivo", models.BooleanField(default=True)),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pool_sorteggio_membri",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "pool",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="membri",
                        to="personaggi.personaggiopool",
                    ),
                ),
            ],
            options={
                "verbose_name": "Membro pool personaggi",
                "verbose_name_plural": "Membri pool personaggi",
            },
        ),
        migrations.CreateModel(
            name="PersonaggioPoolSorteggio",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("n_min", models.PositiveIntegerField(default=1)),
                ("n_max", models.PositiveIntegerField(default=1)),
                ("n_estratti", models.PositiveIntegerField(default=0)),
                (
                    "fattore_usato",
                    models.DecimalField(decimal_places=4, default=Decimal("0.8000"), max_digits=8),
                ),
                ("prioritario", models.BooleanField(default=False)),
                ("messaggio_titolo_snapshot", models.CharField(blank=True, default="", max_length=150)),
                ("messaggio_testo_snapshot", models.TextField(blank=True, default="")),
                (
                    "campagna",
                    models.ForeignKey(
                        default=personaggi.models.get_default_campagna_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sorteggi_pool_personaggi",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "creato_da",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sorteggi_pool_personaggi",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "evento",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sorteggi_pool_personaggi",
                        to="gestione_plot.evento",
                    ),
                ),
                (
                    "pool",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sorteggi",
                        to="personaggi.personaggiopool",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sorteggio pool personaggi",
                "verbose_name_plural": "Sorteggi pool personaggi",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PersonaggioPoolSorteggioEsito",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("peso", models.DecimalField(decimal_places=6, default=Decimal("1"), max_digits=14)),
                ("sorteggi_pregressi", models.PositiveIntegerField(default=0)),
                ("ack_richiesto", models.BooleanField(default=False)),
                ("confermato_at", models.DateTimeField(blank=True, null=True)),
                ("confermato_user_agent", models.CharField(blank=True, default="", max_length=256)),
                ("confermato_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("confermato_dispositivo", models.JSONField(blank=True, default=dict)),
                (
                    "messaggio",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="esiti_sorteggio_pool",
                        to="personaggi.messaggio",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sorteggi_pool_esiti",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "pool",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="esiti",
                        to="personaggi.personaggiopool",
                    ),
                ),
                (
                    "sorteggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="esiti",
                        to="personaggi.personaggiopoolsorteggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Esito sorteggio pool",
                "verbose_name_plural": "Esiti sorteggio pool",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="personaggiopoolmembro",
            constraint=models.UniqueConstraint(fields=("pool", "personaggio"), name="uniq_pool_pg_membro"),
        ),
        migrations.AddIndex(
            model_name="personaggiopoolsorteggioesito",
            index=models.Index(fields=["pool", "personaggio"], name="poolpg_esito_pg_idx"),
        ),
        migrations.AddIndex(
            model_name="personaggiopoolsorteggioesito",
            index=models.Index(
                fields=["ack_richiesto", "confermato_at"],
                name="poolpg_ack_conf_idx",
            ),
        ),
    ]
