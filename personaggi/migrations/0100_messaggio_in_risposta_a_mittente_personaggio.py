# Generated manually for conversation threading

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0099_messaggio_cancellato_staff_messaggio_letto_staff'),
    ]

    operations = [
        migrations.AddField(
            model_name='messaggio',
            name='in_risposta_a',
            field=models.ForeignKey(
                blank=True, 
                null=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                related_name='risposte', 
                to='personaggi.messaggio'
            ),
        ),
        migrations.AddField(
            model_name='messaggio',
            name='mittente_personaggio',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='messaggi_inviati_pg',
                to='personaggi.personaggio'
            ),
        ),
    ]
