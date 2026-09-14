# Generated manually for Abilita.raddoppia_pa_da_equip (T2 Uso Armatura Extra)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0273_abilita_sblocca_creazione_livello"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilita",
            name="raddoppia_pa_da_equip",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, ogni +PA proveniente da oggetti/potenziamenti attivi viene aggiunto di nuovo (es. Uso Armatura Avanzata Extra).",
                verbose_name="Raddoppia PA da equipaggiamento",
            ),
        ),
    ]
