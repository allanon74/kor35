from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0160_nodo_reward_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="nodorewardconfig",
            name="prob_maggiore_to_minore",
            field=models.PositiveSmallIntegerField(
                default=90,
                help_text="Probabilità % che dopo una scansione un nodo MAGGIORE diventi MINORE.",
            ),
        ),
        migrations.AddField(
            model_name="nodorewardconfig",
            name="prob_minore_to_maggiore",
            field=models.PositiveSmallIntegerField(
                default=10,
                help_text="Probabilità % che dopo una scansione un nodo MINORE diventi MAGGIORE.",
            ),
        ),
    ]
