import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0033_creazioneguidataflusso_modalita_test'),
    ]

    operations = [
        migrations.AddField(
            model_name='creazioneguidataflusso',
            name='flusso_produzione',
            field=models.ForeignKey(
                blank=True,
                help_text='Per flussi in modalità test: flusso di produzione su cui pubblicare le modifiche.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sandbox_test',
                to='gestione_plot.creazioneguidataflusso',
            ),
        ),
        migrations.AddConstraint(
            model_name='creazioneguidataflusso',
            constraint=models.UniqueConstraint(
                condition=models.Q(('modalita_test', True), ('flusso_produzione__isnull', False)),
                fields=('flusso_produzione',),
                name='uniq_sandbox_test_per_produzione',
            ),
        ),
    ]
