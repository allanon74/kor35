# Generated manually for Abilita sblocca_creazione_livello (T3 craft unlocks)

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0272_abilitastatistica_cog_slot_conteggio"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilita",
            name="sblocca_creazione_livello",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Se valorizzato, il PG con questa abilità può creare/usare fino a questo livello nell'ambito indicato (max con il valore aura).",
                null=True,
                verbose_name="Sblocca creazione fino a livello",
            ),
        ),
        migrations.AddField(
            model_name="abilita",
            name="ambito_creazione",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "—"),
                    ("TES_AURA", "Tecniche (tessiture/proposte per aura)"),
                    ("MATERIA", "Materie (forgiatura)"),
                    ("MUTAZIONE", "Mutazioni (forgiatura)"),
                    ("MOD", "MOD / Innesti (forgiatura)"),
                    ("CONSUMABILE", "Consumabili / Alchimia"),
                ],
                default="",
                max_length=16,
                verbose_name="Ambito sblocco creazione",
            ),
        ),
        migrations.AddField(
            model_name="abilita",
            name="aura_creazione",
            field=models.ForeignKey(
                blank=True,
                help_text="Obbligatoria per ambito Tecniche: quale aura (es. Magica, Sacra) viene sbloccata.",
                limit_choices_to={"tipo": "AU"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="abilita_sblocco_creazione",
                to="personaggi.punteggio",
                verbose_name="Aura sblocco creazione",
            ),
        ),
    ]
