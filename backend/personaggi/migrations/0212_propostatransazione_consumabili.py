from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0211_puntatascommessa_vincita_riscossa'),
    ]

    operations = [
        migrations.AddField(
            model_name='propostatransazione',
            name='consumabili_da_dare',
            field=models.ManyToManyField(
                blank=True,
                related_name='proposte_consumabili_dati',
                to='personaggi.consumabilepersonaggio',
            ),
        ),
        migrations.AddField(
            model_name='propostatransazione',
            name='consumabili_da_ricevere',
            field=models.ManyToManyField(
                blank=True,
                related_name='proposte_consumabili_ricevuti',
                to='personaggi.consumabilepersonaggio',
            ),
        ),
    ]
