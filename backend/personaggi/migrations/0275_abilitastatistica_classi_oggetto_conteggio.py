# Generated manually: AbilitaStatistica.classi_oggetto_conteggio (Gladiatore 2)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0274_abilita_raddoppia_pa_da_equip"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilitastatistica",
            name="classi_oggetto_conteggio",
            field=models.ManyToManyField(
                blank=True,
                help_text="Se valorizzato, conta solo oggetti equipaggiati di queste classi (es. Spada/Bastone per Gladiatore). Combinabile con gli slot.",
                related_name="abilita_statistiche_conteggio",
                to="personaggi.classeoggetto",
                verbose_name="Classi oggetto (conteggio)",
            ),
        ),
    ]
