from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0041_scientifica_energia_esotici"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pilotconsoleloginticket",
            name="ruolo",
            field=models.CharField(
                choices=[
                    ("navigazione", "Console Navigazione"),
                    ("ingegneria", "Console Ingegneria"),
                    ("scientifica", "Console Scientifica"),
                ],
                default="navigazione",
                help_text="Console destinataria del ticket login inverso.",
                max_length=16,
            ),
        ),
    ]
