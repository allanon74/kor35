"""Compiti automatici: config + payload virtuali per il calendario staff."""
from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Count

from personaggi.models import (
    CAMPAGNA_ROLE_HEAD_MASTER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_STAFFER,
    CampagnaUtente,
    PropostaTecnica,
    STATO_PROPOSTA_IN_VALUTAZIONE,
    TIPO_PROPOSTA_CERIMONIALE,
    TIPO_PROPOSTA_INFUSIONE,
    TIPO_PROPOSTA_TESSITURA,
)

from .models import (
    COMPITO_AUTOMATICO_DEFAULT_CODICI,
    COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_CER,
    COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_INF,
    COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES,
    StaffCompitoAutomatico,
    StaffCompitoAutomaticoAssegnazione,
)

# Ruoli a cui si possono assegnare i compiti automatici di verifica proposte.
CAMPAGNA_ROLES_COMPITO_AUTOMATICO = (
    CAMPAGNA_ROLE_STAFFER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_HEAD_MASTER,
)

COMPITO_AUTOMATICO_META = {
    COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_TES: {
        "titolo_base": "Verifica tessiture",
        "descrizione": "Ci sono proposte di tessiture in valutazione. Aprili dal tool Valutazione proposte.",
        "proposta_tipo": TIPO_PROPOSTA_TESSITURA,
        "staff_tool": "proposte",
        "ordine": 1,
    },
    COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_INF: {
        "titolo_base": "Verifica infusioni",
        "descrizione": "Ci sono proposte di infusioni in valutazione. Aprili dal tool Valutazione proposte.",
        "proposta_tipo": TIPO_PROPOSTA_INFUSIONE,
        "staff_tool": "proposte",
        "ordine": 2,
    },
    COMPITO_AUTOMATICO_VERIFICA_PROPOSTE_CER: {
        "titolo_base": "Verifica cerimoniali",
        "descrizione": "Ci sono proposte di cerimoniali in valutazione. Aprili dal tool Valutazione proposte.",
        "proposta_tipo": TIPO_PROPOSTA_CERIMONIALE,
        "staff_tool": "proposte",
        "ordine": 3,
    },
}


def user_ids_assegnabili_automatici(campagna):
    if not campagna:
        return User.objects.none()
    ids = CampagnaUtente.objects.filter(
        campagna=campagna,
        attivo=True,
        ruolo__in=CAMPAGNA_ROLES_COMPITO_AUTOMATICO,
    ).values_list("user_id", flat=True)
    return User.objects.filter(pk__in=ids)


def ensure_default_compiti_automatici(campagna) -> list[StaffCompitoAutomatico]:
    """Crea le tre config di default se mancanti (senza assegnatari)."""
    if not campagna:
        return []
    rows = []
    for codice in COMPITO_AUTOMATICO_DEFAULT_CODICI:
        obj, _ = StaffCompitoAutomatico.objects.get_or_create(
            campagna=campagna,
            codice=codice,
            defaults={"attivo": True},
        )
        rows.append(obj)
    return rows


def sync_assegnatari_automatico(config: StaffCompitoAutomatico, user_ids: list[int], *, campagna) -> None:
    allowed = set(user_ids_assegnabili_automatici(campagna).values_list("pk", flat=True))
    wanted = {int(uid) for uid in user_ids if int(uid) in allowed}
    existing = {row.user_id: row for row in config.assegnazioni.all()}
    for uid, row in list(existing.items()):
        if uid not in wanted:
            row.delete()
    for uid in wanted:
        if uid not in existing:
            StaffCompitoAutomaticoAssegnazione.objects.create(config=config, user_id=uid)


def conteggi_proposte_in_valutazione(campagna) -> dict[str, int]:
    """Mappa codice_compito → conteggio proposte in VALUTAZIONE per tipo."""
    if not campagna:
        return {c: 0 for c in COMPITO_AUTOMATICO_DEFAULT_CODICI}
    rows = (
        PropostaTecnica.objects.filter(
            stato=STATO_PROPOSTA_IN_VALUTAZIONE,
            personaggio__campagna=campagna,
        )
        .values("tipo")
        .annotate(n=Count("id"))
    )
    by_tipo = {r["tipo"]: int(r["n"]) for r in rows}
    out = {}
    for codice, meta in COMPITO_AUTOMATICO_META.items():
        out[codice] = by_tipo.get(meta["proposta_tipo"], 0)
    return out


