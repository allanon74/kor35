# Generated manually: ordine colonne sistema nella console pilota.

from django.db import migrations, models


def seed_ordine_gruppo(apps, schema_editor):
    """Valori iniziali coerenti con i gruppi seed (migration 0008)."""
    SottosistemaNave = apps.get_model("pilotaggio", "SottosistemaNave")
    group_order = {
        "Propulsione e Manovra": 10,
        "Difesa": 20,
        "Alimentazione": 30,
        "Sistemi Interni": 40,
        "Sistemi Esotici": 50,
    }
    for row in SottosistemaNave.objects.all():
        g = (row.gruppo or "").strip()
        target = group_order.get(g, 0)
        if row.ordine_gruppo != target:
            row.ordine_gruppo = target
            row.save()


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0021_alter_sottosistemanave_colori_per_livello_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sottosistemanave",
            name="ordine_gruppo",
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    "Ordine della colonna 'sistema' nella console pilota. "
                    "Usa lo stesso valore per tutti i sottosistemi appartenenti allo stesso gruppo."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="sottosistemanave",
            name="ordine",
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    "Ordine dei riquadri sottosistema all'interno del gruppo nella console pilota."
                ),
            ),
        ),
        migrations.RunPython(seed_ordine_gruppo, migrations.RunPython.noop),
    ]
