from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personaggi', '0216_scommesse_riserva_rename'),
    ]

    operations = [
        migrations.AddField(
            model_name='personaggio',
            name='foto_outfit',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='personaggi/costume/outfit/%Y/%m/',
                verbose_name='Foto outfit (staff)',
            ),
        ),
        migrations.AddField(
            model_name='personaggio',
            name='foto_trucco',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='personaggi/costume/trucco/%Y/%m/',
                verbose_name='Foto trucco (staff)',
            ),
        ),
    ]
