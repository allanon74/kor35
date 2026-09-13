from django.db import migrations
from django.db.models import Sum


MATTONI_PER_LIVELLO = 5


def _livello_da_mattoni(totale):
    try:
        tot = int(totale or 0)
    except (TypeError, ValueError):
        tot = 0
    if tot < 0:
        tot = 0
    return tot // MATTONI_PER_LIVELLO


def forwards(apps, schema_editor):
    Cerimoniale = apps.get_model('personaggi', 'Cerimoniale')
    PropostaTecnica = apps.get_model('personaggi', 'PropostaTecnica')

    for cer in Cerimoniale.objects.all().iterator():
        totale = (
            cer.componenti.aggregate(tot=Sum('valore'))['tot'] or 0
        )
        nuovo = _livello_da_mattoni(totale)
        if cer.liv != nuovo:
            Cerimoniale.objects.filter(pk=cer.pk).update(liv=nuovo)

    for prop in PropostaTecnica.objects.filter(tipo='CER').iterator():
        totale = (
            prop.componenti.aggregate(tot=Sum('valore'))['tot'] or 0
        )
        nuovo = _livello_da_mattoni(totale)
        if prop.livello_proposto != nuovo:
            PropostaTecnica.objects.filter(pk=prop.pk).update(livello_proposto=nuovo)


def backwards(apps, schema_editor):
    # Non ripristiniamo i valori manuali precedenti.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0269_chiamata_vocale'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
