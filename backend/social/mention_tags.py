"""Sincronizza tag @mention (SocialPostTag, …) dal testo e notifiche citazione."""

from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from typing import Iterator

from .models import (
    SocialComment,
    SocialCommentTag,
    SocialPost,
    SocialPostTag,
    SocialStory,
    SocialStoryTag,
    extract_mentioned_personaggi_ids,
)

MENTION_IN_TEXT_REGEX = re.compile(r"@([A-Za-z0-9_]+)")

_mention_notify_state = threading.local()


@contextmanager
def suppress_mention_notify() -> Iterator[None]:
    """Disattiva notifiche push citazione (edge sync, repair batch)."""
    prev = getattr(_mention_notify_state, "suppressed", False)
    _mention_notify_state.suppressed = True
    try:
        yield
    finally:
        _mention_notify_state.suppressed = prev


def mention_notify_suppressed() -> bool:
    return bool(getattr(_mention_notify_state, "suppressed", False))


def _should_notify(notify: bool | None) -> bool:
    if mention_notify_suppressed():
        return False
    if notify is None:
        return True
    return bool(notify)


def sync_post_tags(post: SocialPost, *, notify: bool | None = None) -> list[int]:
    """Allinea SocialPostTag a titolo+testo; ritorna i personaggio_id appena aggiunti."""
    text = f"{post.titolo or ''}\n{post.testo or ''}".strip()
    ids = extract_mentioned_personaggi_ids(text)
    existing = set(SocialPostTag.objects.filter(post=post).values_list("personaggio_id", flat=True))
    new_ids = [pid for pid in ids if pid not in existing]
    SocialPostTag.objects.filter(post=post).exclude(personaggio_id__in=ids).delete()
    if new_ids:
        SocialPostTag.objects.bulk_create(
            [SocialPostTag(post=post, personaggio_id=pid) for pid in new_ids]
        )
    if new_ids and _should_notify(notify):
        from .mention_notifications import notify_instafame_mentions

        notify_instafame_mentions(post.autore, new_ids, "post", post=post)
    return new_ids


def sync_comment_tags(comment: SocialComment, *, notify: bool | None = None) -> list[int]:
    ids = extract_mentioned_personaggi_ids(comment.testo)
    existing = set(SocialCommentTag.objects.filter(comment=comment).values_list("personaggio_id", flat=True))
    new_ids = [pid for pid in ids if pid not in existing]
    SocialCommentTag.objects.filter(comment=comment).exclude(personaggio_id__in=ids).delete()
    if new_ids:
        SocialCommentTag.objects.bulk_create(
            [SocialCommentTag(comment=comment, personaggio_id=pid) for pid in new_ids]
        )
    if new_ids and _should_notify(notify):
        from .mention_notifications import notify_instafame_mentions

        notify_instafame_mentions(
            comment.autore, new_ids, "comment", comment=comment, post=comment.post
        )
    return new_ids


def sync_story_tags(story: SocialStory, *, notify: bool | None = None) -> list[int]:
    ids = extract_mentioned_personaggi_ids(story.testo)
    existing = set(SocialStoryTag.objects.filter(story=story).values_list("personaggio_id", flat=True))
    new_ids = [pid for pid in ids if pid not in existing]
    SocialStoryTag.objects.filter(story=story).exclude(personaggio_id__in=ids).delete()
    if new_ids:
        SocialStoryTag.objects.bulk_create(
            [SocialStoryTag(story=story, personaggio_id=pid) for pid in new_ids]
        )
    if new_ids and _should_notify(notify):
        from .mention_notifications import notify_instafame_mentions

        notify_instafame_mentions(story.autore, new_ids, "story", story=story)
    return new_ids


def post_ids_needing_tag_resync() -> list[int]:
    """Post con @ nel testo ma tag DB assenti o incompleti."""
    missing: list[int] = []
    for post in SocialPost.objects.only("id", "titolo", "testo").iterator():
        text = f"{post.titolo or ''}\n{post.testo or ''}"
        if not MENTION_IN_TEXT_REGEX.search(text or ""):
            continue
        expected = set(extract_mentioned_personaggi_ids(text))
        if not expected:
            continue
        actual = set(SocialPostTag.objects.filter(post_id=post.id).values_list("personaggio_id", flat=True))
        if expected != actual:
            missing.append(post.id)
    return missing
