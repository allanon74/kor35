from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0153_oggetto_slot_equip_danneggiato"),
    ]

    operations = [
        migrations.AddField(
            model_name="tier",
            name="caratteristiche_visibili",
            field=models.ManyToManyField(
                blank=True,
                help_text="Caratteristiche associate al Tier per visualizzazione/filtri.",
                limit_choices_to={"tipo": "CA"},
                related_name="tiers_caratteristiche",
                to="personaggi.punteggio",
            ),
        ),
    ]
