from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Rettifica cerimoniali:
    - mattoni_generici su Cerimoniale e PropostaTecnica
    - livello resta manuale (non ricalcolato); floor(mattoni/5) è solo suggerito a runtime
    """

    dependencies = [
        ('personaggi', '0269_chiamata_vocale'),
    ]

    operations = [
        migrations.AddField(
            model_name='cerimoniale',
            name='mattoni_generici',
            field=models.PositiveIntegerField(
                default=0,
                help_text="Mattoni obbligatori non legati a un'aura specifica; sommati ai componenti per il totale minimo.",
                verbose_name='Mattoni generici',
            ),
        ),
        migrations.AddField(
            model_name='propostatecnica',
            name='mattoni_generici',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Solo cerimoniali: mattoni obbligatori non specifici d\'aura, sommati ai componenti.',
                verbose_name='Mattoni generici',
            ),
        ),
    ]
