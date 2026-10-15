from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0057_evento_data_da_definire"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="archiviato_at",
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    "Se valorizzato, il plot è in archivio: lo staff lo consulta in sola lettura "
                    "e non compare più tra gli eventi live o le iscrizioni."
                ),
                null=True,
                verbose_name="Archiviato il",
            ),
        ),
    ]
