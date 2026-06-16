"""Logica peso influencer InstaFame (like simulati su popolazione ampia)."""

import logging
import math
import random

from django.db.models import Sum
from django.db.utils import ProgrammingError

from personaggi.models import PersonaggioCarrieraMembership

logger = logging.getLogger(__name__)


class RigeneraLikeInfluencerError(Exception):
    """Errore durante la rigenerazione dei like storici di un personaggio."""


def get_effective_peso_influencer(personaggio):
    """Peso base del personaggio + bonus dalle cariche attive."""
    base = max(1, int(getattr(personaggio, "peso_influencer", None) or 1))
    bonus = 0
    memberships = PersonaggioCarrieraMembership.objects.filter(
        personaggio=personaggio,
        data_a__isnull=True,
    ).select_related("carica")
    for membership in memberships:
        carica = membership.carica
        if carica:
            bonus += int(getattr(carica, "bonus_peso_influencer", None) or 0)
    return max(1, base + bonus)


def random_likes_base(personaggio):
    peso = get_effective_peso_influencer(personaggio)
    return random.randint(1, peso)


def compute_like_peso(personaggio, target_total_likes):
    """
    Peso statico di un singolo like:
    random(1, peso_eff) moltiplicato per random(1, totale_like_target), /10 arrotondato per eccesso.
    """
    peso = get_effective_peso_influencer(personaggio)
    base = random.randint(1, peso)
    multiplier = random.randint(1, max(1, int(target_total_likes or 1)))
    return max(1, math.ceil(base * multiplier / 10))


def _sum_like_peso(qs):
    return int(qs.aggregate(total=Sum("peso_like"))["total"] or 0)


def total_post_likes(post, exclude_like_pk=None):
    qs = post.likes.all()
    if exclude_like_pk:
        qs = qs.exclude(pk=exclude_like_pk)
    likes_base = getattr(post, "likes_base", None)
    if likes_base is None:
        likes_base = 1
    return int(likes_base or 0) + _sum_like_peso(qs)


def total_comment_likes(comment, exclude_like_pk=None):
    qs = comment.likes.all()
    if exclude_like_pk:
        qs = qs.exclude(pk=exclude_like_pk)
    likes_base = getattr(comment, "likes_base", None)
    if likes_base is None:
        likes_base = 1
    return int(likes_base or 0) + _sum_like_peso(qs)


def _rigenera_post_likes(personaggio):
    from .models import SocialLike

    for like in SocialLike.objects.filter(autore=personaggio).select_related("post"):
        target = total_post_likes(like.post, exclude_like_pk=like.pk)
        like.peso_like = compute_like_peso(personaggio, target)
        like.save(update_fields=["peso_like", "updated_at"])


def _rigenera_comment_likes(personaggio):
    from django.apps import apps

    if not apps.is_installed("social"):
        return
    from .models import SocialCommentLike

    for like in SocialCommentLike.objects.filter(autore=personaggio).select_related("comment"):
        target = total_comment_likes(like.comment, exclude_like_pk=like.pk)
        like.peso_like = compute_like_peso(personaggio, target)
        like.save(update_fields=["peso_like", "updated_at"])


def rigenera_like_personaggio(personaggio):
    """Ricalcola i peso_like di tutti i like dati da un personaggio (post e commenti)."""
    try:
        _rigenera_post_likes(personaggio)
        try:
            _rigenera_comment_likes(personaggio)
        except ProgrammingError as exc:
            logger.warning("Rigenera like commenti saltata (migrazione social mancante?): %s", exc)
    except ProgrammingError as exc:
        raise RigeneraLikeInfluencerError(
            "Migrazioni InstaFame non applicate sul server (social.0008_influencer_likes). "
            "Esegui migrate sul backend."
        ) from exc
    except Exception as exc:
        logger.exception("Rigenera like influencer fallita per personaggio %s", personaggio.pk)
        raise RigeneraLikeInfluencerError(str(exc)) from exc
