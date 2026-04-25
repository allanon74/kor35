from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0024_wikitiercollectionwidget_badge_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="wikitiercollectionwidget",
            name="show_characteristics_control",
            field=models.BooleanField(
                default=True,
                help_text="Mostra i filtri per caratteristiche nei controlli runtime.",
            ),
        ),
        migrations.AddField(
            model_name="wikitiercollectionwidget",
            name="show_search_control",
            field=models.BooleanField(
                default=True,
                help_text="Mostra il campo ricerca testuale nei controlli runtime.",
            ),
        ),
        migrations.AddField(
            model_name="wikitiercollectionwidget",
            name="show_sort_controls",
            field=models.BooleanField(
                default=True,
                help_text="Mostra i controlli di ordinamento nei controlli runtime.",
            ),
        ),
        migrations.AddField(
            model_name="wikitiercollectionwidget",
            name="show_tier_type_control",
            field=models.BooleanField(
                default=True,
                help_text="Mostra il filtro per tipo Tier nei controlli runtime.",
            ),
        ),
    ]
