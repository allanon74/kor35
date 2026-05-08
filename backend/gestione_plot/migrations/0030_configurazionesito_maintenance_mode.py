from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0029_paypal_ui_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionesito",
            name="maintenance_admin_note",
            field=models.TextField(
                blank=True,
                default="MODALITA MANUTENZIONE ATTIVA: non effettuare modifiche ai dati applicativi. Usare solo questa console per riattivare il sistema.",
                help_text="Avviso evidenziato in tutte le pagine Admin quando la manutenzione e attiva.",
                verbose_name="Nota visibile in Admin durante manutenzione",
            ),
        ),
        migrations.AddField(
            model_name="configurazionesito",
            name="maintenance_mode",
            field=models.BooleanField(
                default=False,
                help_text="Quando attiva, blocca l'app di gioco/social/staff/pilotaggio e lascia solo la console admin Django.",
                verbose_name="Modalita manutenzione attiva",
            ),
        ),
        migrations.AddField(
            model_name="configurazionesito",
            name="maintenance_public_message",
            field=models.TextField(
                blank=True,
                default="Sistema temporaneamente in manutenzione. Riprova tra pochi minuti.",
                help_text="Messaggio mostrato in alto nella Wiki al posto dell'accesso alla sezione gioco.",
                verbose_name="Messaggio pubblico manutenzione",
            ),
        ),
    ]
