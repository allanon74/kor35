from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0246_mse_package_import_registry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cartegiocodefinizione",
            name="campagna",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="carte_gioco_definizioni",
                to="personaggi.campagna",
            ),
        ),
        migrations.AddConstraint(
            model_name="cartegiocodefinizione",
            constraint=models.UniqueConstraint(
                fields=("campagna", "slug"),
                name="personaggi_cgd_campagna_slug_uniq",
            ),
        ),
    ]
