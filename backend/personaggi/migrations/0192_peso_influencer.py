from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0191_abilitaformularule_when_expr"),
    ]

    operations = [
        migrations.AddField(
            model_name="carica",
            name="bonus_peso_influencer",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Bonus al peso influencer InstaFame per i membri con questa carica.",
            ),
        ),
        migrations.AddField(
            model_name="personaggio",
            name="peso_influencer",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Peso base per like simulati su InstaFame (1 = minimo). Le cariche attive possono aumentarlo.",
                verbose_name="Peso influencer InstaFame",
            ),
        ),
    ]
