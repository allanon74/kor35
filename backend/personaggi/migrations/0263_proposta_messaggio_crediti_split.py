# Split P2P: crediti corrente + deposito sulla stessa cessione (transazioni / messaggi)

from decimal import Decimal

from django.db import migrations, models


def _d2(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def split_legacy_importi(apps, schema_editor):
    PropostaTransazione = apps.get_model("personaggi", "PropostaTransazione")
    Messaggio = apps.get_model("personaggi", "Messaggio")

    for proposta in PropostaTransazione.objects.all().iterator():
        dare = _d2(proposta.crediti_da_dare)
        ricevere = _d2(proposta.crediti_da_ricevere)
        deposito = (proposta.conto_crediti or "CORRENTE").upper() == "DEPOSITO"
        if deposito:
            proposta.crediti_deposito_da_dare = dare
            proposta.crediti_deposito_da_ricevere = ricevere
            proposta.crediti_corrente_da_dare = Decimal("0.00")
            proposta.crediti_corrente_da_ricevere = Decimal("0.00")
        else:
            proposta.crediti_corrente_da_dare = dare
            proposta.crediti_corrente_da_ricevere = ricevere
            proposta.crediti_deposito_da_dare = Decimal("0.00")
            proposta.crediti_deposito_da_ricevere = Decimal("0.00")
        proposta.save(
            update_fields=[
                "crediti_corrente_da_dare",
                "crediti_deposito_da_dare",
                "crediti_corrente_da_ricevere",
                "crediti_deposito_da_ricevere",
            ]
        )

    for msg in Messaggio.objects.all().iterator():
        amt = _d2(msg.crediti_allegati)
        deposito = (msg.conto_crediti_allegati or "CORRENTE").upper() == "DEPOSITO"
        if deposito:
            msg.crediti_deposito_allegati = amt
            msg.crediti_corrente_allegati = Decimal("0.00")
        else:
            msg.crediti_corrente_allegati = amt
            msg.crediti_deposito_allegati = Decimal("0.00")
        msg.save(update_fields=["crediti_corrente_allegati", "crediti_deposito_allegati"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0262_negozio_voce_consegna_istanza"),
    ]

    operations = [
        migrations.AddField(
            model_name="propostatransazione",
            name="crediti_corrente_da_dare",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Crediti correnti che l'autore cede (restano correnti per il destinatario).",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="propostatransazione",
            name="crediti_deposito_da_dare",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Crediti di deposito che l'autore cede (restano deposito per il destinatario).",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="propostatransazione",
            name="crediti_corrente_da_ricevere",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Crediti correnti che l'autore si aspetta di ricevere.",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="propostatransazione",
            name="crediti_deposito_da_ricevere",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Crediti di deposito che l'autore si aspetta di ricevere.",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="messaggio",
            name="crediti_corrente_allegati",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Crediti correnti allegati (restano correnti per il destinatario).",
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name="messaggio",
            name="crediti_deposito_allegati",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Crediti di deposito allegati (restano deposito per il destinatario).",
                max_digits=12,
            ),
        ),
        migrations.AlterField(
            model_name="propostatransazione",
            name="conto_crediti",
            field=models.CharField(
                choices=[("CORRENTE", "Conto corrente"), ("DEPOSITO", "Conto di deposito")],
                db_index=True,
                default="CORRENTE",
                help_text=(
                    "Legacy: conto unico se si usa solo crediti_da_dare. "
                    "Con economia duale preferire crediti_corrente_da_dare + crediti_deposito_da_dare "
                    "(la natura dei crediti è conservata in cessione)."
                ),
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="messaggio",
            name="conto_crediti_allegati",
            field=models.CharField(
                blank=True,
                choices=[("CORRENTE", "Conto corrente"), ("DEPOSITO", "Conto di deposito")],
                default="CORRENTE",
                help_text="Legacy: conto unico di crediti_allegati. Preferire i campi split corrente/deposito.",
                max_length=16,
            ),
        ),
        migrations.RunPython(split_legacy_importi, noop_reverse),
    ]
