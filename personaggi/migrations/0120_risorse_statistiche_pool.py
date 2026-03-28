# Generated manually for risorse a pool (Fortuna / generalizzabile)

import uuid

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0119_merge_0114_cleanup_0118_punteggio_dipendente"),
    ]

    operations = [
        migrations.AddField(
            model_name="statistica",
            name="is_risorsa_pool",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, il valore massimo della statistica definisce il tetto di un pool "
                "con contatore separato (consumi, log, effetti temporanei). Es. Fortuna (FRT).",
                verbose_name="Risorsa a pool",
            ),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="risorse_consumabili",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Contatori attuali per statistiche con pool (es. {"FRT": 2}). Se assente, si assume pari al massimo.',
                verbose_name="Risorse a pool (corrente)",
            ),
        ),
        migrations.AddField(
            model_name="abilita",
            name="effetto_uso_risorsa",
            field=models.JSONField(
                blank=True,
                help_text='Opzionale. Es.: {"stat_sigla":"FRT","durata":"O1H","modifiche":[{"stat_sigla":"PV","valore":1,"tipo_modificatore":"ADD"}]}',
                null=True,
                verbose_name="Effetto all'uso risorsa",
            ),
        ),
        migrations.AddField(
            model_name="abilita",
            name="recupero_risorsa",
            field=models.JSONField(
                blank=True,
                help_text='Opzionale. Es.: {"stat_sigla":"FRT","quando":"FINE_EVENTO"} oppure FINE_ANNO_GIOCO (gestione manuale/automatismi futuri).',
                null=True,
                verbose_name="Recupero risorsa",
            ),
        ),
        migrations.CreateModel(
            name="RisorsaStatisticaMovimento",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("statistica_sigla", models.CharField(db_index=True, max_length=3)),
                ("importo", models.IntegerField()),
                ("descrizione", models.CharField(max_length=240)),
                (
                    "tipo_movimento",
                    models.CharField(
                        choices=[
                            ("CON", "Consumo"),
                            ("REC", "Recupero"),
                            ("STF", "Staff"),
                            ("SYS", "Sistema"),
                        ],
                        default="CON",
                        max_length=3,
                    ),
                ),
                ("data", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movimenti_risorsa_stat",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Movimento risorsa statistica",
                "verbose_name_plural": "Movimenti risorse statistiche",
                "ordering": ["-data"],
            },
        ),
        migrations.CreateModel(
            name="EffettoRisorsaTemporaneo",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("statistica_risorsa_sigla", models.CharField(max_length=3)),
                (
                    "durata_tipo",
                    models.CharField(
                        choices=[
                            ("O1H", "1 ora"),
                            ("DAY", "Fino a fine giornata (locale)"),
                            ("EVT", "Evento in corso"),
                        ],
                        default="O1H",
                        max_length=3,
                    ),
                ),
                ("scadenza", models.DateTimeField(db_index=True)),
                (
                    "modifiche",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='Lista di {"stat_sigla":"PV","valore":1,"tipo_modificatore":"ADD"|"MOL"}',
                    ),
                ),
                (
                    "abilita",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="effetti_risorsa_generati",
                        to="personaggi.abilita",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="effetti_risorsa_temp",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Effetto risorsa temporaneo",
                "verbose_name_plural": "Effetti risorsa temporanei",
                "ordering": ["-scadenza"],
            },
        ),
    ]
