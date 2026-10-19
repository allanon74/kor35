"""Notifiche push e messaggi per citazioni @ su InstaFame."""

from __future__ import annotations

import logging

from django.db.models import Q

from personaggi.models import Personaggio
from social.display_names import social_display_name

logger = logging.getLogger(__name__)

_SOURCE_LABELS = {
    "post": "un post",
    "comment": "un commento",
    "story": "una story",
    "articolo": "un articolo",
    "commento_rubrica": "un commento di rubrica",
}


def rubrica_deep_link_path(*, articolo_id=None, comment_id=None) -> str:
    """Path relativo verso un articolo di rubrica (e, se serve, un commento)."""
    params = []
    if articolo_id:
        params.append(f"articolo={articolo_id}")
    if comment_id:
        params.append(f"commento={comment_id}")
    return f"/app/social?{'&'.join(params)}" if params else "/app/social?vista=rubriche"


def instafame_deep_link_path(*, post_id=None, comment_id=None, story_id=None) -> str:
    """Path relativo per Web Push (edge/mirror/www senza host assoluto)."""
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


def notify_instafame_mentions(
    citer,
    mentioned_ids,
    source_kind,
    *,
    post=None,
    comment=None,
    story=None,
    articolo=None,
    commento_rubrica=None,
):
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
    if articolo is not None or commento_rubrica is not None:
        articolo_ref = articolo or getattr(commento_rubrica, "articolo", None)
        push_url = rubrica_deep_link_path(
            articolo_id=getattr(articolo_ref, "id", None),
            comment_id=getattr(commento_rubrica, "id", None),
        )
    else:
        post_id = getattr(post, "id", None) or (getattr(comment, "post_id", None) if comment else None)
        comment_id = getattr(comment, "id", None)
        story_id = getattr(story, "id", None)
        push_url = instafame_deep_link_path(post_id=post_id, comment_id=comment_id, story_id=story_id)

    targets = (
        Personaggio.objects.filter(id__in=unique_ids)
        .select_related("proprietario", "social_profile")
        .only("id", "nome", "proprietario_id", "proprietario__id")
    )

    for target in targets:
        cited_name = social_display_name(target)
        message = format_mention_message(citer_name, cited_name, source_kind)
        user = getattr(target, "proprietario", None)
        if not user:
            continue
        try:
            from personaggi.notify import notify_user

            notify_user(
                user,
                category="social",
                head="Citazione InstaFame",
                body=message,
                url=push_url,
            )
        except Exception:
            logger.exception(
                "Notifica citazione InstaFame fallita (citer=%s target=%s kind=%s)",
                citer.id,
                target.id,
                source_kind,
            )


def notify_rubrica_comment_author(commento) -> None:
    """Push allo scrittore dell'articolo quando arriva un commento di un altro giocatore."""
    from .mention_tags import mention_notify_suppressed

    if mention_notify_suppressed() or not commento:
        return

    from .models_rubriche import RubricaArticoloComment

    commento = (
        RubricaArticoloComment.objects.select_related(
            "autore",
            "autore__social_profile",
            "autore__proprietario",
            "articolo",
            "articolo__autore_personaggio",
            "articolo__autore_personaggio__proprietario",
            "articolo__autore_personaggio__social_profile",
        )
        .filter(pk=commento.pk)
        .first()
    )
    if not commento or not commento.articolo_id:
        return
    autore = commento.articolo.autore_personaggio
    if not autore or autore.id == commento.autore_id:
        return
    if autore.proprietario_id and autore.proprietario_id == commento.autore.proprietario_id:
        return
    user = getattr(autore, "proprietario", None)
    if not user:
        return

    citer_name = social_display_name(commento.autore)
    titolo = commento.articolo.titolo or "un articolo"
    estratto = (commento.testo or "").strip().replace("\n", " ")
    if len(estratto) > 140:
        estratto = estratto[:137] + "…"
    body = f"{citer_name} ha commentato il tuo articolo «{titolo}»."
    if estratto:
        body = f"{body} {estratto}"
    try:
        from personaggi.notify import notify_user

        notify_user(
            user,
            category="social",
            head="Commento InstaFame",
            body=body,
            url=rubrica_deep_link_path(articolo_id=commento.articolo_id, comment_id=commento.id),
        )
    except Exception:
        logger.exception(
            "Notifica commento rubrica fallita (commento=%s autore=%s)",
            commento.id,
            autore.id,
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

    from personaggi.png_presenza_social import CAMPO_TAG, filtra_ids_funzione

    return filtra_ids_funzione(found_ids, CAMPO_TAG)
