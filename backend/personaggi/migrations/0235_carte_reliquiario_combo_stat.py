import uuid

import django.db.models.deletion
from django.db import migrations, models

import kor35.syncing


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0234_mazzo_leader"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartacollezionabile",
            name="testo_reliquiario",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Testo mostrato sullo slot reliquiario quando equipaggiata (sostituisce il testo gioco).",
            ),
        ),
        migrations.CreateModel(
            name="ComboReliquiario",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("codice", models.CharField(db_index=True, max_length=60)),
                ("nome", models.CharField(max_length=120)),
                (
                    "testo",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Testo mostrato nella sezione combo attive sotto il reliquiario.",
                    ),
                ),
                (
                    "colore",
                    models.CharField(
                        default="#10b981",
                        help_text="Colore bordo/testo combo (es. #10b981).",
                        max_length=7,
                    ),
                ),
                (
                    "tipo_trigger",
                    models.CharField(
                        choices=[
                            ("LEGAME", "Stesso legame_id"),
                            ("SET", "Stesso set_collezione"),
                            ("CARTE", "Carte specifiche (codici)"),
                            ("ENERGIE_NAT", "Energie naturali distinte"),
                            ("ENERGIE_SOP", "Energie soprannaturali distinte"),
                        ],
                        db_index=True,
                        max_length=12,
                    ),
                ),
                ("param_legame_id", models.CharField(blank=True, default="", max_length=80)),
                ("param_set_collezione", models.CharField(blank=True, default="", max_length=80)),
                (
                    "param_carte_codici",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='Lista codici carta richiesti, es. ["ST-KAEL-001","ST-KAEL-002"].',
                    ),
                ),
                (
                    "param_min_count",
                    models.PositiveSmallIntegerField(
                        default=2,
                        help_text="Soglia minima (conteggio legame/set/energie). Ignorata per trigger CARTE.",
                    ),
                ),
                ("ordine", models.PositiveSmallIntegerField(default=0)),
                ("attiva", models.BooleanField(db_index=True, default=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="combo_reliquiario",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Combo reliquiario",
                "verbose_name_plural": "Combo reliquiario",
                "ordering": ["ordine", "nome"],
                "unique_together": {("campagna", "codice")},
            },
            bases=(kor35.syncing.SyncableModel, models.Model),
        ),
        migrations.CreateModel(
            name="CartaReliquiarioStatistica",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("usa_limitazione_aura", models.BooleanField(default=False, verbose_name="Usa Limitazione Aura")),
                ("usa_limitazione_elemento", models.BooleanField(default=False, verbose_name="Usa Limitazione Elemento")),
                ("usa_condizione_text", models.BooleanField(default=False, verbose_name="Usa Condizione Testuale")),
                (
                    "condizione_text",
                    models.CharField(
                        blank=True,
                        help_text="Es. caratt>6",
                        max_length=255,
                        null=True,
                        verbose_name="Condizione",
                    ),
                ),
                (
                    "solo_oggetto_ospitante",
                    models.BooleanField(
                        default=False,
                        help_text="Se attivo, il modificatore vale solo per le formule dell'oggetto su cui è montato (o dell'oggetto stesso), non per le statistiche generali del personaggio.",
                        verbose_name="Solo oggetto ospitante",
                    ),
                ),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("valore", models.FloatField(default=0)),
                (
                    "tipo_modificatore",
                    models.CharField(
                        choices=[("ADD", "Additivo (+N)"), ("MOL", "Moltiplicativo (xN)")],
                        default="ADD",
                        max_length=3,
                    ),
                ),
                (
                    "carta",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reliquiario_statistiche",
                        to="personaggi.cartacollezionabile",
                    ),
                ),
                (
                    "limit_a_aure",
                    models.ManyToManyField(
                        blank=True,
                        limit_choices_to={"tipo": "AU"},
                        related_name="cartareliquiariostatistica_limit_aure",
                        to="personaggi.punteggio",
                        verbose_name="Aure consentite",
                    ),
                ),
                (
                    "limit_a_elementi",
                    models.ManyToManyField(
                        blank=True,
                        limit_choices_to={"tipo": "EL"},
                        related_name="cartareliquiariostatistica_limit_elementi",
                        to="personaggi.punteggio",
                        verbose_name="Elementi consentiti",
                    ),
                ),
                (
                    "statistica",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="personaggi.statistica"),
                ),
            ],
            options={
                "verbose_name": "Statistica reliquiario carta",
                "verbose_name_plural": "Statistiche reliquiario carta",
                "unique_together": {("carta", "statistica")},
            },
            bases=(kor35.syncing.SyncableModel, models.Model),
        ),
        migrations.CreateModel(
            name="ComboReliquiarioStatistica",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("usa_limitazione_aura", models.BooleanField(default=False, verbose_name="Usa Limitazione Aura")),
                ("usa_limitazione_elemento", models.BooleanField(default=False, verbose_name="Usa Limitazione Elemento")),
                ("usa_condizione_text", models.BooleanField(default=False, verbose_name="Usa Condizione Testuale")),
                (
                    "condizione_text",
                    models.CharField(
                        blank=True,
                        help_text="Es. caratt>6",
                        max_length=255,
                        null=True,
                        verbose_name="Condizione",
                    ),
                ),
                (
                    "solo_oggetto_ospitante",
                    models.BooleanField(
                        default=False,
                        help_text="Se attivo, il modificatore vale solo per le formule dell'oggetto su cui è montato (o dell'oggetto stesso), non per le statistiche generali del personaggio.",
                        verbose_name="Solo oggetto ospitante",
                    ),
                ),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("valore", models.FloatField(default=0)),
                (
                    "tipo_modificatore",
                    models.CharField(
                        choices=[("ADD", "Additivo (+N)"), ("MOL", "Moltiplicativo (xN)")],
                        default="ADD",
                        max_length=3,
                    ),
                ),
                (
                    "combo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="statistiche",
                        to="personaggi.comboreliquiario",
                    ),
                ),
                (
                    "limit_a_aure",
                    models.ManyToManyField(
                        blank=True,
                        limit_choices_to={"tipo": "AU"},
                        related_name="comboreliquiariostatistica_limit_aure",
                        to="personaggi.punteggio",
                        verbose_name="Aure consentite",
                    ),
                ),
                (
                    "limit_a_elementi",
                    models.ManyToManyField(
                        blank=True,
                        limit_choices_to={"tipo": "EL"},
                        related_name="comboreliquiariostatistica_limit_elementi",
                        to="personaggi.punteggio",
                        verbose_name="Elementi consentiti",
                    ),
                ),
                (
                    "statistica",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="personaggi.statistica"),
                ),
            ],
            options={
                "verbose_name": "Statistica combo reliquiario",
                "verbose_name_plural": "Statistiche combo reliquiario",
                "unique_together": {("combo", "statistica")},
            },
            bases=(kor35.syncing.SyncableModel, models.Model),
        ),
    ]
