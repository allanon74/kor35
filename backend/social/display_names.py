from django.core.exceptions import ObjectDoesNotExist

from personaggi.models import Personaggio


def social_display_name(personaggio):
    """Nome visibile ad altri giocatori (nickname InstaFame se impostato)."""
    if not personaggio:
        return ""
    nickname = ""
    try:
        nickname = (personaggio.social_profile.nickname or "").strip()
    except ObjectDoesNotExist:
        pass
    return nickname or (personaggio.nome or "")


def social_display_name_from_profile(profile):
    if not profile:
        return ""
    nickname = (getattr(profile, "nickname", None) or "").strip()
    if nickname:
        return nickname
    pg = getattr(profile, "personaggio", None)
    return (pg.nome if pg else "") or ""


def social_display_names_for_ids(personaggio_ids):
    ids = list({int(i) for i in personaggio_ids if i})
    if not ids:
        return {}
    from social.models import SocialProfile

    nick_by_id = {
        row["personaggio_id"]: (row["nickname"] or "").strip()
        for row in SocialProfile.objects.filter(personaggio_id__in=ids).values("personaggio_id", "nickname")
    }
    nome_by_id = dict(Personaggio.objects.filter(id__in=ids).values_list("id", "nome"))
    return {pid: nick_by_id.get(pid) or nome_by_id.get(pid, "") for pid in ids}
