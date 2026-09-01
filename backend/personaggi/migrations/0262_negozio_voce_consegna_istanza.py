from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0261_notifica_preferenze"),
    ]

    operations = [
        migrations.AddField(
            model_name="negoziomercantevoce",
            name="consegna_istanza",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se attivo su una voce Infusione, all'acquisto crea l'oggetto fisico "
                    "(Mod/Materia o Innesto/Mutazione) invece di assegnare la ricetta. "
                    "Le infusioni AUM (aumenti corporei) creano sempre un'istanza."
                ),
            ),
        ),
    ]
