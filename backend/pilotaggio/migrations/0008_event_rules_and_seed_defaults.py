from django.db import migrations, models


SUBSYSTEMS = [
    ("A", "Propulsori di manovra", "Propulsione e Manovra", "manovra"),
    ("B", "Portale Transdimensionale", "Propulsione e Manovra", "portale"),
    ("C", "Compensatori inerziali", "Propulsione e Manovra", "standard"),
    ("D", "Motore Principale", "Propulsione e Manovra", "motore"),
    ("E", "Deflettori", "Difesa", "standard"),
    ("F", "Occultamento", "Difesa", "standard"),
    ("G", "Point Defense", "Difesa", "standard"),
    ("H", "Contromisure", "Difesa", "standard"),
    ("I", "Siluri", "Difesa", "standard"),
    ("J", "Cannoni", "Difesa", "standard"),
    ("K", "Reattore Principale", "Alimentazione", "generatore"),
    ("L", "Reattore ausiliario", "Alimentazione", "generatore"),
    ("M", "Batterie d'emergenza", "Alimentazione", "batteria"),
    ("N", "Sistemi Gravitazionali", "Sistemi Interni", "standard"),
    ("O", "Smaltimento Calore", "Sistemi Interni", "standard"),
    ("P", "Soppressori Elettromagnetici", "Sistemi Interni", "standard"),
    ("Q", "Supporto Vitale", "Sistemi Interni", "standard"),
    ("R", "Nucleo Temporale", "Sistemi Esotici", "standard"),
    ("S", "Nucleo Dimensionale", "Sistemi Esotici", "standard"),
    ("T", "Correttore di Paradossi", "Sistemi Esotici", "standard"),
]


def seed_defaults(apps, schema_editor):
    SottosistemaNave = apps.get_model("pilotaggio", "SottosistemaNave")
    StatoAllertaPilot = apps.get_model("pilotaggio", "StatoAllertaPilot")

    for idx, (codice, nome, gruppo, tipo) in enumerate(SUBSYSTEMS, start=1):
        defaults = {
            "nome": nome,
            "gruppo": gruppo,
            "ordine": idx,
            "tipo": tipo,
            "coeff_produzione": 1.0 if tipo in ("generatore", "motore") else 0.0,
            "coeff_consumo_energia": 1.0 if tipo not in ("generatore", "batteria") else 0.0,
            "coeff_consumo_carburante": 1.0 if tipo == "generatore" else 0.0,
            "capacita_storage": 200.0 if tipo == "batteria" else 0.0,
            "supporta_direzioni": tipo == "manovra",
        }
        SottosistemaNave.objects.update_or_create(codice=codice, defaults=defaults)

    probs = {
        0: 0.0,
        1: 0.15,
        2: 0.25,
        3: 0.35,
        4: 0.50,
        5: 0.60,
        6: 0.0,
    }
    for lvl, p in probs.items():
        row = StatoAllertaPilot.objects.filter(livello=lvl).first()
        if row:
            row.probabilita_evento_per_tick = p
            row.save(update_fields=["probabilita_evento_per_tick", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0007_energy_runtime_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventonave",
            name="regole_json",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Regole avanzate evento in formato JSON (opzionale, editable da staff).",
            ),
        ),
        migrations.AddField(
            model_name="statoallertapilot",
            name="probabilita_evento_per_tick",
            field=models.FloatField(
                default=0.15,
                help_text="Probabilita' 0..1 che a ogni tick venga generato un evento (se non ce n'e' uno attivo).",
            ),
        ),
        migrations.RunPython(seed_defaults, migrations.RunPython.noop),
    ]
