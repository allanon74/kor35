from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0222_mattone_indice_componente"),
        ("pilotaggio", "0032_statosottosistemanave"),
    ]

    operations = [
        migrations.AddField(
            model_name="sottosistemanave",
            name="requisiti_riparazione_json",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Lista vincoli: specifico (mattone_id+quantita) o scelta (mattone_ids+quantita).",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="richiede_componenti_riparazione",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo (e riparazione componenti abilitata in runtime), la riparazione QR consuma componenti da stiva.",
            ),
        ),
        migrations.AlterField(
            model_name="sottosistemanave",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("generatore", "Generatore"),
                    ("batteria", "Batteria"),
                    ("serbatoio", "Serbatoio carburante"),
                    ("motore", "Motore principale"),
                    ("portale", "Portale transdimensionale"),
                    ("manovra", "Propulsori di manovra"),
                    ("compattatore", "Compattatore"),
                ],
                default="standard",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="annichilamento_opposti_abilitato",
            field=models.BooleanField(
                default=True,
                help_text="Annichilamento colori opposti in stiva dopo 5 tick di coesistenza.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="compattatore_console_abilitata",
            field=models.BooleanField(
                default=False,
                help_text="Abilita console /pilot/?screen=compattatore.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="compattatore_login_richiesto",
            field=models.BooleanField(
                default=True,
                help_text="Richiede login alla console compattatore.",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="compattatore_stat_accesso_sigla",
            field=models.CharField(
                default="0IN",
                help_text="Sigla statistica per accesso console compattatore (es. 0IN>0).",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="riparazione_componenti_abilitata",
            field=models.BooleanField(
                default=False,
                help_text="Abilita consumo componenti da stiva nelle riparazioni QR (se richiesto dal sottosistema).",
            ),
        ),
        migrations.AddField(
            model_name="pilotruntimeconfig",
            name="stiva_ultimo_tick_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Ultimo tick annichilamento opposti stiva (idempotenza tra sessioni).",
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="CoppiaColoriComponente",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("ordine", models.PositiveSmallIntegerField(default=0)),
                (
                    "colore_a",
                    models.ForeignKey(
                        limit_choices_to={"tipo": "CA"},
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="coppie_componenti_a",
                        to="personaggi.punteggio",
                    ),
                ),
                (
                    "colore_b",
                    models.ForeignKey(
                        limit_choices_to={"tipo": "CA"},
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="coppie_componenti_b",
                        to="personaggi.punteggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Coppia colori componente",
                "verbose_name_plural": "Coppie colori componente",
                "ordering": ["ordine", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="StivaComponenteNave",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("quantita", models.PositiveIntegerField(default=0)),
                (
                    "mattone",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stiva_nave",
                        to="personaggi.mattone",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stiva componente nave",
                "verbose_name_plural": "Stiva componenti nave",
                "ordering": ["mattone__indice_componente", "mattone__ordine"],
            },
        ),
        migrations.CreateModel(
            name="StivaCoppiaOppositiStato",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tick_coesistenza", models.PositiveSmallIntegerField(default=0)),
                (
                    "coppia",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stato_coesistenza",
                        to="pilotaggio.coppiacoloricomponente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stato coesistenza opposti",
                "verbose_name_plural": "Stati coesistenza opposti",
            },
        ),
        migrations.AddConstraint(
            model_name="coppiacoloricomponente",
            constraint=models.UniqueConstraint(
                fields=("colore_a", "colore_b"), name="uniq_coppia_colori_componente"
            ),
        ),
    ]
