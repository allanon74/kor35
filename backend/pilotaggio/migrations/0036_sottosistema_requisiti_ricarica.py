from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pilotaggio", "0035_compattatore_quantico_abilitato"),
    ]

    operations = [
        migrations.AddField(
            model_name="sottosistemanave",
            name="richiede_componenti_ricarica",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo (e toggle componenti ON), QR su batteria/serbatoio operativo consuma componenti e ricarica storage/carburante.",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="requisiti_ricarica_json",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Vincoli componenti per ricarica: come riparazione + campo ricarica (unità energia o carburante).",
            ),
        ),
    ]
