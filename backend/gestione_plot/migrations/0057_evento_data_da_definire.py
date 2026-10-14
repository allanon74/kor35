from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0056_missione_proposta"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="data_da_definire",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo, le date restano in anagrafica per lo staff ma non compaiono "
                    "sul sito né nel calendario pubblico."
                ),
                verbose_name="Data da definire",
            ),
        ),
    ]
