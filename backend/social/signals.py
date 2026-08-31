from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .mention_tags import sync_comment_tags, sync_post_tags, sync_story_tags
from .models import SocialComment, SocialPost, SocialStory
from .models_rubriche import Rubrica, RubricaArticolo, RubricaArticoloImmagine
from .rubriche_wiki import rimuovi_pagine_wiki_rubrica, sync_rubrica_to_wiki_safe


@receiver(post_save, sender=SocialPost)
def social_post_sync_mention_tags(sender, instance: SocialPost, **kwargs):
    sync_post_tags(instance)


@receiver(post_save, sender=SocialComment)
def social_comment_sync_mention_tags(sender, instance: SocialComment, **kwargs):
    sync_comment_tags(instance)


@receiver(post_save, sender=SocialStory)
def social_story_sync_mention_tags(sender, instance: SocialStory, **kwargs):
    sync_story_tags(instance)


def _rigenera_wiki(rubrica):
    if not rubrica:
        return
    transaction.on_commit(lambda: sync_rubrica_to_wiki_safe(rubrica))


@receiver(post_save, sender=Rubrica)
def rubrica_aggiorna_wiki(sender, instance: Rubrica, **kwargs):
    _rigenera_wiki(instance)


@receiver(post_delete, sender=Rubrica)
def rubrica_rimuovi_wiki(sender, instance: Rubrica, **kwargs):
    """Senza questo le pagine generate resterebbero orfane nel menu wiki."""
    transaction.on_commit(lambda: rimuovi_pagine_wiki_rubrica(instance))


@receiver(post_save, sender=RubricaArticolo)
@receiver(post_delete, sender=RubricaArticolo)
def articolo_aggiorna_wiki(sender, instance: RubricaArticolo, **kwargs):
    if not instance.rubrica_id:
        return
    # In cascata dalla delete della rubrica il genitore non esiste più: se ne occupa
    # rubrica_rimuovi_wiki.
    rubrica = Rubrica.objects.filter(pk=instance.rubrica_id).first()
    _rigenera_wiki(rubrica)


@receiver(post_save, sender=RubricaArticoloImmagine)
@receiver(post_delete, sender=RubricaArticoloImmagine)
def immagine_articolo_aggiorna_wiki(sender, instance: RubricaArticoloImmagine, **kwargs):
    articolo = instance.articolo if instance.articolo_id else None
    _rigenera_wiki(articolo.rubrica if articolo and articolo.rubrica_id else None)
