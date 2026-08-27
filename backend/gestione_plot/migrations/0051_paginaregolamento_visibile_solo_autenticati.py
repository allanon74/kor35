# Generated manually: wiki visibile solo agli utenti loggati

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0050_staff_compito_calendario"),
    ]

    operations = [
        migrations.AddField(
            model_name="paginaregolamento",
            name="visibile_solo_autenticati",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, la pagina non compare nella wiki pubblica anonima: serve il login (giocatori e staff).",
                verbose_name="Visibile solo agli utenti loggati",
            ),
        ),
    ]
