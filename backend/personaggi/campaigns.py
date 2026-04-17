from django.db import transaction

from personaggi.models import CAMPAGNA_ROLE_PLAYER, Campagna, CampagnaUtente


def get_or_create_base_campaign():
    """
    Recupera la campagna base Kor35 con fallback coerenti.
    """
    return (
        Campagna.objects.filter(is_base=True, attiva=True).order_by("-is_default", "nome").first()
        or Campagna.objects.filter(is_base=True).order_by("-is_default", "nome").first()
        or Campagna.objects.filter(is_default=True, attiva=True).order_by("nome").first()
        or Campagna.objects.filter(is_default=True).order_by("nome").first()
        or Campagna.objects.filter(slug="kor35").first()
        or Campagna.objects.create(
            slug="kor35",
            nome="Kor35",
            is_default=True,
            is_base=True,
            attiva=True,
        )
    )


def ensure_user_in_base_campaign(user):
    """
    Garantisce che l'utente abbia membership PLAYER attiva nella campagna base.
    """
    with transaction.atomic():
        campagna_base = get_or_create_base_campaign()
        membership, created = CampagnaUtente.objects.get_or_create(
            campagna=campagna_base,
            user=user,
            defaults={"ruolo": CAMPAGNA_ROLE_PLAYER, "attivo": True},
        )
        if not created and not membership.attivo:
            membership.attivo = True
            membership.save(update_fields=["attivo"])
        return membership
