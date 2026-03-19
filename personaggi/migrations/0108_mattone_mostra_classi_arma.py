# Generated manually: campo scelta "mostra classi arma" su Mattone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0107_alter_punteggio_tipo_archetipo_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='mattone',
            name='mostra_classi_arma',
            field=models.CharField(
                choices=[('nessuno', 'Nessuno'), ('materia', 'Mostrare i tipi di arma per Materia'), ('mod', 'Mostrare i tipi di arma per Mod')],
                default='nessuno',
                help_text='Nessuno: come ora. Materia: classi con questo castone (mattoni_materia_permessi). Mod: classi con limite mod e massimale.',
                max_length=10,
                verbose_name='Mostra classi arma nel widget',
            ),
        ),
    ]
