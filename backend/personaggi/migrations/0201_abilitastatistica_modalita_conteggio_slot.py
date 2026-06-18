from django.db import migrations, models


def migrate_slot_equip_counting_modes(apps, schema_editor):
    AbilitaStatistica = apps.get_model("personaggi", "AbilitaStatistica")
    for row in AbilitaStatistica.objects.filter(usa_bonus_slot_equip=True):
        per_ogg = int(getattr(row, "valore_per_oggetto_equip", 0) or 0)
        conta_pot = bool(getattr(row, "conta_potenziamenti_equip", False))
        per_pot = int(getattr(row, "valore_per_potenziamento_equip", 0) or 0)

        if conta_pot and per_ogg == 0:
            row.modalita_conteggio_slot_equip = "OGNI_POTENZIAMENTO"
            row.valore_per_unita_slot_equip = per_pot or 1
        else:
            row.modalita_conteggio_slot_equip = "TUTTI_OGGETTI"
            row.valore_per_unita_slot_equip = per_ogg or 1
        row.save(update_fields=["modalita_conteggio_slot_equip", "valore_per_unita_slot_equip"])


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0200_sport_scommesse_tipo_risultato"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilitastatistica",
            name="modalita_conteggio_slot_equip",
            field=models.CharField(
                choices=[
                    ("TUTTI_OGGETTI", "Tutti gli oggetti equipaggiati"),
                    ("OGNI_POTENZIAMENTO", "Ogni Materia/Mod installata"),
                    ("OGGETTI_MODIFICATI", "Oggetti modificati (almeno 1 MAT/MOD)"),
                ],
                default="TUTTI_OGGETTI",
                max_length=24,
                verbose_name="Modalità conteggio slot",
            ),
        ),
        migrations.AddField(
            model_name="abilitastatistica",
            name="valore_per_unita_slot_equip",
            field=models.IntegerField(
                default=1,
                help_text="Moltiplicatore applicato alla modalità di conteggio scelta.",
                verbose_name="Valore per unità",
            ),
        ),
        migrations.RunPython(migrate_slot_equip_counting_modes, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="abilitastatistica",
            name="conta_potenziamenti_equip",
        ),
        migrations.RemoveField(
            model_name="abilitastatistica",
            name="valore_per_oggetto_equip",
        ),
        migrations.RemoveField(
            model_name="abilitastatistica",
            name="valore_per_potenziamento_equip",
        ),
    ]
