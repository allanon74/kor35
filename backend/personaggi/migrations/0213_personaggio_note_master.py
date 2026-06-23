from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0212_propostatransazione_consumabili'),
    ]

    operations = [
        migrations.AddField(
            model_name='personaggio',
            name='note_master',
            field=models.TextField(
                blank=True,
                help_text='Annotazioni visibili solo allo staff; non mostrate al giocatore.',
                null=True,
                verbose_name='Note master (interne)',
            ),
        ),
    ]
