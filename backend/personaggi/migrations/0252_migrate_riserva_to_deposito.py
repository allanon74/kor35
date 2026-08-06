# Data migration: riserva scommesse → movimenti deposito

from decimal import Decimal

from django.db import migrations


def migrate_riserva_to_deposito(apps, schema_editor):
    Personaggio = apps.get_model("personaggi", "Personaggio")
    CreditoMovimento = apps.get_model("personaggi", "CreditoMovimento")
    for pg in Personaggio.objects.all().iterator():
        riserva = Decimal(str(pg.riserva or 0))
        if riserva <= 0:
            continue
        CreditoMovimento.objects.create(
            personaggio_id=pg.pk,
            importo=riserva,
            descrizione="Migrazione riserva scommesse → conto deposito",
            conto="DEPOSITO",
        )
        pg.riserva = Decimal("0.00")
        # updated_at può non esistere su historical model in alcuni stati
        try:
            pg.save(update_fields=["riserva", "updated_at"])
        except Exception:
            pg.save(update_fields=["riserva"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0251_economia_duale_conti"),
        ("gestione_plot", "0049_evento_trasferimento_deposito"),
    ]

    operations = [
        migrations.RunPython(migrate_riserva_to_deposito, noop_reverse),
    ]
