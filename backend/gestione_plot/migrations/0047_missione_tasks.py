import uuid
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0046_eventovocereportare"),
        ("personaggi", "0249_carriera_fattore_task_prestigio_labels"),
        ("social", "0011_alter_socialprofile_nickname"),
    ]

    operations = [
        migrations.CreateModel(
            name="Missione",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("titolo", models.CharField(max_length=200)),
                ("descrizione", models.TextField(blank=True)),
                (
                    "reward_crediti",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Premio Crediti (base)",
                    ),
                ),
                (
                    "reward_prestigio",
                    models.PositiveIntegerField(default=0, verbose_name="Premio Prestigio (base)"),
                ),
                (
                    "tipo_risoluzione",
                    models.CharField(
                        choices=[
                            ("TECNICA", "Tecnica"),
                            ("POST_SOCIAL", "Post Social"),
                            ("QUEST", "Quest"),
                            ("MANUALE", "Manuale"),
                        ],
                        default="MANUALE",
                        max_length=20,
                    ),
                ),
                (
                    "premio_solo_primo",
                    models.BooleanField(
                        default=False,
                        help_text="Se attivo, solo il primo risolvitore riceve il premio (gli altri possono essere segnati senza ricompensa).",
                        verbose_name="Premio solo al primo",
                    ),
                ),
                (
                    "malus_non_primo_crediti",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="Sottratto al premio Cr se non sei il primo (ignorato se premio solo al primo).",
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Malus Crediti se non primo",
                    ),
                ),
                (
                    "malus_non_primo_prestigio",
                    models.PositiveIntegerField(default=0, verbose_name="Malus Prestigio se non primo"),
                ),
                (
                    "bonus_successive_crediti",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        help_text="Aggiunto al premio Cr dal secondo risolvitore in poi.",
                        max_digits=12,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Bonus Crediti risoluzioni successive",
                    ),
                ),
                (
                    "bonus_successive_prestigio",
                    models.PositiveIntegerField(default=0, verbose_name="Bonus Prestigio risoluzioni successive"),
                ),
                ("attiva", models.BooleanField(default=True)),
                ("ordine", models.PositiveIntegerField(default=0)),
                (
                    "korp",
                    models.ForeignKey(
                        blank=True,
                        help_text="Se valorizzato, la task è di quella KORP (ricompense maggiorate per i membri).",
                        limit_choices_to={"tipo_carriera__codice": "korp"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="missioni",
                        to="personaggi.carriera",
                    ),
                ),
            ],
            options={
                "verbose_name": "Task (missione)",
                "verbose_name_plural": "Tasks (missioni)",
                "ordering": ["ordine", "titolo"],
            },
        ),
        migrations.CreateModel(
            name="MissioneEvento",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="missione_links",
                        to="gestione_plot.evento",
                    ),
                ),
                (
                    "missione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evento_links",
                        to="gestione_plot.missione",
                    ),
                ),
            ],
            options={
                "verbose_name": "Task–Evento",
                "verbose_name_plural": "Task–Eventi",
            },
        ),
        migrations.CreateModel(
            name="MissioneRisoluzione",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(auto_now_add=True)),
                ("is_primo", models.BooleanField(default=False)),
                ("reward_crediti", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("reward_prestigio", models.PositiveIntegerField(default=0)),
                ("ricompensa_reclamata", models.BooleanField(default=False)),
                ("reclamata_at", models.DateTimeField(blank=True, null=True)),
                ("note", models.TextField(blank=True)),
                (
                    "evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="risoluzioni_missioni",
                        to="gestione_plot.evento",
                    ),
                ),
                (
                    "giorno",
                    models.ForeignKey(
                        blank=True,
                        help_text="Giorno plot per risoluzioni manuali.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="missioni_manuali_risolte",
                        to="gestione_plot.giornoevento",
                    ),
                ),
                (
                    "missione",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="risoluzioni",
                        to="gestione_plot.missione",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="risoluzioni_missioni",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "proposta_tecnica",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="missioni_risolte",
                        to="personaggi.propostatecnica",
                    ),
                ),
                (
                    "quest",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="missioni_risolte",
                        to="gestione_plot.quest",
                    ),
                ),
                (
                    "social_post",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="missioni_risolte",
                        to="social.socialpost",
                    ),
                ),
            ],
            options={
                "verbose_name": "Risoluzione task",
                "verbose_name_plural": "Risoluzioni task",
                "ordering": ["resolved_at"],
            },
        ),
        migrations.AddField(
            model_name="missione",
            name="eventi",
            field=models.ManyToManyField(
                blank=True,
                related_name="missioni",
                through="gestione_plot.MissioneEvento",
                to="gestione_plot.evento",
            ),
        ),
        migrations.AddConstraint(
            model_name="missioneevento",
            constraint=models.UniqueConstraint(fields=("missione", "evento"), name="uq_missione_evento"),
        ),
        migrations.AddConstraint(
            model_name="missionerisoluzione",
            constraint=models.UniqueConstraint(
                fields=("missione", "evento", "personaggio"),
                name="uq_missione_evento_personaggio",
            ),
        ),
    ]
