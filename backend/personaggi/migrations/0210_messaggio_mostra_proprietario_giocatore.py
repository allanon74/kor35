from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0209_minigioco_sezione_accesso'),
    ]

    operations = [
        migrations.AddField(
            model_name='messaggio',
            name='mostra_proprietario_giocatore',
            field=models.BooleanField(
                default=True,
                help_text="Se attivo, il destinatario vede anche l'identità del giocatore proprietario del personaggio mittente.",
            ),
        ),
    ]
