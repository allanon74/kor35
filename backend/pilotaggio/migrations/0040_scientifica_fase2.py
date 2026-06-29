# Generated manually — Console scientifica Fase 2 (matrice R/S/T, coerenza, interventi)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0039_scientifica_fase1"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessionevolo",
            name="interventi_scientifici_count",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Interventi scientifici attivi eseguiti in questa sessione.",
            ),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="ca_soppressa_scientifica",
            field=models.BooleanField(
                default=False,
                help_text="Prossima valutazione CA soppressa da gabbia dimensionale.",
            ),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="eco_parziale_attiva",
            field=models.BooleanField(
                default=False,
                help_text="Prossima valutazione SP non decrementa i tick (eco parziale).",
            ),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="dilatazioni_applicate",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Dilatazioni temporali già applicate su questo evento.",
            ),
        ),
        migrations.AddField(
            model_name="eventoattivosessione",
            name="correzione_paradosso_applicata",
            field=models.BooleanField(
                default=False,
                help_text="Correzione paradosso (DEFCON -1) già usata su questo evento.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_interventi_abilitati",
            field=models.BooleanField(
                default=True,
                help_text="Abilita matrice R/S/T e interventi attivi in console scientifica.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_coerenza_cap",
            field=models.PositiveSmallIntegerField(
                default=24,
                help_text="Massimo coerenza di campo accumulabile.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_livello_min_esotici",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Livello minimo R/S/T per generare coerenza a ogni tick.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_interventi_max_per_volo",
            field=models.PositiveSmallIntegerField(
                default=12,
                help_text="Limite interventi attivi (escluso reset risonanza) per sessione.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="scientifica_interventi_requisiti_json",
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text=(
                    "Override requisiti componenti per tipo intervento "
                    "(chiavi: dilatazione, gabbia, correzione, eco). "
                    "Lista vuota = N unità qualsiasi."
                ),
            ),
        ),
        migrations.CreateModel(
            name="ScientificoStatoNave",
            fields=[
                (
                    "singleton_id",
                    models.PositiveSmallIntegerField(
                        default=1,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("sync_id", models.UUIDField(db_index=True, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "coerenza_accumulata",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Coerenza di campo disponibile per interventi.",
                    ),
                ),
                (
                    "fase_r",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Fase matrice Nucleo Temporale (0–2).",
                    ),
                ),
                (
                    "fase_s",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Fase matrice Nucleo Dimensionale (0–2).",
                    ),
                ),
                (
                    "fase_t",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Fase matrice Correttore Paradossi (0–2).",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stato scientifico nave",
                "verbose_name_plural": "Stato scientifico nave",
            },
        ),
    ]
