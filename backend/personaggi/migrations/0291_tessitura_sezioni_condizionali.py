import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0290_prestigio_punteggio_personaggio"),
    ]

    operations = [
        migrations.CreateModel(
            name="TessituraSezioneCondizionale",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("ordine", models.PositiveIntegerField(default=0)),
                (
                    "modalita",
                    models.CharField(
                        choices=[
                            ("auto", "Automatica (requisiti del personaggio)"),
                            ("manuale", "Facoltativa (il giocatore la attiva)"),
                        ],
                        db_index=True,
                        default="auto",
                        max_length=12,
                    ),
                ),
                (
                    "etichetta",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Nome della condizione facoltativa (es. Canto, Ballo). Usato anche come flag in {if canto}.",
                        max_length=80,
                    ),
                ),
                ("testo", models.TextField("Testo addizionale", blank=True, default="")),
                (
                    "condizioni",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Gruppo requisiti AND/OR: {"operator":"AND"|"OR","requisiti":[...]}.',
                    ),
                ),
                (
                    "sostituisci_bersaglio",
                    models.BooleanField(
                        default=False,
                        help_text="Se attivo, le stats bersaglio di questa sezione (esplos, tocco, …) sostituiscono quelle della formula base.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tessitura",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sezioni_condizionali",
                        to="personaggi.tessitura",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sezione condizionale tessitura",
                "verbose_name_plural": "Sezioni condizionali tessitura",
                "ordering": ["ordine", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="TessituraSezioneStatisticaBase",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("valore_base", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sezione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="statistiche_base",
                        to="personaggi.tessiturasezionecondizionale",
                    ),
                ),
                (
                    "statistica",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="personaggi.statistica",
                    ),
                ),
            ],
            options={
                "verbose_name": "Statistica base sezione tessitura",
                "verbose_name_plural": "Statistiche base sezioni tessitura",
                "unique_together": {("sezione", "statistica")},
            },
        ),
    ]
