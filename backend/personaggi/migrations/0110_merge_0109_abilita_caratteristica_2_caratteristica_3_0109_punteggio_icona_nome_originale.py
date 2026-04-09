from django.db import migrations


class Migration(migrations.Migration):
    """
    Merge migration per risolvere il conflitto:
    - 0109_abilita_caratteristica_2_caratteristica_3
    - 0109_punteggio_icona_nome_originale
    
    Entrambe risultano leaf node dello stesso app label, quindi serve una
    dipendenza unificata per rendere il grafo delle migrazioni lineare.
    """

    dependencies = [
        ('personaggi', '0109_abilita_caratteristica_2_caratteristica_3'),
        ('personaggi', '0109_punteggio_icona_nome_originale'),
    ]

    operations = []

