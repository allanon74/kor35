"""Bonus caratteristica contestuali e abilità conferite dagli oggetti."""

import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0303_gruppo_chat_carriera"),
    ]

    operations = [
        migrations.CreateModel(
            name="BonusCaratteristicaContestuale",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("valore", models.PositiveSmallIntegerField(default=1)),
                (
                    "vale_tessiture",
                    models.BooleanField(default=False, verbose_name="Vale per le tessiture"),
                ),
                (
                    "vale_infusioni",
                    models.BooleanField(default=False, verbose_name="Vale per le infusioni"),
                ),
                (
                    "vale_cerimoniali",
                    models.BooleanField(default=False, verbose_name="Vale per i cerimoniali"),
                ),
                (
                    "abilita",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonus_caratteristica_contestuali",
                        to="personaggi.abilita",
                    ),
                ),
                (
                    "caratteristica",
                    models.ForeignKey(
                        limit_choices_to={"tipo": "CA"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonus_contestuali",
                        to="personaggi.punteggio",
                        verbose_name="Caratteristica",
                    ),
                ),
                (
                    "infusione",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonus_caratteristica_contestuali",
                        to="personaggi.infusione",
                    ),
                ),
                (
                    "oggetto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonus_caratteristica_contestuali",
                        to="personaggi.oggetto",
                    ),
                ),
                (
                    "oggetto_base",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bonus_caratteristica_contestuali",
                        to="personaggi.oggettobase",
                    ),
                ),
                (
                    "aure",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Vuoto = tutte le aure degli ambiti selezionati.",
                        limit_choices_to={"tipo": "AU"},
                        related_name="bonus_ca_contestuali_limitati",
                        to="personaggi.punteggio",
                        verbose_name="Aure",
                    ),
                ),
            ],
            options={
                "verbose_name": "Bonus caratteristica contestuale",
                "verbose_name_plural": "Bonus caratteristiche contestuali",
                "constraints": [
                    models.CheckConstraint(
                        check=(
                            Q(abilita__isnull=False, oggetto__isnull=True, infusione__isnull=True, oggetto_base__isnull=True)
                            | Q(abilita__isnull=True, oggetto__isnull=False, infusione__isnull=True, oggetto_base__isnull=True)
                            | Q(abilita__isnull=True, oggetto__isnull=True, infusione__isnull=False, oggetto_base__isnull=True)
                            | Q(abilita__isnull=True, oggetto__isnull=True, infusione__isnull=True, oggetto_base__isnull=False)
                        ),
                        name="bonus_ca_contestuale_un_proprietario",
                    ),
                    models.CheckConstraint(
                        check=Q(vale_tessiture=True) | Q(vale_infusioni=True) | Q(vale_cerimoniali=True),
                        name="bonus_ca_contestuale_almeno_un_ambito",
                    ),
                    models.CheckConstraint(
                        check=Q(valore__gte=1),
                        name="bonus_ca_contestuale_valore_positivo",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="OggettoAbilitaConferita",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "abilita",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conferimenti_da_oggetto",
                        to="personaggi.abilita",
                    ),
                ),
                (
                    "infusione",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="abilita_conferite",
                        to="personaggi.infusione",
                    ),
                ),
                (
                    "oggetto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="abilita_conferite",
                        to="personaggi.oggetto",
                    ),
                ),
                (
                    "oggetto_base",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="abilita_conferite",
                        to="personaggi.oggettobase",
                    ),
                ),
            ],
            options={
                "verbose_name": "Abilità conferita da oggetto",
                "verbose_name_plural": "Abilità conferite da oggetto",
                "constraints": [
                    models.CheckConstraint(
                        check=(
                            Q(oggetto__isnull=False, infusione__isnull=True, oggetto_base__isnull=True)
                            | Q(oggetto__isnull=True, infusione__isnull=False, oggetto_base__isnull=True)
                            | Q(oggetto__isnull=True, infusione__isnull=True, oggetto_base__isnull=False)
                        ),
                        name="abilita_conferita_un_proprietario",
                    ),
                    models.UniqueConstraint(
                        condition=Q(oggetto__isnull=False),
                        fields=("oggetto", "abilita"),
                        name="abilita_conferita_oggetto_unica",
                    ),
                    models.UniqueConstraint(
                        condition=Q(infusione__isnull=False),
                        fields=("infusione", "abilita"),
                        name="abilita_conferita_infusione_unica",
                    ),
                    models.UniqueConstraint(
                        condition=Q(oggetto_base__isnull=False),
                        fields=("oggetto_base", "abilita"),
                        name="abilita_conferita_oggetto_base_unica",
                    ),
                ],
            },
        ),
    ]
