from django.db import migrations, models


def imposta_creazione_guidata_spenta(apps, schema_editor):
    ConfigurazioneSito = apps.get_model('gestione_plot', 'ConfigurazioneSito')
    ConfigurazioneSito.objects.update(creazione_guidata_aperta_giocatori=False)


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0035_configurazionesito_creazione_guidata_giocatori'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configurazionesito',
            name='creazione_guidata_aperta_giocatori',
            field=models.BooleanField(
                default=False,
                help_text='Se disattivo, il pulsante creazione guidata non compare per i giocatori (staff/master possono ancora usare la sandbox test).',
                verbose_name='Creazione guidata visibile ai giocatori',
            ),
        ),
        migrations.RunPython(imposta_creazione_guidata_spenta, migrations.RunPython.noop),
    ]
