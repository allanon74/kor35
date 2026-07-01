"""
Operazioni condivise acquisizione/revoca abilità (giocatore e staff).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Tuple

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction

from personaggi.acquisto_costi import (
    calcola_costi_abilita_acquisto,
    rimborso_crediti_da_pivot,
    rimborso_pc_da_pivot,
)
from personaggi.carriere_tier_sblocco import invalidate_acquirable_skills_cache
from personaggi.modificabilita import (
    get_abilita_bloccate_da_prerequisito,
    get_event_context,
    is_modificabile_per_eventi,
    personaggio_scheda_modifica_libera,
)
from personaggi.models import (
    PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
    Abilita,
    EraAbilita,
    Personaggio,
    PersonaggioAbilita,
    RegioneAbilita,
    PARAMETRO_SCONTO_ABILITA,
)


@dataclass
class AbilitaOpResult:
    ok: bool
    error: str = ""
    personaggio: Optional[Personaggio] = None


def valuta_revoca_abilita(personaggio, abilita_id) -> Tuple[bool, str, Optional[PersonaggioAbilita]]:
    """Stesse regole di RevocaAbilitaView (senza effetti collaterali)."""
    try:
        pivot = PersonaggioAbilita.objects.select_related("abilita").get(
            personaggio=personaggio,
            abilita_id=abilita_id,
        )
    except PersonaggioAbilita.DoesNotExist:
        return False, "Abilità non posseduta.", None

    abilita = pivot.abilita
    if pivot.origine != PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO:
        return (
            False,
            "Questa abilità è assegnata automaticamente (Era, Regione o Carriera/KORP) "
            "e non può essere revocata singolarmente.",
            pivot,
        )

    event_in_corso, latest_event_start = get_event_context()
    if not is_modificabile_per_eventi(
        pivot.data_acquisizione,
        event_in_corso=event_in_corso,
        latest_event_start=latest_event_start,
        personaggio=personaggio,
    ):
        return False, "Acquisto non revocabile in questo momento.", pivot

    possessed_ids = set(personaggio.abilita_possedute.values_list("id", flat=True))
    prereq_locked_ids = get_abilita_bloccate_da_prerequisito(possessed_ids)
    if abilita.id in prereq_locked_ids:
        return (
            False,
            "Abilità non revocabile: è prerequisito di un'altra abilità posseduta.",
            pivot,
        )

    return True, "", pivot


@transaction.atomic
def revoca_abilita_personaggio(
    personaggio,
    abilita_id,
    *,
    staff: bool = False,
    motivo_staff: str = "",
) -> AbilitaOpResult:
    ok, err, pivot = valuta_revoca_abilita(personaggio, abilita_id)
    if not ok:
        return AbilitaOpResult(ok=False, error=err)

    abilita = pivot.abilita
    acquired_at = pivot.data_acquisizione

    pc_refund = rimborso_pc_da_pivot(pivot, acquired_at=acquired_at)
    credits_refund = rimborso_crediti_da_pivot(pivot, item=abilita, acquired_at=acquired_at)

    log_suffix = f" ({motivo_staff})" if staff and motivo_staff else ""
    refund_prefix = "Staff: revocato acquisto abilità" if staff else "Revocato acquisto abilità"

    if pc_refund:
        personaggio.modifica_pc(pc_refund, f"{refund_prefix}: {abilita.nome}{log_suffix}")
    if credits_refund:
        personaggio.modifica_crediti(credits_refund, f"{refund_prefix}: {abilita.nome}{log_suffix}")

    pivot.delete()
    if staff:
        personaggio.aggiungi_log(f"Staff: revocata abilità «{abilita.nome}»{log_suffix}.")
    else:
        personaggio.aggiungi_log(f"Ha revocato l'acquisto dell'abilità '{abilita.nome}'.")

    invalidate_acquirable_skills_cache(personaggio.id)
    cache.delete(f"acquirable_skills_{personaggio.id}")

    from personaggi.views import _sync_coma_state

    _sync_coma_state(personaggio)
    personaggio.refresh_from_db()
    return AbilitaOpResult(ok=True, personaggio=personaggio)


@transaction.atomic
def acquisisci_abilita_personaggio(personaggio, abilita_id, request, *, staff: bool = False, motivo_staff: str = "") -> AbilitaOpResult:
    """
    Stessa logica di AcquisisciAbilitaView (validazioni, costi, rimborsi swap AIN).
  `request` serve per filtri campagna; può essere None solo in contesti staff senza filtro.
    """
    from django.utils import timezone

    from personaggi.accademia_catalogo import verifica_abilita_accademia
    from personaggi.views import FEATURE_ABILITA, _campaign_feature_filter

    try:
        abilita = (
            Abilita.objects.select_related("aura_riferimento", "caratteristica", "caratteristica_2")
            .prefetch_related("abilita_requisito_set__requisito", "abilita_prerequisiti")
            .get(id=abilita_id)
        )
    except Abilita.DoesNotExist:
        return AbilitaOpResult(ok=False, error="Abilità non trovata.")

    if request is not None:
        abilita_qs = _campaign_feature_filter(request, Abilita.objects.filter(id=abilita_id), FEATURE_ABILITA)
        if not abilita_qs.exists():
            return AbilitaOpResult(ok=False, error="Abilità non disponibile nella campagna attiva.")

    try:
        verifica_abilita_accademia(abilita)
    except ValidationError as exc:
        return AbilitaOpResult(ok=False, error=str(exc))

    era_ids_abilita = set(EraAbilita.objects.filter(abilita_id=abilita.id).values_list("era_id", flat=True))
    if era_ids_abilita:
        if not personaggio.era_id:
            return AbilitaOpResult(
                ok=False,
                error="Questa abilità richiede la selezione di un'Era di provenienza.",
            )
        if personaggio.era_id not in era_ids_abilita:
            return AbilitaOpResult(
                ok=False,
                error="Questa abilità appartiene a un'altra Era e non è acquistabile dal personaggio.",
            )

    regione_ids_abilita = set(RegioneAbilita.objects.filter(abilita_id=abilita.id).values_list("regione_id", flat=True))
    if regione_ids_abilita:
        regione_pg_id = getattr(getattr(personaggio, "prefettura", None), "regione_id", None)
        if not regione_pg_id:
            return AbilitaOpResult(
                ok=False,
                error="Questa abilità richiede una regione di provenienza (tramite prefettura).",
            )
        if regione_pg_id not in regione_ids_abilita:
            return AbilitaOpResult(
                ok=False,
                error="Questa abilità appartiene a un'altra Regione e non è acquistabile dal personaggio.",
            )

    if personaggio.abilita_possedute.filter(id=abilita_id).exists():
        return AbilitaOpResult(ok=False, error="Abilità già posseduta.")

    is_tratto_ain = (
        abilita.is_tratto_aura
        and abilita.aura_riferimento_id
        and getattr(abilita.aura_riferimento, "sigla", None) == "AIN"
    )

    if is_tratto_ain and not personaggio_scheda_modifica_libera(personaggio):
        now = timezone.now()
        if personaggio.eventi_partecipati.filter(data_inizio__lte=now).exists():
            return AbilitaOpResult(
                ok=False,
                error="Non puoi modificare la razza: il personaggio partecipa già a un evento iniziato (o concluso).",
            )

    ok_val, msg_val = personaggio.valida_acquisizione_abilita(abilita)
    if not ok_val:
        return AbilitaOpResult(ok=False, error=msg_val)

    old_ain_trait = None
    if is_tratto_ain:
        liv = abilita.livello_riferimento
        if liv in (0, 1):
            old_ain_trait = (
                PersonaggioAbilita.objects.select_related("abilita")
                .filter(
                    personaggio=personaggio,
                    abilita__is_tratto_aura=True,
                    abilita__aura_riferimento__sigla="AIN",
                    abilita__livello_riferimento__in=(0, 1),
                )
                .order_by("-data_acquisizione")
                .first()
            )
            PersonaggioAbilita.objects.filter(
                personaggio=personaggio,
                abilita__is_tratto_aura=True,
                abilita__aura_riferimento__sigla="AIN",
                abilita__livello_riferimento__in=(0, 1),
            ).delete()
        elif liv == 2:
            old_ain_trait = (
                PersonaggioAbilita.objects.select_related("abilita")
                .filter(
                    personaggio=personaggio,
                    abilita__is_tratto_aura=True,
                    abilita__aura_riferimento__sigla="AIN",
                    abilita__livello_riferimento=2,
                )
                .order_by("-data_acquisizione")
                .first()
            )
            PersonaggioAbilita.objects.filter(
                personaggio=personaggio,
                abilita__is_tratto_aura=True,
                abilita__aura_riferimento__sigla="AIN",
                abilita__livello_riferimento=2,
            ).delete()
        personaggio = Personaggio.objects.select_related("tipologia").get(pk=personaggio.pk)

    if not is_tratto_ain:
        character_scores = personaggio.caratteristiche_base
        for req in abilita.abilita_requisito_set.all():
            punteggio_nome = req.requisito.nome
            valore_richiesto = req.valore
            punteggio_pg = character_scores.get(punteggio_nome, 0)
            if punteggio_pg < valore_richiesto:
                return AbilitaOpResult(
                    ok=False,
                    error=f"Requisito non soddisfatto: {punteggio_nome} {valore_richiesto} (possiedi {punteggio_pg})",
                )

    required_prereqs = [p.prerequisito for p in abilita.abilita_prerequisiti.all()]
    if required_prereqs:
        possessed_skill_ids = set(personaggio.abilita_possedute.values_list("id", flat=True))
        for prereq in required_prereqs:
            if prereq.id not in possessed_skill_ids:
                return AbilitaOpResult(ok=False, error=f"Prerequisito non soddisfatto: {prereq.nome}")

    log_suffix = f" ({motivo_staff})" if staff and motivo_staff else ""

    if is_tratto_ain:
        old_abilita = old_ain_trait.abilita if old_ain_trait else None
        old_costo_pc = int(getattr(old_abilita, "costo_pc", 0) or 0)
        old_costo_crediti = Decimal(getattr(old_abilita, "costo_crediti", 0) or 0)
        new_costo_pc = int(abilita.costo_pc or 0)
        new_costo_crediti = Decimal(abilita.costo_crediti or 0)
        pc_delta = old_costo_pc - new_costo_pc
        crediti_delta = old_costo_crediti - new_costo_crediti

        if pc_delta < 0 and personaggio.punti_caratteristica < abs(pc_delta):
            return AbilitaOpResult(
                ok=False,
                error=f"Punti Caratteristica insufficenti. Richiesti: {abs(pc_delta)}",
            )
        if crediti_delta < 0 and Decimal(personaggio.crediti) < abs(crediti_delta):
            return AbilitaOpResult(
                ok=False,
                error=f"Crediti insufficienti. Richiesti: {abs(crediti_delta)}",
            )

        ain_label = "Staff: cambio tratto AIN" if staff else "Cambio tratto AIN"
        if pc_delta:
            personaggio.modifica_pc(
                pc_delta,
                f"{ain_label}: {old_abilita.nome if old_abilita else 'Nessuno'} -> {abilita.nome}{log_suffix}",
            )
        if crediti_delta:
            personaggio.modifica_crediti(
                crediti_delta,
                f"{ain_label}: {old_abilita.nome if old_abilita else 'Nessuno'} -> {abilita.nome}{log_suffix}",
            )
        costo_pc_pagato = int(abilita.costo_pc or 0)
        costo_crediti_pagato = Decimal(abilita.costo_crediti or 0)
    else:
        costo_pc_finale, costo_crediti_finale = calcola_costi_abilita_acquisto(personaggio, abilita)
        mods = personaggio.modificatori_calcolati
        sconto_stat = mods.get(PARAMETRO_SCONTO_ABILITA, {"add": 0, "mol": 1.0})
        sconto_valore = max(0, sconto_stat.get("add", 0))

        if personaggio.punti_caratteristica < costo_pc_finale:
            return AbilitaOpResult(
                ok=False,
                error=f"Punti Caratteristica insufficenti. Richiesti: {costo_pc_finale}",
            )
        if personaggio.crediti < costo_crediti_finale:
            return AbilitaOpResult(
                ok=False,
                error=(
                    f"Crediti insufficenti. Richiesti: {costo_crediti_finale} "
                    f"(Costo base: {abilita.costo_crediti}, Sconto: {sconto_valore}%)"
                ),
            )

        acquire_label = "Staff: acquisita abilità" if staff else "Acquisito abilità"
        personaggio.modifica_pc(
            -costo_pc_finale,
            f"{acquire_label}: {abilita.nome} (Costo: {costo_pc_finale} PC){log_suffix}",
        )
        personaggio.modifica_crediti(
            -costo_crediti_finale,
            f"{acquire_label}: {abilita.nome} (Costo: {costo_crediti_finale} Crediti){log_suffix}",
        )
        costo_pc_pagato = int(costo_pc_finale)
        costo_crediti_pagato = costo_crediti_finale

    PersonaggioAbilita.objects.create(
        personaggio=personaggio,
        abilita=abilita,
        origine=PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
        costo_pc_pagato=costo_pc_pagato,
        costo_crediti_pagato=costo_crediti_pagato,
    )

    if staff:
        personaggio.aggiungi_log(f"Staff: assegnata abilità «{abilita.nome}»{log_suffix}.")

    invalidate_acquirable_skills_cache(personaggio.id)
    cache.delete(f"acquirable_skills_{personaggio.id}")

    from personaggi.views import _sync_coma_state

    _sync_coma_state(personaggio)
    personaggio.refresh_from_db()
    return AbilitaOpResult(ok=True, personaggio=personaggio)
