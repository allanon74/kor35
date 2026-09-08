import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0267_pool_effect_da_infusione"),
    ]

    operations = [
        migrations.CreateModel(
            name="InfusioneSezioneCondizionale",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("testo", models.TextField("Testo addizionale", blank=True, default="")),
                (
                    "condizioni",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Gruppo requisiti AND/OR: {"operator":"AND"|"OR","requisiti":[...]}.',
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "infusione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sezioni_condizionali",
                        to="personaggi.infusione",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sezione condizionale infusione",
                "verbose_name_plural": "Sezioni condizionali infusione",
                "ordering": ["ordine", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="InfusioneSezioneStatisticaBase",
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
                        to="personaggi.infusionesezionecondizionale",
                    ),
                ),
                (
                    "statistica",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="personaggi.statistica"),
                ),
            ],
            options={
                "verbose_name": "Statistica base sezione infusione",
                "verbose_name_plural": "Statistiche base sezioni infusione",
                "unique_together": {("sezione", "statistica")},
            },
        ),
        migrations.CreateModel(
            name="InfusioneSezioneStatistica",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                (
                    "valore",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Valore additivo (+N) o moltiplicativo (xN, es. 0.5 per -50%).",
                        max_digits=7,
                    ),
                ),
                (
                    "tipo_modificatore",
                    models.CharField(
                        choices=[("ADD", "Additivo (+N)"), ("MOL", "Moltiplicativo (xN)")],
                        default="ADD",
                        max_length=3,
                    ),
                ),
                (
                    "solo_oggetto_ospitante",
                    models.BooleanField(
                        default=False,
                        help_text="Se attivo, il modificatore vale solo per le formule dell'oggetto, non per il personaggio.",
                        verbose_name="Solo oggetto ospitante",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sezione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="modificatori",
                        to="personaggi.infusionesezionecondizionale",
                    ),
                ),
                (
                    "statistica",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="personaggi.statistica"),
                ),
            ],
            options={
                "verbose_name": "Modificatore sezione infusione",
                "verbose_name_plural": "Modificatori sezioni infusione",
                "unique_together": {("sezione", "statistica")},
            },
        ),
        migrations.CreateModel(
            name="OggettoSezioneCondizionale",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("testo", models.TextField("Testo addizionale", blank=True, default="")),
                (
                    "condizioni",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Gruppo requisiti AND/OR: {"operator":"AND"|"OR","requisiti":[...]}.',
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "oggetto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sezioni_condizionali",
                        to="personaggi.oggetto",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sezione condizionale oggetto",
                "verbose_name_plural": "Sezioni condizionali oggetto",
                "ordering": ["ordine", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="OggettoSezioneStatisticaBase",
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
                        to="personaggi.oggettosezionecondizionale",
                    ),
                ),
                (
                    "statistica",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="personaggi.statistica"),
                ),
            ],
            options={
                "verbose_name": "Statistica base sezione oggetto",
                "verbose_name_plural": "Statistiche base sezioni oggetto",
                "unique_together": {("sezione", "statistica")},
            },
        ),
        migrations.CreateModel(
            name="OggettoSezioneStatistica",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                (
                    "valore",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Valore additivo (+N) o moltiplicativo (xN, es. 0.5 per -50%).",
                        max_digits=7,
                    ),
                ),
                (
                    "tipo_modificatore",
                    models.CharField(
                        choices=[("ADD", "Additivo (+N)"), ("MOL", "Moltiplicativo (xN)")],
                        default="ADD",
                        max_length=3,
                    ),
                ),
                (
                    "solo_oggetto_ospitante",
                    models.BooleanField(
                        default=False,
                        help_text="Se attivo, il modificatore vale solo per le formule dell'oggetto, non per il personaggio.",
                        verbose_name="Solo oggetto ospitante",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sezione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="modificatori",
                        to="personaggi.oggettosezionecondizionale",
                    ),
                ),
                (
                    "statistica",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="personaggi.statistica"),
                ),
            ],
            options={
                "verbose_name": "Modificatore sezione oggetto",
                "verbose_name_plural": "Modificatori sezioni oggetto",
                "unique_together": {("sezione", "statistica")},
            },
        ),
    ]
