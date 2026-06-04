# Generated manually: memorizza costi effettivi pagati su pivot acquisto/revoca

from datetime import timedelta
from decimal import Decimal

from django.db import migrations, models


def _importo_credito(mov):
    if mov and mov.importo < 0:
        return -mov.importo
    return None


def _backfill_costi_pagati(apps, schema_editor):
    CreditoMovimento = apps.get_model("personaggi", "CreditoMovimento")
    PuntiCaratteristicaMovimento = apps.get_model("personaggi", "PuntiCaratteristicaMovimento")
    PersonaggioAbilita = apps.get_model("personaggi", "PersonaggioAbilita")
    PersonaggioInfusione = apps.get_model("personaggi", "PersonaggioInfusione")
    PersonaggioTessitura = apps.get_model("personaggi", "PersonaggioTessitura")
    PersonaggioCerimoniale = apps.get_model("personaggi", "PersonaggioCerimoniale")
    Abilita = apps.get_model("personaggi", "Abilita")
    Infusione = apps.get_model("personaggi", "Infusione")
    Tessitura = apps.get_model("personaggi", "Tessitura")
    Cerimoniale = apps.get_model("personaggi", "Cerimoniale")

    finestra = timedelta(hours=24)

    def credito_pagato(personaggio_id, desc_exact, desc_prefix, acquired_at):
        qs = CreditoMovimento.objects.filter(personaggio_id=personaggio_id, importo__lt=0)
        if desc_exact:
            qs = qs.filter(descrizione=desc_exact)
        elif desc_prefix:
            qs = qs.filter(descrizione__startswith=desc_prefix)
        if acquired_at:
            qs = qs.filter(
                data__gte=acquired_at - finestra,
                data__lte=acquired_at + finestra,
            )
        mov = qs.order_by("-data").first()
        return _importo_credito(mov)

    for pivot in PersonaggioAbilita.objects.select_related("abilita").iterator():
        ab = pivot.abilita
        if not ab:
            continue
        cr = credito_pagato(
            pivot.personaggio_id,
            None,
            f"Acquisito abilità: {ab.nome}",
            pivot.data_acquisizione,
        )
        if cr is None:
            cr = Decimal(ab.costo_crediti or 0)
        pc_mov = PuntiCaratteristicaMovimento.objects.filter(
            personaggio_id=pivot.personaggio_id,
            descrizione__startswith=f"Acquisito abilità: {ab.nome}",
            importo__lt=0,
        )
        if pivot.data_acquisizione:
            pc_mov = pc_mov.filter(
                data__gte=pivot.data_acquisizione - finestra,
                data__lte=pivot.data_acquisizione + finestra,
            )
        pc_mov = pc_mov.order_by("-data").first()
        pc = int(-pc_mov.importo) if pc_mov and pc_mov.importo < 0 else int(ab.costo_pc or 0)
        PersonaggioAbilita.objects.filter(pk=pivot.pk).update(
            costo_crediti_pagato=cr,
            costo_pc_pagato=pc,
        )

    for Model, fk, prefix, Catalog in (
        (PersonaggioInfusione, "infusione", "Acquisito infusione", Infusione),
        (PersonaggioTessitura, "tessitura", "Acquisito tessitura", Tessitura),
        (PersonaggioCerimoniale, "cerimoniale", "Appreso cerimoniale", Cerimoniale),
    ):
        for pivot in Model.objects.iterator():
            item_id = getattr(pivot, f"{fk}_id")
            item = Catalog.objects.filter(pk=item_id).first()
            nome = item.nome if item else ""
            cr = credito_pagato(
                pivot.personaggio_id,
                f"{prefix}: {nome}",
                None,
                pivot.data_acquisizione,
            )
            if cr is None and item:
                cr = Decimal(item.costo_crediti or 0)
            elif cr is None:
                cr = Decimal(0)
            Model.objects.filter(pk=pivot.pk).update(costo_crediti_pagato=cr)


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0184_qrcode_stl_creato"),
    ]

    operations = [
        migrations.AddField(
            model_name="personaggioabilita",
            name="costo_pc_pagato",
            field=models.IntegerField(
                default=0,
                help_text="Usato per il rimborso in revoca (valore effettivo pagato).",
                verbose_name="PC pagati all'acquisto",
            ),
        ),
        migrations.AddField(
            model_name="personaggioabilita",
            name="costo_crediti_pagato",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Usato per il rimborso in revoca (valore effettivo pagato).",
                max_digits=10,
                verbose_name="Crediti pagati all'acquisto",
            ),
        ),
        migrations.AddField(
            model_name="personaggioinfusione",
            name="costo_crediti_pagato",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Usato per il rimborso in revoca (valore effettivo pagato).",
                max_digits=10,
                verbose_name="Crediti pagati all'acquisto",
            ),
        ),
        migrations.AddField(
            model_name="personaggiotessitura",
            name="costo_crediti_pagato",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Usato per il rimborso in revoca (valore effettivo pagato).",
                max_digits=10,
                verbose_name="Crediti pagati all'acquisto",
            ),
        ),
        migrations.AddField(
            model_name="personaggiocerimoniale",
            name="costo_crediti_pagato",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Usato per il rimborso in revoca (valore effettivo pagato).",
                max_digits=10,
                verbose_name="Crediti pagati all'acquisto",
            ),
        ),
        migrations.RunPython(_backfill_costi_pagati, migrations.RunPython.noop),
    ]
