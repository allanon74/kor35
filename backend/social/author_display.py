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
