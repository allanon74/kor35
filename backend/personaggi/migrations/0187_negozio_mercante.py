import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0186_accademia_catalogo_flags"),
    ]

    operations = [
        migrations.CreateModel(
            name="NegozioMercante",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nome", models.CharField(max_length=120)),
                ("descrizione", models.TextField(blank=True, default="")),
                (
                    "tipo_negozio",
                    models.CharField(
                        choices=[("ALT", "Alternativo (QR)"), ("CORP", "Corporativo (tab)")],
                        db_index=True,
                        default="ALT",
                        max_length=4,
                    ),
                ),
                ("attivo", models.BooleanField(db_index=True, default=True)),
                ("saldo_crediti", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("incassa_acquisti_catalogo", models.BooleanField(default=True)),
                ("regole_apertura", models.JSONField(blank=True, default=dict)),
                ("regole_visibilita", models.JSONField(blank=True, default=dict)),
                ("config_economia", models.JSONField(blank=True, default=dict)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="negozi_mercante",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "inventario",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="negozio_mercante",
                        to="personaggi.inventario",
                    ),
                ),
                (
                    "qr_code",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="negozio_mercante",
                        to="personaggi.qrcode",
                    ),
                ),
            ],
            options={
                "verbose_name": "Negozio mercante",
                "verbose_name_plural": "Negozi mercante",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="NegozioMercanteVoce",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tipo_voce",
                    models.CharField(
                        choices=[
                            ("OGB", "Oggetto base (template)"),
                            ("OGG", "Oggetto (istanza unica)"),
                            ("ABL", "Abilità"),
                            ("INF", "Infusione"),
                            ("TES", "Tessitura"),
                            ("CER", "Cerimoniale"),
                            ("CON", "Consumabile (lotto)"),
                        ],
                        db_index=True,
                        max_length=3,
                    ),
                ),
                ("prezzo_crediti", models.PositiveIntegerField()),
                ("ordine", models.PositiveIntegerField(default=0)),
                ("attivo", models.BooleanField(default=True)),
                ("quantita_residua", models.PositiveIntegerField(blank=True, null=True)),
                ("consumabile_nome", models.CharField(blank=True, default="", max_length=200)),
                ("consumabile_livello", models.PositiveIntegerField(default=1)),
                (
                    "abilita",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voci_negozio_mercante",
                        to="personaggi.abilita",
                    ),
                ),
                (
                    "cerimoniale",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voci_negozio_mercante",
                        to="personaggi.cerimoniale",
                    ),
                ),
                (
                    "consumabile_tessitura",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="voci_consumabile_negozio",
                        to="personaggi.tessitura",
                    ),
                ),
                (
                    "infusione",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voci_negozio_mercante",
                        to="personaggi.infusione",
                    ),
                ),
                (
                    "negozio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voci",
                        to="personaggi.negoziomercante",
                    ),
                ),
                (
                    "oggetto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voci_negozio_mercante",
                        to="personaggi.oggetto",
                    ),
                ),
                (
                    "oggetto_base",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voci_negozio_mercante",
                        to="personaggi.oggettobase",
                    ),
                ),
                (
                    "tessitura",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="voci_negozio_mercante",
                        to="personaggi.tessitura",
                    ),
                ),
            ],
            options={
                "verbose_name": "Voce negozio mercante",
                "verbose_name_plural": "Voci negozio mercante",
                "ordering": ["ordine", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="NegozioMercanteStock",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "stato",
                    models.CharField(
                        choices=[("DISP", "Disponibile"), ("VEND", "Venduto")],
                        db_index=True,
                        default="DISP",
                        max_length=4,
                    ),
                ),
                ("prezzo_rivendita", models.PositiveIntegerField()),
                ("valore_riferimento", models.PositiveIntegerField()),
                (
                    "negozio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock",
                        to="personaggi.negoziomercante",
                    ),
                ),
                (
                    "oggetto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stock_negozio_mercante",
                        to="personaggi.oggetto",
                    ),
                ),
                (
                    "venduto_da",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="oggetti_venduti_a_negozi",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock negozio mercante",
                "verbose_name_plural": "Stock negozi mercante",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="NegozioMercanteMovimento",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tipo", models.CharField(max_length=20)),
                ("importo", models.DecimalField(decimal_places=2, max_digits=12)),
                ("saldo_dopo", models.DecimalField(decimal_places=2, max_digits=12)),
                ("nota", models.CharField(blank=True, default="", max_length=255)),
                (
                    "negozio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movimenti",
                        to="personaggi.negoziomercante",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="movimenti_negozio_mercante",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "riferimento_stock",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="personaggi.negoziomercantestock",
                    ),
                ),
                (
                    "riferimento_voce",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="personaggi.negoziomercantevoce",
                    ),
                ),
            ],
            options={
                "verbose_name": "Movimento cassa negozio",
                "verbose_name_plural": "Movimenti cassa negozi",
                "ordering": ["-created_at"],
            },
        ),
    ]
