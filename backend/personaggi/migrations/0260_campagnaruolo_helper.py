# Generated manually: CampagnaUtente.ruolo include HELPER (Aiuto staff)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0259_minigioco_pattern_sezione_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campagnautente",
            name="ruolo",
            field=models.CharField(
                choices=[
                    ("PLAYER", "Giocatore"),
                    ("REDACTOR", "Redactor"),
                    ("HELPER", "Aiuto staff"),
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
