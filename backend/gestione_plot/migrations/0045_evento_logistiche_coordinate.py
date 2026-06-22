from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0044_manualepdfpagina"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="latitudine",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name="Latitudine",
            ),
        ),
        migrations.AddField(
            model_name="evento",
            name="logistiche_pubbliche",
            field=models.TextField(
                blank=True,
                help_text="Indicazioni logistiche visibili ai giocatori (HTML).",
                verbose_name="Logistiche pubbliche",
            ),
        ),
        migrations.AddField(
            model_name="evento",
            name="longitudine",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
                verbose_name="Longitudine",
            ),
        ),
    ]
