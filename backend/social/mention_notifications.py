"""Notifiche push e messaggi per citazioni @ su InstaFame."""

from __future__ import annotations

import logging

from django.conf import settings
from django.db.models import Q

from personaggi.models import Personaggio
from social.display_names import social_display_name

logger = logging.getLogger(__name__)

_SOURCE_LABELS = {
    "post": "un post",
    "comment": "un commento",
    "story": "una story",
}


def instafame_public_base_url() -> str:
    return (getattr(settings, "INSTAFAME_PUBLIC_BASE_URL", None) or "https://www.kor35.it").rstrip("/")


def instafame_deep_link_path(*, post_id=None, comment_id=None, story_id=None) -> str:
    params = []
    if post_id:
        params.append(f"post={int(post_id)}")
    if comment_id:
        params.append(f"comment={int(comment_id)}")
    if story_id:
        params.append(f"story={int(story_id)}")
    return f"/app/social?{'&'.join(params)}" if params else "/app/social"


def format_mention_message(citer_name: str, cited_name: str, source_kind: str) -> str:
    where = _SOURCE_LABELS.get(source_kind, "InstaFame")
    return f"{citer_name} ha citato {cited_name} in {where} di InstaFame."


def notify_instafame_mentions(citer, mentioned_ids, source_kind, *, post=None, comment=None, story=None):
    """
    Invia web push al proprietario di ogni personaggio citato (escluso auto-citazione).
    """
    if not citer or not mentioned_ids:
        return

    unique_ids = []
    seen = set()
    for raw_id in mentioned_ids:
        try:
            pid = int(raw_id)
        except (TypeError, ValueError):
            continue
        if pid in seen or pid == citer.id:
            continue
        seen.add(pid)
        unique_ids.append(pid)

    if not unique_ids:
        return

    citer_name = social_display_name(citer)
    post_id = getattr(post, "id", None) or (getattr(comment, "post_id", None) if comment else None)
    comment_id = getattr(comment, "id", None)
    story_id = getattr(story, "id", None)
    link_path = instafame_deep_link_path(post_id=post_id, comment_id=comment_id, story_id=story_id)
    push_url = f"{instafame_public_base_url()}{link_path}"

    targets = (
        Personaggio.objects.filter(id__in=unique_ids)
        .select_related("proprietario", "social_profile")
        .only("id", "nome", "proprietario_id", "proprietario__id")
    )

    try:
        from webpush import send_user_notification
    except ImportError:
        send_user_notification = None

    for target in targets:
        cited_name = social_display_name(target)
        message = format_mention_message(citer_name, cited_name, source_kind)
        user = getattr(target, "proprietario", None)
        if not user or not send_user_notification:
            continue
        try:
            send_user_notification(
                user=user,
                payload={
                    "head": "Citazione InstaFame",
                    "body": message,
                    "icon": "/pwa-192x192.png",
                    "url": push_url,
                },
                ttl=1000,
            )
        except Exception:
            logger.exception(
                "Web push citazione InstaFame fallita (citer=%s target=%s kind=%s)",
                citer.id,
                target.id,
                source_kind,
            )


def personaggi_ids_for_mention_tokens(tokens):
    """Risolve token @nome, @nickname o @123 in id personaggio."""
    if not tokens:
        return []

    explicit_ids = {int(t) for t in tokens if str(t).isdigit()}
    names = {str(t).replace("_", " ").strip() for t in tokens if not str(t).isdigit()}

    found_ids = set()
    if explicit_ids:
        found_ids.update(Personaggio.objects.filter(id__in=explicit_ids).values_list("id", flat=True))

    for nome in names:
        if not nome:
            continue
        found_ids.update(
            Personaggio.objects.filter(
                Q(nome__iexact=nome) | Q(social_profile__nickname__iexact=nome)
            ).values_list("id", flat=True)
        )

    return list(found_ids)
