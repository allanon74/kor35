import django.db.models.deletion
import django.utils.timezone
import social.models_rubriche
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestione_plot', '0051_paginaregolamento_visibile_solo_autenticati'),
        ('personaggi', '0261_notifica_preferenze'),
        ('social', '0011_alter_socialprofile_nickname'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Rubrica',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=160)),
                ('slug', models.SlugField(blank=True, max_length=80, unique=True)),
                ('sottotitolo', models.CharField(blank=True, max_length=200)),
                ('descrizione', models.TextField(blank=True)),
                ('logo', models.ImageField(blank=True, null=True, upload_to=social.models_rubriche.rubrica_logo_upload_to)),
                ('colore_accento', models.CharField(default='#b91c1c', help_text='Colore esadecimale usato per occhielli e bordi della rubrica.', max_length=9)),
                ('attiva', models.BooleanField(default=True)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('pubblica_in_wiki', models.BooleanField(default=False)),
                ('wiki_titolo', models.CharField(blank=True, max_length=200)),
                ('wiki_ordine', models.PositiveIntegerField(default=0)),
                ('wiki_visibilita', models.CharField(choices=[('PUBBLICA', 'Visibile a tutti'), ('AUTENTICATI', 'Solo utenti autenticati')], default='AUTENTICATI', max_length=16)),
                ('creata_da', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rubriche_create', to=settings.AUTH_USER_MODEL)),
                ('wiki_pagina', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rubrica_generata', to='gestione_plot.paginaregolamento')),
                ('wiki_parent', models.ForeignKey(blank=True, help_text='Pagina wiki sotto cui pubblicare la rubrica.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rubriche_ospitate', to='gestione_plot.paginaregolamento')),
            ],
            options={
                'verbose_name': 'Rubrica',
                'verbose_name_plural': 'Rubriche',
                'ordering': ['ordine', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='RubricaArticolo',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('slug', models.SlugField(blank=True, max_length=80)),
                ('stato', models.CharField(choices=[('BOZZA', 'Bozza'), ('PUBBLICATO', 'Pubblicato'), ('ARCHIVIATO', 'Archiviato')], default='BOZZA', max_length=12)),
                ('occhiello', models.CharField(blank=True, max_length=120)),
                ('titolo', models.CharField(max_length=200)),
                ('sottotitolo', models.CharField(blank=True, max_length=300)),
                ('sommario', models.TextField(blank=True)),
                ('corpo', models.TextField(blank=True, help_text="HTML dell'articolo (editor wiki).")),
                ('hero_immagine', models.ImageField(blank=True, null=True, upload_to=social.models_rubriche.rubrica_articolo_hero_upload_to)),
                ('hero_didascalia', models.CharField(blank=True, max_length=300)),
                ('video', models.FileField(blank=True, null=True, upload_to=social.models_rubriche.rubrica_articolo_hero_upload_to)),
                ('firma_libera', models.CharField(blank=True, help_text="Nome di penna usato quando l'articolo non è firmato da un personaggio.", max_length=160)),
                ('data_pubblicazione', models.DateTimeField(blank=True, null=True)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('tempo_lettura_min', models.PositiveSmallIntegerField(default=1)),
                ('likes_base', models.PositiveIntegerField(default=1, help_text='Like iniziali simulati (statici) alla pubblicazione.')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('autore_personaggio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articoli_rubrica', to='personaggi.personaggio')),
                ('creato_da_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articoli_rubrica_creati', to=settings.AUTH_USER_MODEL)),
                ('evento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articoli_rubrica', to='gestione_plot.evento')),
                ('post_annuncio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articolo_annunciato', to='social.socialpost')),
                ('rubrica', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='articoli', to='social.rubrica')),
            ],
            options={
                'verbose_name': 'Articolo rubrica',
                'verbose_name_plural': 'Articoli rubrica',
                'ordering': ['-data_pubblicazione', '-created_at', '-id'],
                'unique_together': {('rubrica', 'slug')},
            },
        ),
        migrations.AddField(
            model_name='socialpost',
            name='articolo_collegato',
            field=models.ForeignKey(blank=True, help_text='Articolo di rubrica linkato dal post (card anteprima nel feed).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='post_collegati', to='social.rubricaarticolo'),
        ),
        migrations.CreateModel(
            name='RubricaArticoloComment',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('testo', models.TextField()),
                ('likes_base', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('articolo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='social.rubricaarticolo')),
                ('autore', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rubrica_articolo_comments', to='personaggi.personaggio')),
                ('evento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rubrica_articolo_comments', to='gestione_plot.evento')),
            ],
            options={
                'verbose_name': 'Commento articolo rubrica',
                'verbose_name_plural': 'Commenti articoli rubrica',
                'ordering': ['created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='RubricaArticoloCommentLike',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('peso_like', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('autore', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rubrica_commento_likes', to='personaggi.personaggio')),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='social.rubricaarticolocomment')),
            ],
            options={
                'verbose_name': 'Like commento articolo rubrica',
                'verbose_name_plural': 'Like commenti articoli rubrica',
                'ordering': ['-created_at', '-id'],
                'unique_together': {('comment', 'autore')},
            },
        ),
        migrations.CreateModel(
            name='RubricaArticoloImmagine',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('immagine', models.ImageField(upload_to=social.models_rubriche.rubrica_articolo_gallery_upload_to)),
                ('didascalia', models.CharField(blank=True, max_length=300)),
                ('ordine', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('articolo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='immagini', to='social.rubricaarticolo')),
            ],
            options={
                'verbose_name': 'Immagine articolo rubrica',
                'verbose_name_plural': 'Immagini articoli rubrica',
                'ordering': ['ordine', 'id'],
                'unique_together': {('articolo', 'ordine')},
            },
        ),
        migrations.CreateModel(
            name='RubricaArticoloLike',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('peso_like', models.PositiveIntegerField(default=1, help_text='Peso statico del like (simulazione popolazione).')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('articolo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='social.rubricaarticolo')),
                ('autore', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rubrica_articolo_likes', to='personaggi.personaggio')),
            ],
            options={
                'verbose_name': 'Like articolo rubrica',
                'verbose_name_plural': 'Like articoli rubrica',
                'ordering': ['-created_at', '-id'],
                'unique_together': {('articolo', 'autore')},
            },
        ),
        migrations.CreateModel(
            name='RubricaPermessoScrittura',
            fields=[
                ('sync_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('attivo', models.BooleanField(default=True)),
                ('note', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('concesso_da', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='permessi_rubriche_concessi', to=settings.AUTH_USER_MODEL)),
                ('personaggio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permessi_rubriche', to='personaggi.personaggio')),
                ('rubrica', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='permessi_scrittura', to='social.rubrica')),
            ],
            options={
                'verbose_name': 'Permesso scrittura rubrica',
                'verbose_name_plural': 'Permessi scrittura rubriche',
                'ordering': ['rubrica__nome', 'personaggio__nome'],
                'unique_together': {('rubrica', 'personaggio')},
            },
        ),
    ]
