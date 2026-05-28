from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0182_carriera_tier_sblocco"),
    ]

    operations = [
        migrations.AddField(
            model_name="carica",
            name="bonus_crediti_evento",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Bonus crediti evento assegnato ai membri con questa carica.",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="carriera",
            name="bonus_crediti_evento",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Bonus crediti assegnato a ogni evento iniziato ai membri attivi di questa carriera/KORP.",
                max_digits=10,
                verbose_name="Bonus crediti evento",
            ),
        ),
    ]

