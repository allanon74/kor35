from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0036_sottosistema_requisiti_ricarica"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessionevolo",
            name="allarme_equipaggio",
            field=models.CharField(
                db_index=True,
                default="crociera",
                help_text="Allarme equipaggio manuale (Giallo/Rosso/Nero/Blu) o crociera.",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="allarme_equipaggio_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Ultimo cambio allarme equipaggio (sync LED WiFi).",
                null=True,
            ),
        ),
    ]
