from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0292_staff_pool_pg"),
    ]

    operations = [
        migrations.AddField(
            model_name="personaggiopool",
            name="max_sorteggi_giorno",
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    "Tetto di attivazioni giornaliere da parte dei giocatori (giorno locale). "
                    "0 = nessuna attivazione giocatore (la tab può comparire, il pulsante resta disattivo)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="personaggiopool",
            name="statistica",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Se valorizzata e il PG ha quella statistica > 0, in area personaggio compare "
                    "una tab con il nome del pool."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pool_personaggi",
                to="personaggi.statistica",
            ),
        ),
        migrations.AddField(
            model_name="personaggiopoolsorteggio",
            name="origine",
            field=models.CharField(
                choices=[("STAFF", "Staff"), ("GIOCATORE", "Giocatore")],
                db_index=True,
                default="STAFF",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="personaggiopoolsorteggio",
            name="avviato_da_personaggio",
            field=models.ForeignKey(
                blank=True,
                help_text="Personaggio che ha lanciato l'attivazione (solo origine giocatore).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sorteggi_pool_avviati",
                to="personaggi.personaggio",
            ),
        ),
    ]
