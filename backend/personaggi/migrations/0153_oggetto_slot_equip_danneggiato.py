from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0152_campagnautente_ruolo_head_master_staffer"),
    ]

    operations = [
        migrations.AddField(
            model_name="oggetto",
            name="is_danneggiato",
            field=models.BooleanField(default=False, verbose_name="Oggetto danneggiato"),
        ),
        migrations.AddField(
            model_name="oggetto",
            name="slot_equip",
            field=models.CharField(
                blank=True,
                choices=[
                    ("head", "Testa"),
                    ("neck", "Collo"),
                    ("vest", "Veste"),
                    ("shoulders", "Spalle"),
                    ("arms", "Braccia"),
                    ("fingers", "Dita"),
                    ("feet", "Piedi"),
                    ("belt", "Cintura"),
                    ("armor", "Armatura"),
                    ("melee", "Armi in mischia"),
                    ("ranged", "Armi a distanza"),
                    ("focus", "Focus"),
                    ("shield", "Scudo"),
                ],
                help_text="Slot corporeo reale usato dagli oggetti fisici equipaggiati.",
                max_length=20,
                null=True,
            ),
        ),
    ]
