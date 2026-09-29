import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0287_prestito_tecniche"),
        ("pilotaggio", "0043_percorso_volo"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventonave",
            name="allarme_richiesto",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Colore che la console comunicazioni deve dichiarare durante la reazione "
                    "per sopprimere il primo controllo di catastrofe. Vuoto = nessun colore."
                ),
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="allarme_annuncio",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Testo vocale dell'ultimo allarme, letto dalla console di pilotaggio.",
            ),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="ca_soppressa_comunicazioni",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Primo controllo CA soppresso perché la radio ha dichiarato "
                    "il colore richiesto durante la reazione."
                ),
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="comunicazioni_login_richiesto",
            field=models.BooleanField(
                default=True,
                help_text="Richiede login alla console comunicazioni.",
            ),
        ),
        migrations.CreateModel(
            name="DipartimentoBordo",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("nome", models.CharField(max_length=80)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attivo", models.BooleanField(db_index=True, default=True)),
                (
                    "membri",
                    models.ManyToManyField(
                        blank=True,
                        related_name="dipartimenti_bordo",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dipartimento di bordo",
                "verbose_name_plural": "Dipartimenti di bordo",
                "ordering": ["ordine", "nome"],
            },
        ),
        migrations.CreateModel(
            name="ProtocolloComunicazione",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("colore", models.CharField(max_length=16, unique=True)),
                (
                    "testo",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Messaggio ai membri. Segnaposto: {sottosistema} {evento}.",
                    ),
                ),
                (
                    "testo_audio",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Frase letta dalla plancia. Vuoto = annuncio standard del colore.",
                    ),
                ),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attivo", models.BooleanField(db_index=True, default=True)),
                (
                    "dipartimento",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="protocolli",
                        to="pilotaggio.dipartimentobordo",
                    ),
                ),
            ],
            options={
                "verbose_name": "Protocollo comunicazione",
                "verbose_name_plural": "Protocolli comunicazione",
                "ordering": ["ordine", "colore"],
            },
        ),
    ]
