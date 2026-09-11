from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0264_negozio_mercante_bundle"),
    ]

    operations = [
        migrations.AddField(
            model_name="personaggio",
            name="punti_grigi",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Contatore task a allineamento grigio risolte (visibile allo staff).",
                verbose_name="Punteggio grigio",
            ),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="punti_luminosi",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Contatore task a allineamento luminoso risolte (visibile allo staff).",
                verbose_name="Punteggio luminoso",
            ),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="punti_oscuri",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Contatore task a allineamento oscuro risolte (visibile allo staff).",
                verbose_name="Punteggio oscuro",
            ),
        ),
    ]
