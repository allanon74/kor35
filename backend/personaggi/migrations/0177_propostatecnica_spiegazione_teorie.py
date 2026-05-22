from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0176_synctombstone"),
    ]

    operations = [
        migrations.AddField(
            model_name="propostatecnica",
            name="spiegazione_teorie",
            field=models.TextField(
                blank=True,
                help_text="Contesto narrativo delle teorie di gioco alla base della proposta.",
                null=True,
                verbose_name="Spiegazione teorie coinvolte (in game)",
            ),
        ),
    ]
