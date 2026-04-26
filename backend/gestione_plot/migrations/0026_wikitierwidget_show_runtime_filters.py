from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0025_wikitiercollectionwidget_runtime_controls"),
    ]

    operations = [
        migrations.AddField(
            model_name="wikitierwidget",
            name="show_runtime_filters",
            field=models.BooleanField(
                default=False,
                help_text="Mostra filtri runtime sulle abilita del singolo Tier.",
            ),
        ),
    ]
