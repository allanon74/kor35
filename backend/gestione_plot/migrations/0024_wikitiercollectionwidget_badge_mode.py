from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0023_wikitiercollectionwidget_caratteristiche"),
    ]

    operations = [
        migrations.AddField(
            model_name="wikitiercollectionwidget",
            name="badge_mode",
            field=models.CharField(
                choices=[
                    ("compact", "Compatto (sigla)"),
                    ("extended", "Esteso (nome)"),
                ],
                default="compact",
                help_text="Modalita di visualizzazione badge caratteristiche sui Tier.",
                max_length=16,
            ),
        ),
    ]
