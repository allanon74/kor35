from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0169_oggetto_slot_fisici_possibili"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilita",
            name="nascondi_in_scheda_abilita",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, questa abilità non viene mostrata nella tab Abilità ma i suoi effetti restano applicati.",
                verbose_name='Nascondi nella scheda "Abilità"',
            ),
        ),
    ]
