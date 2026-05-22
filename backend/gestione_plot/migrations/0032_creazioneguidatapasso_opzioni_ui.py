from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0031_creazione_guidata'),
    ]

    operations = [
        migrations.AddField(
            model_name='creazioneguidatapasso',
            name='opzioni_ui',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='presentazione, gruppo_id, modalita_rewind, widget_fondo',
            ),
        ),
        migrations.AlterField(
            model_name='creazioneguidatascelta',
            name='tipo_azione',
            field=models.CharField(
                choices=[
                    ('naviga', 'Naviga verso altro passo'),
                    ('imposta_campo', 'Imposta campo personaggio'),
                    ('aggiungi_abilita', 'Aggiungi abilità suggerite'),
                    ('combo', 'Combinata (campo + abilità + navigazione da payload)'),
                    ('fine', 'Fine percorso'),
                ],
                default='naviga',
                max_length=32,
            ),
        ),
    ]
