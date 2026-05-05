from django.db import migrations, models


TUNING = {
    "A": dict(gruppo="Propulsione e Manovra", tipo="manovra", coeff_produzione=4.0, coeff_consumo_energia=1.2, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1, supporta_direzioni=True),
    "B": dict(gruppo="Propulsione e Manovra", tipo="portale", coeff_produzione=0.0, coeff_consumo_energia=1.8, coeff_consumo_carburante=0.0, coeff_effetto_speciale=0.15, rampa_livelli_per_tick=1),
    "C": dict(gruppo="Propulsione e Manovra", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.6, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "D": dict(gruppo="Propulsione e Manovra", tipo="motore", coeff_produzione=12.0, coeff_consumo_energia=2.6, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "E": dict(gruppo="Difesa", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.5, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "F": dict(gruppo="Difesa", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.8, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "G": dict(gruppo="Difesa", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.3, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "H": dict(gruppo="Difesa", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.1, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "I": dict(gruppo="Difesa", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.7, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "J": dict(gruppo="Difesa", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.9, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    # Reattore principale: piu' efficiente ma con risposta lenta
    "K": dict(gruppo="Alimentazione", tipo="generatore", coeff_produzione=22.0, coeff_consumo_energia=0.0, coeff_consumo_carburante=3.2, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    # Reattore ausiliario: risposta rapida ma circa doppio consumo a parita' output
    "L": dict(gruppo="Alimentazione", tipo="generatore", coeff_produzione=20.0, coeff_consumo_energia=0.0, coeff_consumo_carburante=6.4, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=2),
    "M": dict(gruppo="Alimentazione", tipo="batteria", coeff_produzione=0.0, coeff_consumo_energia=0.0, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, capacita_storage=1400.0, coeff_ricarica_storage=0.5, rampa_livelli_per_tick=1),
    "N": dict(gruppo="Sistemi Interni", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.2, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "O": dict(gruppo="Sistemi Interni", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.4, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "P": dict(gruppo="Sistemi Interni", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.1, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "Q": dict(gruppo="Sistemi Interni", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.6, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "R": dict(gruppo="Sistemi Esotici", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.8, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "S": dict(gruppo="Sistemi Esotici", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=1.9, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
    "T": dict(gruppo="Sistemi Esotici", tipo="standard", coeff_produzione=0.0, coeff_consumo_energia=2.1, coeff_consumo_carburante=0.0, coeff_effetto_speciale=1.0, rampa_livelli_per_tick=1),
}


def apply_tuning(apps, schema_editor):
    SottosistemaNave = apps.get_model("pilotaggio", "SottosistemaNave")
    for codice, values in TUNING.items():
        row = SottosistemaNave.objects.filter(codice=codice).first()
        if not row:
            continue
        for key, value in values.items():
            setattr(row, key, value)
        row.save()


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0010_runtime_login_toggle"),
    ]

    operations = [
        migrations.AddField(
            model_name="sottosistemanave",
            name="rampa_livelli_per_tick",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Variazione massima del livello attuale per tick verso il target (solo sistemi con inerzia).",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="coeff_effetto_speciale",
            field=models.FloatField(
                default=1.0,
                help_text="Coefficiente speciale (es. portale: moltiplicatore per livello).",
            ),
        ),
        migrations.RunPython(apply_tuning, migrations.RunPython.noop),
    ]
