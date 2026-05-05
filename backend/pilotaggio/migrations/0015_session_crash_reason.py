from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0014_alter_eventoattivosessione_esito_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessionevolo",
            name="crash_reason",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Motivo tecnico della precipitazione (es. defcon_overflow, end_of_energy, manual_abort).",
                max_length=32,
            ),
        ),
    ]
