from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0233_programmazione_cadenza_temporale"),
    ]

    operations = [
        migrations.AddField(
            model_name="mazzoduello",
            name="leader_carta_posseduta_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="UUID CartaPosseduta Leader (Personaggio comandante, fuori dal mazzo).",
                max_length=36,
            ),
        ),
        migrations.AddField(
            model_name="duellocarte",
            name="leader_sfidante_id",
            field=models.CharField(blank=True, default="", max_length=36),
        ),
        migrations.AddField(
            model_name="duellocarte",
            name="leader_sfidato_id",
            field=models.CharField(blank=True, default="", max_length=36),
        ),
    ]
