from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_stato_nave_da_sessioni(apps, schema_editor):
    StatoSottosistemaNave = apps.get_model("pilotaggio", "StatoSottosistemaNave")
    StatoSottosistemaSessione = apps.get_model("pilotaggio", "StatoSottosistemaSessione")
    SottosistemaNave = apps.get_model("pilotaggio", "SottosistemaNave")

    campi = (
        "online",
        "guasto_at",
        "recovery_at",
        "livello_target",
        "livello_attuale",
        "invertito",
        "espulso",
        "direzione",
    )
    for sdef in SottosistemaNave.objects.filter(attivo=True):
        latest = (
            StatoSottosistemaSessione.objects.filter(sottosistema_id=sdef.pk)
            .order_by("-updated_at")
            .first()
        )
        defaults = {
            "sync_id": uuid.uuid4(),
            "online": True,
            "livello_target": 0,
            "livello_attuale": 0,
            "direzione": "avanti",
            "invertito": False,
            "espulso": False,
        }
        if latest is not None:
            for k in campi:
                defaults[k] = getattr(latest, k)
        StatoSottosistemaNave.objects.get_or_create(
            sottosistema_id=sdef.pk,
            defaults=defaults,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0031_vocediariovolo"),
    ]

    operations = [
        migrations.CreateModel(
            name="StatoSottosistemaNave",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("online", models.BooleanField(default=True)),
                ("guasto_at", models.DateTimeField(blank=True, null=True)),
                ("recovery_at", models.DateTimeField(blank=True, null=True)),
                ("livello_target", models.PositiveSmallIntegerField(default=0)),
                ("livello_attuale", models.PositiveSmallIntegerField(default=0)),
                ("invertito", models.BooleanField(default=False)),
                ("espulso", models.BooleanField(default=False)),
                (
                    "direzione",
                    models.CharField(
                        choices=[
                            ("avanti", "Avanti"),
                            ("indietro", "Indietro"),
                            ("su", "Su"),
                            ("giu", "Giu"),
                            ("destra", "Destra"),
                            ("sinistra", "Sinistra"),
                        ],
                        default="avanti",
                        max_length=16,
                    ),
                ),
                (
                    "sottosistema",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stato_nave",
                        to="pilotaggio.sottosistemanave",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stato sottosistema nave (persistente)",
                "verbose_name_plural": "Stati sottosistemi nave (persistenti)",
            },
        ),
        migrations.AddIndex(
            model_name="statosottosistemanave",
            index=models.Index(fields=["online"], name="pilotaggio__online__nave_idx"),
        ),
        migrations.AddIndex(
            model_name="statosottosistemanave",
            index=models.Index(fields=["espulso"], name="pilotaggio__espulso_nave_idx"),
        ),
        migrations.RunPython(seed_stato_nave_da_sessioni, migrations.RunPython.noop),
    ]
