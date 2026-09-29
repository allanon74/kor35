from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0045_protocollo_dipartimento_korp"),
    ]

    operations = [
        migrations.AddField(
            model_name="protocollocomunicazione",
            name="campione",
            field=models.FileField(
                blank=True,
                default="",
                help_text=(
                    "Campione audio della plancia (mp3, wav, ogg, m4a, webm), "
                    "prima della voce. Vuoto = file statico storico se c'è, altrimenti solo voce."
                ),
                upload_to="pilotaggio/allarmi/",
            ),
        ),
    ]
