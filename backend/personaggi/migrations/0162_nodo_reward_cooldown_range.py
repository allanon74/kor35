from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0161_nodo_reward_transition_probs"),
    ]

    operations = [
        migrations.AddField(
            model_name="nodorewardconfig",
            name="cooldown_minuti_max",
            field=models.PositiveSmallIntegerField(
                default=25,
                help_text="Cooldown massimo (minuti) dopo scansione nodo.",
            ),
        ),
        migrations.AddField(
            model_name="nodorewardconfig",
            name="cooldown_minuti_min",
            field=models.PositiveSmallIntegerField(
                default=5,
                help_text="Cooldown minimo (minuti) dopo scansione nodo.",
            ),
        ),
    ]
