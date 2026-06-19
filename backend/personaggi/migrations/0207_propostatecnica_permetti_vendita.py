from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0206_formula_builder_selezioni"),
    ]

    operations = [
        migrations.AddField(
            model_name="propostatecnica",
            name="permetti_vendita",
            field=models.BooleanField(
                default=True,
                help_text="Se disattivato, la tecnica creata non sarà disponibile in Accademia.",
                verbose_name="Permetti la vendita",
            ),
        ),
    ]
