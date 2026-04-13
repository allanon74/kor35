from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0140_alter_statistica_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="statistica",
            name="formula",
            field=models.BooleanField(
                default=False,
                help_text="Indica le statistiche usate soprattutto nelle formule: nei pivot (es. statistiche_base) vengono mostrate prima.",
                verbose_name="Formula",
            ),
        ),
    ]
