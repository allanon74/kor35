# Generated manually for QR multi-tipo (manifesto, inventario session, innesco timer)

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _default_campagna_fk():
    """Evita import circolare: risolve la campagna default a runtime migrazione."""
    from django.apps import apps

    Campagna = apps.get_model("personaggi", "Campagna")
    row = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.filter(is_default=True).first()
    return row.pk if row else None


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("personaggi", "0154_tier_caratteristiche_visibili"),
    ]

    operations = [
        migrations.AddField(
            model_name="manifesto",
            name="requisiti_lettura",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Requisiti opzionali (statistica per sigla o abilità per id). Vuoto = accesso libero.",
            ),
        ),
        migrations.CreateModel(
            name="InnescoTimer",
            fields=[
                (
                    "avista_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="personaggi.a_vista",
                    ),
                ),
                (
                    "modalita_target",
                    models.CharField(
                        choices=[
                            ("globale", "Tutti i giocatori"),
                            ("filtri", "Solo era / regione / KORP selezionate"),
                        ],
                        db_index=True,
                        default="globale",
                        max_length=16,
                    ),
                ),
                (
                    "durata_secondi",
                    models.PositiveIntegerField(default=60, verbose_name="Durata countdown (secondi)"),
                ),
                (
                    "max_cariche",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Quante volte si può attivare prima della rigenerazione (0 = illimitato).",
                        verbose_name="Cariche per ciclo",
                    ),
                ),
                (
                    "rigenera_cariche_ogni_secondi",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Lasciare vuoto per nessuna rigenerazione automatica delle cariche.",
                        null=True,
                        verbose_name="Rigenera cariche ogni (secondi)",
                    ),
                ),
                (
                    "segnale_luminoso",
                    models.BooleanField(
                        default=True,
                        help_text="Il client può evidenziare il timer in modo più visibile.",
                        verbose_name="Segnale luminoso in-app",
                    ),
                ),
                (
                    "campagna",
                    models.ForeignKey(
                        db_index=True,
                        default=_default_campagna_fk,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="innesco_timers",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Innesco timer (QR)",
                "verbose_name_plural": "Inneschi timer (QR)",
            },
            bases=("personaggi.A_vista",),
        ),
        migrations.AddField(
            model_name="innescotimer",
            name="target_ere",
            field=models.ManyToManyField(blank=True, related_name="innesco_timers", to="personaggi.era"),
        ),
        migrations.AddField(
            model_name="innescotimer",
            name="target_korps",
            field=models.ManyToManyField(blank=True, related_name="innesco_timers", to="personaggi.korp"),
        ),
        migrations.AddField(
            model_name="innescotimer",
            name="target_regioni",
            field=models.ManyToManyField(blank=True, related_name="innesco_timers", to="personaggi.regione"),
        ),
        migrations.CreateModel(
            name="QrInventarioScanSession",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
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
                ("first_scan_at", models.DateTimeField(auto_now_add=True)),
                ("confermato_at", models.DateTimeField(blank=True, null=True)),
                (
                    "inventario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="qr_scan_sessions",
                        to="personaggi.inventario",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="qr_inventario_sessions",
                        to="personaggi.personaggio",
                    ),
                ),
                (
                    "qr_code",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventario_scan_sessions",
                        to="personaggi.qrcode",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="qr_inventario_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Sessione scansione inventario QR",
                "verbose_name_plural": "Sessioni scansione inventario QR",
            },
        ),
        migrations.AddIndex(
            model_name="qrinventarioscansession",
            index=models.Index(fields=["user", "qr_code", "confermato_at"], name="qrinv_sess_uqcf"),
        ),
        migrations.AddIndex(
            model_name="qrinventarioscansession",
            index=models.Index(fields=["personaggio", "qr_code"], name="qrinv_sess_pgqr"),
        ),
        migrations.CreateModel(
            name="StatoInnescoTimerPersonaggio",
            fields=[
                (
                    "sync_id",
                    models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
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
                ("data_fine", models.DateTimeField(verbose_name="Scadenza countdown")),
                ("cariche_usate_ciclo", models.PositiveIntegerField(default=0)),
                ("ciclo_iniziato_at", models.DateTimeField(blank=True, null=True)),
                (
                    "innesco_timer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stati_personaggio",
                        to="personaggi.innescotimer",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stati_innesco_timer",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stato innesco timer (personaggio)",
                "verbose_name_plural": "Stati innesco timer (personaggio)",
                "unique_together": {("personaggio", "innesco_timer")},
            },
        ),
        migrations.AddIndex(
            model_name="statoinnescotimerpersonaggio",
            index=models.Index(fields=["personaggio", "innesco_timer"], name="innesco_st_pg_it"),
        ),
    ]
