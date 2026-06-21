from django.db import migrations, models


def _migra_durata_tick_legacy(apps, schema_editor):
    EventoNave = apps.get_model("pilotaggio", "EventoNave")
    for ev in EventoNave.objects.all().iterator():
        spec = str(ev.durata_tick or "").strip()
        if not spec.startswith("-"):
            continue
        ev.scadenza_critica = True
        if len(spec) > 1 and spec[1:].isdigit():
            ev.durata_tick = spec[1:]
        elif spec == "-":
            ev.durata_tick = "4"
        ev.save(update_fields=["scadenza_critica", "durata_tick"])


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0024_fix_defcon0_event_probability"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventonave",
            name="scadenza_critica",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo: allo scadere dei tick dell'evento applica ca_effetto. "
                    "Altrimenti l'evento termina senza fallimento critico."
                ),
            ),
        ),
        migrations.RunPython(_migra_durata_tick_legacy, migrations.RunPython.noop),
    ]
