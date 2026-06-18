from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0192_peso_influencer"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilitastatistica",
            name="usa_bonus_slot_equip",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, il bonus scala con oggetti fisici equipaggiati negli slot selezionati.",
                verbose_name="Bonus per slot equipaggiati",
            ),
        ),
        migrations.AddField(
            model_name="abilitastatistica",
            name="slot_equip_ammessi",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Lista slot fisici (es. melee, armor, fingers).",
                verbose_name="Slot equipaggiamento",
            ),
        ),
        migrations.AddField(
            model_name="abilitastatistica",
            name="valore_per_oggetto_equip",
            field=models.IntegerField(
                default=1,
                verbose_name="Valore per oggetto equipaggiato",
            ),
        ),
        migrations.AddField(
            model_name="abilitastatistica",
            name="conta_potenziamenti_equip",
            field=models.BooleanField(
                default=True,
                help_text="Aggiunge un bonus per ogni Materia/Mod installata su oggetti equipaggiati negli slot.",
                verbose_name="Conta potenziamenti MAT/MOD",
            ),
        ),
        migrations.AddField(
            model_name="abilitastatistica",
            name="valore_per_potenziamento_equip",
            field=models.IntegerField(
                default=1,
                verbose_name="Valore per potenziamento MAT/MOD",
            ),
        ),
    ]
