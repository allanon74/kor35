# Guscio/Chakra/Cavaliere/Macchinista residui T2-T3

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0275_abilitastatistica_classi_oggetto_conteggio"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilita",
            name="immunita_scarica_chakra_esterna",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, variazione staff/QR negativa su CHA non può ridurre il pool "
                "(es. Chakra Avanzato Extra). Il consumo volontario del PG resta possibile.",
                verbose_name="Immunità scarica chakra esterna",
            ),
        ),
        migrations.AddField(
            model_name="abilita",
            name="consente_pesanti_una_mano",
            field=models.BooleanField(
                default=False,
                help_text="Es. Forza Straordinaria Avanzata II. Abilita regole dipendenti che richiedono questa capacità.",
                verbose_name="Consente oggetti pesanti a una mano",
            ),
        ),
        migrations.AddField(
            model_name="abilita",
            name="permette_mix_materia_mod",
            field=models.BooleanField(
                default=False,
                help_text="Es. Macchinista 1: montare una Materia su host con Mod (e viceversa) anche oltre whitelist classe.",
                verbose_name="Permette mix Materia+Mod",
            ),
        ),
        migrations.AddField(
            model_name="abilita_punteggio_dipendente",
            name="richiede_pesanti_una_mano",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, la regola vale solo se il PG ha un'abilità con consente_pesanti_una_mano "
                "(es. Cavaliere 1 → DaM da Robustezza solo con Forza Straordinaria II).",
                verbose_name="Richiede pesanti a una mano",
            ),
        ),
    ]
