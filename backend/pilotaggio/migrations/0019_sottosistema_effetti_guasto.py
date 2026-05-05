from django.db import migrations, models


def _default_effetti_guasto():
    return {
        "tipo": "none",
        "valore": 0.0,
        "target_codice": "",
    }


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0018_sottosistema_serbatoio"),
    ]

    operations = [
        migrations.AddField(
            model_name="sottosistemanave",
            name="effetti_guasto_json",
            field=models.JSONField(
                blank=True,
                default=_default_effetti_guasto,
                help_text="Effetto applicato quando il sottosistema va guasto. Chiavi: tipo, valore, target_codice.",
            ),
        ),
    ]
