"""Badge e cariche visibili su profilo/post InstaFame."""

from personaggi.models import PersonaggioCarrieraMembership


def get_personaggio_badge_instafame(personaggio) -> str:
    if not personaggio:
        return ""
    return str(getattr(personaggio, "badge_instafame", None) or "").strip()


def social_cariche_for_personaggio(personaggio):
    """Cariche attive con flag visibile_social, ordinate per carriera/carica."""
    if not personaggio:
        return []
    memberships = (
        PersonaggioCarrieraMembership.objects.filter(
            personaggio=personaggio,
            data_a__isnull=True,
            visibile_social=True,
            carica__isnull=False,
            carica__attiva=True,
        )
        .select_related("carriera", "carica", "tipo_carriera")
        .order_by("carriera__nome", "carica__ordine", "carica__nome")
    )
    return [
        {
            "carriera_nome": m.carriera.nome,
            "carica_nome": m.carica.nome,
            "tipo_carriera": m.tipo_carriera.codice if m.tipo_carriera_id else "",
        }
        for m in memberships
    ]


def social_firma_for_personaggio(personaggio, request=None):
    """Testo e URL banner firma social del personaggio (vuoto se assente)."""
    if not personaggio:
        return {"testo": "", "banner": None}
    profile = getattr(personaggio, "social_profile", None)
    if profile is None:
        return {"testo": "", "banner": None}
    testo = (profile.firma_testo or "").strip()
    banner = None
    field = profile.firma_banner
    if field and getattr(field, "name", ""):
        try:
            if field.storage.exists(field.name):
                banner = field.url
                if request:
                    banner = request.build_absolute_uri(banner)
        except Exception:
            banner = None
    if not testo and not banner:
        return {"testo": "", "banner": None}
    return {"testo": testo, "banner": banner}
