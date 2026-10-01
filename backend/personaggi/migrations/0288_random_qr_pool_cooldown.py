# Generated manually for pool QR spegnimento (cooldown stile nodi)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0287_prestito_tecniche"),
    ]

    operations = [
        migrations.AddField(
            model_name="randomqrpool",
            name="cooldown_attivo",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se True, dopo una scansione riuscita il QR fisico del pool si spegne per tutti "
                    "fino a disponibile_dal (range minuti sotto). Indipendente dall'anti-farm per PG."
                ),
            ),
        ),
        migrations.AddField(
            model_name="randomqrpool",
            name="cooldown_minuti_max",
            field=models.PositiveSmallIntegerField(
                default=25,
                help_text="Cooldown massimo (minuti) di spegnimento QR dopo scansione (se cooldown attivo).",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpool",
            name="cooldown_minuti_min",
            field=models.PositiveSmallIntegerField(
                default=5,
                help_text="Cooldown minimo (minuti) di spegnimento QR dopo scansione (se cooldown attivo).",
            ),
        ),
        migrations.AlterField(
            model_name="randomqrpool",
            name="minigioco_pattern",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Pattern estrazione minigioco a monte del pool (quale tipo/difficoltà di puzzle "
                    "giocare prima dell'effetto). Non riguarda la tabella effetti pesati. "
                    "Vuoto = legacy: tipi abilitati + difficoltà sul pool. Override per-QR via MinigiocoQrConfig."
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="random_qr_pools",
                to="personaggi.minigiocopattern",
            ),
        ),
        migrations.AddField(
            model_name="randomqrpoolmembership",
            name="disponibile_dal",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Se valorizzato e nel futuro, il QR è spento (cooldown pool) per tutti.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="randomqrpoolmembership",
            name="ultima_scansione_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
