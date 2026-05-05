from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0017_evento_durata_tick"),
    ]

    operations = [
        migrations.AddField(
            model_name="sottosistemanave",
            name="capacita_carburante",
            field=models.FloatField(
                default=0.0,
                help_text="Capacita serbatoio carburante (solo tipo serbatoio).",
            ),
        ),
        migrations.AlterField(
            model_name="sottosistemanave",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("generatore", "Generatore"),
                    ("batteria", "Batteria"),
                    ("serbatoio", "Serbatoio carburante"),
                    ("motore", "Motore principale"),
                    ("portale", "Portale transdimensionale"),
                    ("manovra", "Propulsori di manovra"),
                ],
                default="standard",
                max_length=16,
            ),
        ),
    ]
