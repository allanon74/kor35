from django.db import migrations


def fix_defcon0_probability(apps, schema_editor):
    """
    DEFCON 0 aveva probabilita_evento_per_tick=0: a inizio viaggio (defcon=0)
    nessun evento poteva mai generarsi (deadlock fino a crash per altre cause).
    """
    StatoAllertaPilot = apps.get_model("pilotaggio", "StatoAllertaPilot")
    row = StatoAllertaPilot.objects.filter(livello=0).first()
    if row and float(row.probabilita_evento_per_tick or 0.0) <= 0.0:
        row.probabilita_evento_per_tick = 0.10
        row.save(update_fields=["probabilita_evento_per_tick", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0023_alter_eventoattivosessione_esito_guasto_ca"),
    ]

    operations = [
        migrations.RunPython(fix_defcon0_probability, migrations.RunPython.noop),
    ]
