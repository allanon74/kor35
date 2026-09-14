from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0271_merge_0270_cerimoniale_fcm"),
    ]

    operations = [
        migrations.AlterField(
            model_name="abilitastatistica",
            name="modalita_conteggio_slot_equip",
            field=models.CharField(
                choices=[
                    ("TUTTI_OGGETTI", "Tutti gli oggetti equipaggiati"),
                    ("OGNI_POTENZIAMENTO", "Ogni Materia/Mod installata"),
                    ("OGGETTI_MODIFICATI", "Oggetti modificati (almeno 1 MAT/MOD)"),
                    ("COG_OCCUPATI", "Slot COG occupati"),
                    ("COG_VUOTI", "Slot COG vuoti"),
                ],
                default="TUTTI_OGGETTI",
                max_length=24,
                verbose_name="Modalità conteggio slot",
            ),
        ),
    ]
