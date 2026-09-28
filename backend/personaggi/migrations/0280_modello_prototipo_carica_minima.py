import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0279_statistica_sct"),
    ]

    operations = [
        migrations.AddField(
            model_name="modellocontratto",
            name="prototipo",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Etichetta del tipo, per esempio talento. Più modelli possono condividerla.",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="modellocontratto",
            name="carica_minima",
            field=models.ForeignKey(
                blank=True,
                help_text="Se valorizzata, il proponente deve avere una carica con ordine maggiore o uguale.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="modelli_contratto_minimi",
                to="personaggi.carica",
            ),
        ),
    ]
