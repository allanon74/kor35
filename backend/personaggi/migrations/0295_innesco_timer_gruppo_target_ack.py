# Istanze multiple, destinatari (evento / KORP / personaggi) e ack scadenza.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0054_missioneevento_attiva"),
        ("personaggi", "0294_statistica_parametro_da_sigla"),
    ]

    operations = [
        migrations.AddField(
            model_name="innescotimer",
            name="gruppo_id",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                help_text="Istanze con lo stesso gruppo condividono nome, durata e destinatari.",
                verbose_name="Gruppo istanze",
            ),
        ),
        migrations.AddField(
            model_name="innescotimer",
            name="etichetta_istanza",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Nome staff della singola istanza (es. QR nord). I giocatori vedono il nome del timer.",
                max_length=80,
                verbose_name="Etichetta istanza",
            ),
        ),
        migrations.AddField(
            model_name="innescotimer",
            name="ordine_istanza",
            field=models.PositiveIntegerField(default=1, verbose_name="Ordine istanza"),
        ),
        migrations.AddField(
            model_name="innescotimer",
            name="target_evento",
            field=models.ForeignKey(
                blank=True,
                help_text="Con modalità evento: solo i PG in «partecipanti» di questo evento.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="innesco_timers",
                to="gestione_plot.evento",
                verbose_name="Evento (presenti)",
            ),
        ),
        migrations.AddField(
            model_name="innescotimer",
            name="target_personaggi",
            field=models.ManyToManyField(
                blank=True,
                related_name="innesco_timers_mirati",
                to="personaggi.personaggio",
                verbose_name="Personaggi destinatari",
            ),
        ),
        migrations.AlterField(
            model_name="innescotimer",
            name="modalita_target",
            field=models.CharField(
                choices=[
                    ("globale", "A tutti"),
                    ("evento", "Solo giocatori presenti all'evento"),
                    ("korp", "Solo KORP"),
                    ("personaggi", "Lista di personaggi"),
                    ("filtri", "Filtri era / regione / KORP"),
                ],
                db_index=True,
                default="globale",
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name="InnescoTimerAck",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "data_fine",
                    models.DateTimeField(
                        help_text="broadcast_data_fine dell'istanza al momento della conferma.",
                        verbose_name="Scadenza confermata",
                    ),
                ),
                (
                    "innesco_timer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ack_personaggi",
                        to="personaggi.innescotimer",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ack_innesco_timer",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ack scadenza innesco timer",
                "verbose_name_plural": "Ack scadenze innesco timer",
            },
        ),
        migrations.AddIndex(
            model_name="innescotimerack",
            index=models.Index(fields=["personaggio", "innesco_timer"], name="innesco_ack_pg_it"),
        ),
        migrations.AddConstraint(
            model_name="innescotimerack",
            constraint=models.UniqueConstraint(
                fields=("personaggio", "innesco_timer", "data_fine"),
                name="uq_innesco_timer_ack_pg_fine",
            ),
        ),
    ]
