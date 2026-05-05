from django.db import migrations, models


def _default_effetti_inversione():
    return {
        "tipo": "none",
        "probabilita_percent": 0.0,
        "valore": 0.0,
        "target_codice": "",
    }


def _default_effetti_espulsione():
    return {
        "tipo": "none",
        "probabilita_percent": 0.0,
        "valore": 0.0,
        "target_codice": "",
    }


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0019_sottosistema_effetti_guasto"),
    ]

    operations = [
        migrations.AddField(
            model_name="sottosistemanave",
            name="effetti_espulsione_json",
            field=models.JSONField(
                blank=True,
                default=_default_effetti_espulsione,
                help_text="Effetti percentuali quando si attiva 'espelli'.",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="effetti_inversione_json",
            field=models.JSONField(
                blank=True,
                default=_default_effetti_inversione,
                help_text="Effetti percentuali quando si attiva 'inverti'.",
            ),
        ),
    ]
