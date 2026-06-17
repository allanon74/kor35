from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0197_minigioco_openverse_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="personaggio",
            name="badge_instafame",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Nessuno"),
                    ("GOLD", "Utente Gold"),
                    ("DIAMOND", "Utente Diamond"),
                    ("PREMIUM", "Utente Premium"),
                ],
                default="",
                help_text="Badge verificato mostrato nel profilo social e sotto il nome su post/storie.",
                max_length=8,
                verbose_name="Badge InstaFame",
            ),
        ),
        migrations.AddField(
            model_name="personaggiocarrieramembership",
            name="visibile_social",
            field=models.BooleanField(
                default=True,
                help_text="Se attivo, la carica compare nel profilo social InstaFame del personaggio.",
            ),
        ),
    ]
