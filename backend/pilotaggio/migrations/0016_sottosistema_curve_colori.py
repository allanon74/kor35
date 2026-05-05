from django.db import migrations, models


def _default_curve_zero():
    return {str(i): 0.0 for i in range(10)}


def _default_curve_guasto():
    data = _default_curve_zero()
    data["7"] = 1.0
    data["8"] = 10.0
    data["9"] = 25.0
    return data


def _default_colori_livello():
    return {
        "0": "#ffffff",
        "1": "#8a2be2",
        "2": "#4b5fd1",
        "3": "#2f8cff",
        "4": "#00b894",
        "5": "#9ccc65",
        "6": "#ffd54f",
        "7": "#ffb74d",
        "8": "#ff7043",
        "9": "#ff3b30",
    }


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0015_session_crash_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="sottosistemanave",
            name="guasto_percent_per_livello",
            field=models.JSONField(
                blank=True,
                default=_default_curve_guasto,
                help_text="Probabilita' guasto in percentuale per livello 0..9 (chiavi stringa).",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="ripristino_percent_per_livello",
            field=models.JSONField(
                blank=True,
                default=_default_curve_zero,
                help_text="Probabilita' ripristino automatico in percentuale per tick per livello 0..9.",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="colori_per_livello",
            field=models.JSONField(
                blank=True,
                default=_default_colori_livello,
                help_text="Colore HEX per ogni livello 0..9 (es. {'0':'#ffffff',...}).",
            ),
        ),
    ]
