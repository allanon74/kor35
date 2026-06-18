from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0201_abilitastatistica_modalita_conteggio_slot"),
    ]

    operations = [
        migrations.AddField(
            model_name="personaggio",
            name="eliminato_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Se valorizzato, il personaggio è archiviato e non compare nell'app.",
                null=True,
                verbose_name="Eliminato il",
            ),
        ),
    ]
