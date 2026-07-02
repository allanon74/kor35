from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0039_evento_start_end_crediti_base"),
        ("personaggi", "0231_scommesse_allibratore_bonus_quota"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProgrammazioneTorneoScommesse",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("attiva", models.BooleanField(default=False, help_text="Se attiva, la sincronizzazione può creare nuove giornate.")),
                ("auto_genera", models.BooleanField(default=True, help_text="Crea automaticamente calendari per i prossimi eventi (cron/sync).")),
                (
                    "strategia_accoppiamento",
                    models.CharField(
                        choices=[("RANDOM", "Casuale"), ("ROUND_ROBIN", "Girone all'italiana")],
                        default="ROUND_ROBIN",
                        max_length=16,
                    ),
                ),
                (
                    "ore_apertura_prima_evento",
                    models.PositiveIntegerField(
                        default=336,
                        help_text="Ore prima dell'inizio evento in cui aprono le scommesse (default 14 giorni).",
                    ),
                ),
                (
                    "ore_chiusura_prima_evento",
                    models.PositiveIntegerField(
                        default=2,
                        help_text="Ore prima dell'inizio evento in cui si pubblicano i risultati (default 2h).",
                    ),
                ),
                ("giornata_corrente", models.PositiveSmallIntegerField(default=0, help_text="Contatore giornate già generate (usato per il girone).")),
                (
                    "sport",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="programmazione",
                        to="personaggi.sportscommesse",
                    ),
                ),
                (
                    "ultimo_evento",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="programmazioni_scommesse_ultimo",
                        to="gestione_plot.evento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Programmazione torneo scommesse",
                "verbose_name_plural": "Programmazioni torneo scommesse",
            },
        ),
        migrations.AddField(
            model_name="calendarioscommesse",
            name="evento",
            field=models.ForeignKey(
                blank=True,
                help_text="Evento LARP a cui è collegata questa giornata (se generata da programmazione).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="calendari_scommesse",
                to="gestione_plot.evento",
            ),
        ),
        migrations.AddField(
            model_name="calendarioscommesse",
            name="giornata_numero",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Numero giornata nel torneo (1, 2, 3…).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="calendarioscommesse",
            name="programmazione",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="calendari_generati",
                to="personaggi.programmazionetorneoscommesse",
            ),
        ),
        migrations.AddConstraint(
            model_name="calendarioscommesse",
            constraint=models.UniqueConstraint(
                condition=models.Q(("evento__isnull", False)),
                fields=("sport", "evento"),
                name="uniq_calendario_sport_evento",
            ),
        ),
    ]
