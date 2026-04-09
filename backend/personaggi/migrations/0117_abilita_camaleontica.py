from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0116_usersocialpreference"),
    ]

    operations = [
        migrations.AddField(
            model_name="abilita",
            name="camaleontica",
            field=models.BooleanField(
                default=False,
                help_text="Se attiva, questa forma AIN usa una forma del giorno randomica (deterministica).",
            ),
        ),
    ]
