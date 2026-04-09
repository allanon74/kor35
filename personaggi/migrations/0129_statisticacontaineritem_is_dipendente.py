from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0128_merge_0125_stat_container_0127_regioni"),
    ]

    operations = [
        migrations.AddField(
            model_name="statisticacontaineritem",
            name="is_dipendente",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, questa statistica non abilita da sola la visibilita del contenitore.",
                verbose_name="Dipendente",
            ),
        ),
    ]

