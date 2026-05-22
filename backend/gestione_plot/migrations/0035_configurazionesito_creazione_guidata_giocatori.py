from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0034_creazioneguidataflusso_flusso_produzione'),
    ]

    operations = [
        migrations.AddField(
            model_name='configurazionesito',
            name='creazione_guidata_aperta_giocatori',
            field=models.BooleanField(
                default=False,
                help_text='Se disattivo, il pulsante creazione guidata non compare per i giocatori (staff/master possono ancora usare la sandbox test).',
                verbose_name='Creazione guidata visibile ai giocatori',
            ),
        ),
    ]
