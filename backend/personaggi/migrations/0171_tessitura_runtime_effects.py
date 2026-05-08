from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0170_abilita_nascondi_in_scheda_abilita"),
    ]

    operations = [
        migrations.AddField(
            model_name="tessitura",
            name="abilita_temporanea",
            field=models.ForeignKey(
                blank=True,
                help_text="Abilita da applicare temporaneamente quando la tessitura viene attivata in Game.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tessiture_che_attivano_abilita_temporanea",
                to="personaggi.abilita",
            ),
        ),
        migrations.AddField(
            model_name="tessitura",
            name="durata_effetto_secondi",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Durata in secondi dell'effetto temporaneo (0 = non attivabile).",
            ),
        ),
        migrations.AddField(
            model_name="tessitura",
            name="oggetto_runtime_config",
            field=models.JSONField(
                blank=True,
                help_text='Configurazione oggetto runtime leggero: {"nome":"...", "slot_key":"melee", "modificatori":[{"stat_sigla":"PV","valore":1,"tipo_modificatore":"ADD"}], "formula_rules":[]}.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="tessitura",
            name="usa_effetto_temporaneo",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, la tessitura puo generare un effetto runtime temporaneo in Game.",
            ),
        ),
        migrations.CreateModel(
            name="TessituraEffettoRuntime",
            fields=[
                ("sync_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("inizio", models.DateTimeField(db_index=True, default=timezone.now)),
                ("fine", models.DateTimeField(db_index=True)),
                ("is_attivo", models.BooleanField(db_index=True, default=True)),
                ("motivo_fine", models.CharField(blank=True, default="", max_length=40)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("abilita_temporanea", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="runtime_tessitura_generati", to="personaggi.abilita")),
                ("attivata_da", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="runtime_tessitura_attivati", to=settings.AUTH_USER_MODEL)),
                ("personaggio", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tessiture_runtime_attive", to="personaggi.personaggio")),
                ("tessitura", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runtime_attivi", to="personaggi.tessitura")),
            ],
            options={
                "verbose_name": "Runtime tessitura",
                "verbose_name_plural": "Runtime tessiture",
                "ordering": ["-fine"],
            },
        ),
        migrations.CreateModel(
            name="TessituraOggettoRuntime",
            fields=[
                ("sync_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("nome", models.CharField(max_length=120)),
                ("slot_key", models.CharField(db_index=True, max_length=20)),
                ("equipaggiato", models.BooleanField(db_index=True, default=True)),
                ("config_modificatori", models.JSONField(blank=True, default=list)),
                ("config_formule", models.JSONField(blank=True, default=list)),
                ("config_cariche", models.JSONField(blank=True, default=dict)),
                ("effetto_runtime", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="oggetto_runtime", to="personaggi.tessituraeffettoruntime")),
            ],
            options={
                "verbose_name": "Oggetto runtime tessitura",
                "verbose_name_plural": "Oggetti runtime tessitura",
                "ordering": ["-updated_at"],
            },
        ),
    ]
