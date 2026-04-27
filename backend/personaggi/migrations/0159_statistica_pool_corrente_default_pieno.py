# Generated manually: pool nodi vs Fortuna (contatore assente)

from django.db import migrations, models


def _set_nodo_pools_non_pieni(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    for sigla in ("TEO", "SIW", "ROT", "AST", "MUT", "AVA"):
        Statistica.objects.filter(sigla=sigla, is_risorsa_pool=True).update(
            pool_corrente_default_pieno_se_assente=False
        )


def _noop_reverse(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    for sigla in ("TEO", "SIW", "ROT", "AST", "MUT", "AVA"):
        Statistica.objects.filter(sigla=sigla, is_risorsa_pool=True).update(
            pool_corrente_default_pieno_se_assente=True
        )


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0158_nodo_foto_posizione"),
    ]

    operations = [
        migrations.AddField(
            model_name="statistica",
            name="pool_corrente_default_pieno_se_assente",
            field=models.BooleanField(
                default=True,
                help_text="Se vero, senza valore salvato in risorse_consumabili il contatore coincide col massimo di scheda "
                "(tipico Fortuna: aumenti la stat e ti ritieni al completo). Se falso (Teoforia, Rottami, nodi, …), "
                "senza valore salvato il contatore è 0; solo ricompense/consumi/staff alzano il corrente; alzare solo il max "
                "da abilità non riempie il pool.",
                verbose_name="Pool: assente = pieno (come Fortuna)",
            ),
        ),
        migrations.RunPython(_set_nodo_pools_non_pieni, _noop_reverse),
    ]
