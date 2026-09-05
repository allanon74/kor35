import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0263_proposta_messaggio_crediti_split"),
    ]

    operations = [
        migrations.AddField(
            model_name="negoziomercantevoce",
            name="non_vendibile",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo, la voce non compare nel listino come articolo singolo: "
                    "è acquistabile solo come componente di un bundle."
                ),
            ),
        ),
        migrations.CreateModel(
            name="NegozioMercanteBundle",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=200)),
                ("descrizione", models.TextField(blank=True, default="")),
                (
                    "prezzo_crediti",
                    models.PositiveIntegerField(
                        help_text=(
                            "Prezzo del pacchetto (manuale, non somma automatica delle voci)."
                        ),
                    ),
                ),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attivo", models.BooleanField(default=True)),
                (
                    "negozio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bundle",
                        to="personaggi.negoziomercante",
                    ),
                ),
            ],
            options={
                "verbose_name": "Bundle negozio mercante",
                "verbose_name_plural": "Bundle negozi mercante",
                "ordering": ["ordine", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="NegozioMercanteBundleRiga",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "quantita",
                    models.PositiveIntegerField(
                        default=1,
                        help_text=(
                            "Quante unità di questa voce consegna un acquisto del bundle."
                        ),
                    ),
                ),
                ("ordine", models.PositiveIntegerField(default=0)),
                (
                    "bundle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="righe",
                        to="personaggi.negoziomercantebundle",
                    ),
                ),
                (
                    "voce",
                    models.ForeignKey(
                        help_text="Voce del medesimo negozio inclusa nel pacchetto.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="righe_bundle",
                        to="personaggi.negoziomercantevoce",
                    ),
                ),
            ],
            options={
                "verbose_name": "Riga bundle negozio",
                "verbose_name_plural": "Righe bundle negozio",
                "ordering": ["ordine", "created_at"],
            },
        ),
        migrations.AddField(
            model_name="negoziomercantemovimento",
            name="riferimento_bundle",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="personaggi.negoziomercantebundle",
            ),
        ),
        migrations.AddConstraint(
            model_name="negoziomercantebundleriga",
            constraint=models.UniqueConstraint(
                fields=("bundle", "voce"),
                name="uniq_negozio_bundle_voce",
            ),
        ),
    ]
