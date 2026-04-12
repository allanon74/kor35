# Generated manually for CHK/CHA legacy pool linkage

from django.db import migrations, models


def set_chk_massimo_da_cha(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    Statistica.objects.filter(sigla__iexact="CHK").update(massimo_pool_sigla="CHA")


def unset_chk_massimo_da_cha(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    Statistica.objects.filter(sigla__iexact="CHK", massimo_pool_sigla__iexact="CHA").update(
        massimo_pool_sigla=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0132_alter_authgroupsyncstate_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="statistica",
            name="massimo_pool_sigla",
            field=models.CharField(
                blank=True,
                help_text="Opzionale (legacy / risorse non is_risorsa_pool). Es. CHK: imposta CHA se il tetto del "
                "pool chakra è la statistica primaria CHA mentre il contatore runtime è CHK_CUR in "
                "statistiche_temporanee. Se vuoto, il massimo è calcolato sulla stessa sigla.",
                max_length=10,
                null=True,
                verbose_name="Massimo pool da altra statistica",
            ),
        ),
        migrations.RunPython(set_chk_massimo_da_cha, unset_chk_massimo_da_cha),
    ]
