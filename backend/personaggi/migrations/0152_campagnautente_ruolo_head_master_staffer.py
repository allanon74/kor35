from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0151_remove_campagnafeaturepolicy_camp_feat_unique_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campagnautente",
            name="ruolo",
            field=models.CharField(
                choices=[
                    ("PLAYER", "Giocatore"),
                    ("STAFFER", "Staffer"),
                    ("MASTER", "Master"),
                    ("HEAD_MASTER", "Head Master"),
                ],
                db_index=True,
                default="PLAYER",
                max_length=16,
            ),
        ),
    ]
