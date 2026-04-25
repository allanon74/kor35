from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0022_wikitiercollectionwidget"),
    ]

    operations = [
        migrations.AlterField(
            model_name="wikitiercollectionwidget",
            name="tier_type_filter",
            field=models.CharField(
                choices=[
                    ("all", "Tutti i tipi"),
                    ("G0", "Tabelle Generali"),
                    ("T1", "Tier 1"),
                    ("T2", "Tier 2"),
                    ("T3", "Tier 3"),
                    ("T4", "Tier 4"),
                ],
                default="all",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="wikitiercollectionwidget",
            name="caratteristiche",
            field=models.ManyToManyField(
                blank=True,
                help_text="Filtra i Tier in base alle caratteristiche associate (se valorizzate).",
                limit_choices_to={"tipo": "CA"},
                related_name="wiki_tier_collection_widgets_caratteristiche",
                to="personaggi.punteggio",
            ),
        ),
        migrations.AddField(
            model_name="wikitiercollectionwidget",
            name="caratteristiche_filter_mode",
            field=models.CharField(
                choices=[
                    ("any", "Qualsiasi caratteristica selezionata"),
                    ("all", "Tutte le caratteristiche selezionate"),
                ],
                default="any",
                max_length=8,
            ),
        ),
    ]
