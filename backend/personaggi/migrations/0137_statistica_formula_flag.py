from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0136_default_formula_template"),
    ]

    operations = [
        migrations.AddField(
            model_name="statistica",
            name="formula",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, la statistica viene proposta prima nelle liste formula.",
                verbose_name="Priorita formula",
            ),
        ),
    ]
