"""Peso social InstaFame derivato dal Prestigio (like simulati su popolazione ampia)."""

import logging
import random

from django.db.models import Sum
from django.db.utils import ProgrammingError

logger = logging.getLogger(__name__)


class RigeneraLikeInfluencerError(Exception):
    """Errore durante la rigenerazione dei like storici di un personaggio."""


def get_peso_social(personaggio):
    """Peso social usato per i like: il Prestigio del personaggio, minimo 1.

    Cariche, carriere e KORP non concorrono: il Prestigio è un punteggio
    assegnato al personaggio (staff, eventi, task).
    """
    return max(1, int(getattr(personaggio, "prestigio", None) or 0))


def random_likes_base(personaggio):
    peso = get_peso_social(personaggio)
    return random.randint(1, peso)


def compute_like_peso(liker, content_owner):
    """
    Peso statico di un singolo like:
    random(1, peso_liker) + random(1, peso_autore_post/commento).
    """
    peso_liker = get_peso_social(liker)
    peso_owner = get_peso_social(content_owner)
    return random.randint(1, peso_liker) + random.randint(1, peso_owner)


def _sum_like_peso(qs):
    return int(qs.aggregate(total=Sum("peso_like"))["total"] or 0)


def total_likes_contenuto(contenuto, exclude_like_pk=None):
    """likes_base + somma peso_like: vale per post, commenti e articoli di rubrica."""
    qs = contenuto.likes.all()
    if exclude_like_pk:
        qs = qs.exclude(pk=exclude_like_pk)
    likes_base = getattr(contenuto, "likes_base", None)
    if likes_base is None:
        likes_base = 1
    return int(likes_base or 0) + _sum_like_peso(qs)


def total_post_likes(post, exclude_like_pk=None):
    return total_likes_contenuto(post, exclude_like_pk)


def total_comment_likes(comment, exclude_like_pk=None):
    return total_likes_contenuto(comment, exclude_like_pk)


def _rigenera_post_likes_queryset(qs):
    count = 0
    for like in qs.select_related("autore", "post", "post__autore").iterator():
        like.peso_like = compute_like_peso(like.autore, like.post.autore)
        like.save(update_fields=["peso_like", "updated_at"])
        count += 1
    return count


def _rigenera_comment_likes_queryset(qs):
    from .models import SocialCommentLike

    count = 0
    for like in qs.select_related("autore", "comment", "comment__autore").iterator():
        like.peso_like = compute_like_peso(like.autore, like.comment.autore)
        like.save(update_fields=["peso_like", "updated_at"])
        count += 1
    return count


def rigenera_like_personaggio(personaggio):
    """Ricalcola i peso_like di tutti i like dati da un personaggio (post e commenti)."""
    from .models import SocialCommentLike, SocialLike

    try:
        post_count = _rigenera_post_likes_queryset(SocialLike.objects.filter(autore=personaggio))
        try:
            comment_count = _rigenera_comment_likes_queryset(
                SocialCommentLike.objects.filter(autore=personaggio)
            )
        except ProgrammingError as exc:
            logger.warning("Rigenera like commenti saltata (migrazione social mancante?): %s", exc)
            comment_count = 0
        return post_count, comment_count
    except ProgrammingError as exc:
        raise RigeneraLikeInfluencerError(
            "Migrazioni InstaFame non applicate sul server (social.0008_influencer_likes). "
            "Esegui migrate sul backend."
        ) from exc
    except Exception as exc:
        logger.exception("Rigenera like influencer fallita per personaggio %s", personaggio.pk)
        raise RigeneraLikeInfluencerError(str(exc)) from exc


def rigenera_tutti_like_instafame():
    """Ricalcola tutti i peso_like su post e commenti (operazione globale)."""
    from .models import SocialCommentLike, SocialLike

    try:
        post_count = _rigenera_post_likes_queryset(SocialLike.objects.all())
        try:
            comment_count = _rigenera_comment_likes_queryset(SocialCommentLike.objects.all())
        except ProgrammingError as exc:
            logger.warning("Rigenera like commenti saltata (migrazione social mancante?): %s", exc)
            comment_count = 0
        return post_count, comment_count
    except ProgrammingError as exc:
        raise RigeneraLikeInfluencerError(
            "Migrazioni InstaFame non applicate sul server (social.0008_influencer_likes). "
            "Esegui migrate sul backend."
        ) from exc
    except Exception as exc:
        logger.exception("Rigenera globale like influencer fallita")
        raise RigeneraLikeInfluencerError(str(exc)) from exc
