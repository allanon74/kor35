"""Chat permanente di gruppo collegata a Korp e Dipartimento."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0302_png_presenza_social"),
    ]

    operations = [
        migrations.AddField(
            model_name="gruppo",
            name="chat_permanente",
            field=models.BooleanField(
                default=False,
                help_text="Chat di Korp o Dipartimento: visibile a tutti i membri attivi, con storico condiviso.",
            ),
        ),
        migrations.AddField(
            model_name="gruppo",
            name="carriera",
            field=models.OneToOneField(
                blank=True,
                help_text="Se valorizzata, la chat di gruppo è quella permanente della Korp o del Dipartimento.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chat_gruppo",
                to="personaggi.carriera",
            ),
        ),
    ]