def _assegnazione_payload(row: StaffCompitoAutomaticoAssegnazione, *, request_user) -> dict:
    user = row.user
    return {
        "id": str(row.id),
        "user": user.pk,
        "username": user.username,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "completato_at": None,
        "is_mine": bool(request_user and request_user.is_authenticated and user.pk == request_user.pk),
    }


def build_automatic_compito_payload(
    config: StaffCompitoAutomatico,
    *,
    conteggio: int,
    request_user,
) -> dict | None:
    """Payload virtuale allineato a StaffCompitoSerializer. None se non mostrabile."""
    if not config.attivo or conteggio <= 0:
        return None
    meta = COMPITO_AUTOMATICO_META.get(config.codice)
    if not meta:
        return None
    assegnazioni = [
        _assegnazione_payload(row, request_user=request_user)
        for row in config.assegnazioni.select_related("user").order_by("user__username")
    ]
    if not assegnazioni:
        return None
    mia = next((a for a in assegnazioni if a["is_mine"]), None)
    titolo_base = meta["titolo_base"]
    return {
        "id": f"auto:{config.codice}",
        "automatico": True,
        "codice": config.codice,
        "conteggio": conteggio,
        "staff_tool": meta["staff_tool"],
        "campagna": config.campagna_id,
        "titolo": f"{titolo_base}: {conteggio}",
        "descrizione": meta["descrizione"],
        "scadenza": None,
        "preavviso_minuti": 0,
        "preavviso_at": None,
        "crea_notifica_scadenza": False,
        "creato_da": None,
        "creato_da_username": "sistema",
        "attivo": True,
        "assegnazioni": assegnazioni,
        "mia_assegnazione": mia,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if getattr(config, "updated_at", None) else None,
    }


def list_automatic_compiti_payloads(
    *,
    campagna,
    request_user,
    only_assigned_to_user: bool = False,
) -> list[dict]:
    """
    Compiti automatici da anteporre alla lista.
    - only_assigned_to_user=True: solo se l'utente corrente è assegnatario (miei / non-master).
    - False (master overview): tutti quelli con conteggio > 0 e almeno un assegnatario.
    """
    if not campagna:
        return []
    ensure_default_compiti_automatici(campagna)
    conteggi = conteggi_proposte_in_valutazione(campagna)
    configs = (
        StaffCompitoAutomatico.objects.filter(campagna=campagna, attivo=True)
        .prefetch_related("assegnazioni__user")
    )
    by_codice = {c.codice: c for c in configs}
    out = []
    for codice in sorted(
        COMPITO_AUTOMATICO_META.keys(),
        key=lambda c: COMPITO_AUTOMATICO_META[c]["ordine"],
    ):
        config = by_codice.get(codice)
        if not config:
            continue
        payload = build_automatic_compito_payload(
            config,
            conteggio=conteggi.get(codice, 0),
            request_user=request_user,
        )
        if not payload:
            continue
        if only_assigned_to_user:
            if not payload.get("mia_assegnazione"):
                continue
        out.append(payload)
    return out


def serialize_config_row(config: StaffCompitoAutomatico, *, conteggio: int = 0) -> dict:
    meta = COMPITO_AUTOMATICO_META.get(config.codice) or {}
    return {
        "id": str(config.id),
        "codice": config.codice,
        "label": dict(config._meta.get_field("codice").choices).get(config.codice, config.codice),
        "titolo_base": meta.get("titolo_base") or config.codice,
        "attivo": config.attivo,
        "conteggio": conteggio,
        "staff_tool": meta.get("staff_tool") or "proposte",
        "assegnatari": [
            {
                "id": row.user_id,
                "username": row.user.username,
                "first_name": row.user.first_name or "",
                "last_name": row.user.last_name or "",
            }
            for row in config.assegnazioni.select_related("user").order_by("user__username")
        ],
    }
