import uuid

import django.db.models.deletion
import personaggi.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0159_statistica_pool_corrente_default_pieno"),
    ]

    operations = [
        migrations.CreateModel(
            name="NodoRewardConfig",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("nome", models.CharField(max_length=120)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("attiva", models.BooleanField(default=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        db_index=True,
                        default=personaggi.models.get_default_campagna_id,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="nodo_reward_configs",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configurazione reward nodo",
                "verbose_name_plural": "Configurazioni reward nodo",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="NodoRewardRegolaEra",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "tipo_reward",
                    models.CharField(
                        choices=[("POOL", "Pool statistica"), ("CRDT", "Crediti")],
                        db_index=True,
                        default="POOL",
                        max_length=4,
                    ),
                ),
                (
                    "delta_base",
                    models.IntegerField(
                        default=1,
                        help_text="Valore base: con nodo MAGGIORE verrà moltiplicato x2.",
                    ),
                ),
                (
                    "config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="regole_era",
                        to="personaggi.nodorewardconfig",
                    ),
                ),
                (
                    "era",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nodo_reward_regole",
                        to="personaggi.era",
                    ),
                ),
                (
                    "statistica_pool",
                    models.ForeignKey(
                        blank=True,
                        help_text="Richiesta quando tipo_reward = Pool statistica.",
                        limit_choices_to={"is_risorsa_pool": True},
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="nodo_reward_regole",
                        to="personaggi.statistica",
                    ),
                ),
            ],
            options={
                "verbose_name": "Regola reward nodo per era",
                "verbose_name_plural": "Regole reward nodo per era",
                "ordering": ["config__nome", "era__ordine", "era__nome"],
                "unique_together": {("config", "era")},
            },
        ),
        migrations.AddField(
            model_name="nodo",
            name="reward_config",
            field=models.ForeignKey(
                blank=True,
                help_text="Se valorizzata, usa le regole DB per era. Se vuota, fallback hardcoded legacy.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="nodi",
                to="personaggi.nodorewardconfig",
            ),
        ),
    ]
