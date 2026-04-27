from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("personaggi", "0157_era_difetto_nodo"),
    ]

    operations = [
        migrations.AddField(
            model_name="nodo",
            name="foto_posizione",
            field=models.ImageField(
                blank=True,
                help_text="Foto di riferimento posizione nodo (salvata in bassa risoluzione).",
                null=True,
                upload_to="nodi/",
            ),
        ),
    ]
