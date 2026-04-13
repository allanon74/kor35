from django.db import migrations, models


DEFAULT_FORMULA_TEMPLATE = "{formula_type}{rango}{formula_prefix}{formula_target}"


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0135_standardizza_pool_tattici"),
    ]

    operations = [
        migrations.AlterField(
            model_name="consumabilepersonaggio",
            name="formula",
            field=models.TextField(blank=True, default=DEFAULT_FORMULA_TEMPLATE, null=True),
        ),
        migrations.AlterField(
            model_name="effettocasuale",
            name="formula",
            field=models.TextField(
                blank=True,
                default=DEFAULT_FORMULA_TEMPLATE,
                help_text="Stesso formato della descrizione. Obbligatorio se tipologia=Tessitura.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="infusione",
            name="formula_attacco",
            field=models.CharField(
                blank=True,
                default=DEFAULT_FORMULA_TEMPLATE,
                max_length=255,
                null=True,
                verbose_name="Formula Attacco",
            ),
        ),
        migrations.AlterField(
            model_name="tessitura",
            name="formula",
            field=models.TextField(blank=True, default=DEFAULT_FORMULA_TEMPLATE, null=True, verbose_name="Formula"),
        ),
    ]
