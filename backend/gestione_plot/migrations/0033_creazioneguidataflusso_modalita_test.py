from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0032_creazioneguidatapasso_opzioni_ui'),
    ]

    operations = [
        migrations.AddField(
            model_name='creazioneguidataflusso',
            name='modalita_test',
            field=models.BooleanField(
                default=False,
                help_text='Se attivo, il flusso è visibile solo a staff Django, superuser e ruoli campagna Staffer/Master/Head Master.',
                verbose_name='Modalità test (solo staff)',
            ),
        ),
    ]
