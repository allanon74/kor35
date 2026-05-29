import django.db.models.deletion
from django.db import migrations, models


def crea_portali_e_collega_qr(apps, schema_editor):
    NegozioMercante = apps.get_model("personaggi", "NegozioMercante")
    Portale = apps.get_model("personaggi", "NegozioMercantePortale")
    QrCode = apps.get_model("personaggi", "QrCode")

    for negozio in NegozioMercante.objects.all():
        portale, created = Portale.objects.get_or_create(
            negozio_id=negozio.pk,
            defaults={
                "nome": negozio.nome or "Negozio",
                "testo": negozio.descrizione or "",
            },
        )
        if not created:
            portale.nome = negozio.nome or portale.nome
            portale.testo = negozio.descrizione or ""
            portale.save(update_fields=["nome", "testo"])
        if negozio.qr_code_id:
            QrCode.objects.filter(pk=negozio.qr_code_id).update(vista_id=portale.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0187_negozio_mercante"),
    ]

    operations = [
        migrations.CreateModel(
            name="NegozioMercantePortale",
            fields=[
                (
                    "a_vista_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="personaggi.a_vista",
                    ),
                ),
                (
                    "negozio",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portale_avista",
                        to="personaggi.negoziomercante",
                    ),
                ),
            ],
            options={
                "verbose_name": "Portale negozio mercante",
                "verbose_name_plural": "Portali negozi mercante",
            },
            bases=("personaggi.a_vista",),
        ),
        migrations.RunPython(crea_portali_e_collega_qr, migrations.RunPython.noop),
    ]
