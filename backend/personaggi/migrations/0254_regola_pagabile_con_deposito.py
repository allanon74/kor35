# Generated manually for economia duale + regole transazioni

import uuid

from django.db import migrations, models


def forwards_pagabile_e_negozio(apps, schema_editor):
    Regola = apps.get_model("personaggi", "RegolaTransazioneCategoria")
    Campagna = apps.get_model("personaggi", "Campagna")

    default_pagabili = {
        "oggetti",
        "materia",
        "consumabili",
        "mod",
        "innesti",
        "mutazioni",
        "negozio",
    }
    eco_to_regola = {
        "oggetto": "oggetti",
        "materia": "materia",
        "consumabile": "consumabili",
        "negozio": "negozio",
    }

    for campagna in Campagna.objects.all():
        raw = campagna.economia_config if isinstance(campagna.economia_config, dict) else {}
        cats = raw.get("categorie_spesa_deposito")
        wanted = None
        if isinstance(cats, list):
            wanted = set()
            for c in cats:
                key = str(c).strip().lower()
                codice = eco_to_regola.get(key, key)
                wanted.add(codice)

        for regola in Regola.objects.filter(campagna_id=campagna.pk):
            if wanted is not None and regola.codice in eco_to_regola.values():
                regola.pagabile_con_deposito = regola.codice in wanted
            else:
                regola.pagabile_con_deposito = regola.codice in default_pagabili
            regola.save(update_fields=["pagabile_con_deposito", "updated_at"])

        if not Regola.objects.filter(campagna_id=campagna.pk, codice="negozio").exists():
            pagabile = True if wanted is None else ("negozio" in wanted)
            Regola.objects.create(
                sync_id=uuid.uuid4(),
                campagna_id=campagna.pk,
                codice="negozio",
                nome="Negozi / mercanti NPC",
                ordine=100,
                vendibile_giocatori=False,
                requisiti_gruppo={},
                pagabile_con_deposito=pagabile,
            )


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0253_proposta_messaggio_conto_crediti"),
    ]

    operations = [
        migrations.AddField(
            model_name="regolatransazionecategoria",
            name="pagabile_con_deposito",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo (e modulo conto deposito ON), acquisti di questa categoria "
                    "possono usare il conto deposito / crediti di investimento (prezzo con fattore)."
                ),
                verbose_name="Pagabile con crediti di deposito",
            ),
        ),
        migrations.AlterField(
            model_name="regolatransazionecategoria",
            name="codice",
            field=models.CharField(
                choices=[
                    ("crediti", "Crediti"),
                    ("oggetti", "Oggetti"),
                    ("materia", "Materia"),
                    ("mod", "Mod"),
                    ("consumabili", "Consumabili"),
                    ("innesti", "Innesti"),
                    ("mutazioni", "Mutazioni"),
                    ("infusioni", "Infusioni"),
                    ("tessiture", "Tessiture"),
                    ("cerimoniali", "Cerimoniali"),
                    ("negozio", "Negozi / mercanti NPC"),
                ],
                max_length=32,
            ),
        ),
        migrations.RunPython(forwards_pagabile_e_negozio, backwards_noop),
    ]
