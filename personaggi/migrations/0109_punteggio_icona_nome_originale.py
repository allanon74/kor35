from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0108_mattone_mostra_classi_arma'),
    ]

    operations = [
        migrations.AddField(
            model_name='punteggio',
            name='icona_nome_originale',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

