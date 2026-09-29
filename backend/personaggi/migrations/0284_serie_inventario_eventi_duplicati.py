# Inventario serie: ammetti_duplicati, eventi M2M, vincolo QR+PG

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestione_plot", "0054_missioneevento_attiva"),
        ("personaggi", "0283_random_qr_pool_claim_serie_qr_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="seriecollezione",
            name="ammetti_duplicati",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se disattivo (default), ogni indice 1..N viene consegnato una sola volta "
                    "e ogni QR fisico assegna al massimo un pezzo. Se attivo, gli indici possono "
                    "ripetersi e lo stesso QR può essere riscosso da personaggi diversi "
                    "(una volta ciascuno)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="seriecollezione",
            name="eventi",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Opzionale: se valorizzato, i pezzi in inventario serie restano visibili "
                    "solo finché almeno un evento collegato non è chiuso (ended_at vuoto)."
                ),
                related_name="serie_collezioni",
                to="gestione_plot.evento",
            ),
        ),
        migrations.AlterField(
            model_name="serieassegnazione",
            name="oggetto",
            field=models.ForeignKey(
                blank=True,
                help_text="Oggetto collegato (metadata); non va nello zaino generico.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="serie_assegnazioni",
                to="personaggi.oggetto",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="serieassegnazione",
            unique_together=set(),
        ),
        migrations.RemoveConstraint(
            model_name="serieassegnazione",
            name="uq_serie_assegnazione_qr_code",
        ),
        migrations.AddConstraint(
            model_name="serieassegnazione",
            constraint=models.UniqueConstraint(
                condition=models.Q(("qr_code__isnull", False)),
                fields=("qr_code", "personaggio"),
                name="uq_serie_assegnazione_qr_personaggio",
            ),
        ),
    ]
