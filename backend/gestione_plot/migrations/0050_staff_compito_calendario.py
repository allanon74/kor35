# Generated manually: calendario compiti staff + feed iCal

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("personaggi", "0259_minigioco_pattern_sezione_default"),
        ("gestione_plot", "0049_evento_trasferimento_deposito"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffCompito",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                ("titolo", models.CharField(max_length=200)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("scadenza", models.DateTimeField(db_index=True)),
                (
                    "preavviso_minuti",
                    models.PositiveIntegerField(
                        default=1440,
                        help_text="Minuti prima della scadenza per la notifica di preavviso (0 = solo a scadenza).",
                    ),
                ),
                (
                    "preavviso_at",
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        help_text="Istante calcolato della notifica di preavviso.",
                        null=True,
                    ),
                ),
                ("crea_notifica_scadenza", models.BooleanField(default=True)),
                ("attivo", models.BooleanField(db_index=True, default=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_compiti",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "creato_da",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="staff_compiti_creati",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Compito staff",
                "verbose_name_plural": "Compiti staff",
                "ordering": ["scadenza", "titolo"],
            },
        ),
        migrations.CreateModel(
            name="StaffCompitoAssegnazione",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                ("completato_at", models.DateTimeField(blank=True, null=True)),
                (
                    "push_preavviso_inviata",
                    models.BooleanField(db_index=True, default=False),
                ),
                (
                    "push_scadenza_inviata",
                    models.BooleanField(db_index=True, default=False),
                ),
                (
                    "compito",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assegnazioni",
                        to="gestione_plot.staffcompito",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_compiti_assegnati",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Assegnazione compito staff",
                "verbose_name_plural": "Assegnazioni compiti staff",
                "ordering": ["compito_id", "user_id"],
            },
        ),
        migrations.CreateModel(
            name="CalendarioFeedToken",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                (
                    "token",
                    models.UUIDField(
                        db_index=True, default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="calendario_feed_token",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Token feed calendario",
                "verbose_name_plural": "Token feed calendario",
            },
        ),
        migrations.AddIndex(
            model_name="staffcompitoassegnazione",
            index=models.Index(
                fields=["user", "completato_at"],
                name="gestione_pl_user_id_c0a91e_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="staffcompitoassegnazione",
            index=models.Index(
                fields=["compito", "user"],
                name="gestione_pl_compito_2b4c11_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="staffcompitoassegnazione",
            constraint=models.UniqueConstraint(
                fields=("compito", "user"),
                name="uq_staff_compito_assegnazione_user",
            ),
        ),
    ]
