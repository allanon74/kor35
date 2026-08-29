# Generated manually: InnescoTimer broadcast_data_fine + broadcast_push_inviata

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0256_trappola_serieqr_uuid_pk"),
    ]

    operations = [
        migrations.AddField(
            model_name="innescotimer",
            name="broadcast_data_fine",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Fine countdown dell'ultima attivazione inviata a tutti i destinatari.",
                null=True,
                verbose_name="Scadenza ultimo broadcast",
            ),
        ),
        migrations.AddField(
            model_name="innescotimer",
            name="broadcast_push_inviata",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="False dopo attivazione; True dopo che il worker ha inviato le web push di scadenza.",
                verbose_name="Push scadenza già inviata",
            ),
        ),
    ]
