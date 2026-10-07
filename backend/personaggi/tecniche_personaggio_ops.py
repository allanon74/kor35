"""
Assegnazione e revoca di tecniche possedute (infusioni, tessiture, cerimoniali).

Usato dalla dashboard staff personaggi. La modalità acquisto replica le regole
del giocatore (requisiti, Accademia, costo, royalty). L'omaggio staff salta
requisiti e addebito. La revoca staff ignora il blocco evento e rimborsa solo
quanto risulta pagato (pivot o movimento), senza inventare il listino.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from personaggi.acquisto_costi import (
    calcola_costo_tecnica_acquisto,
    trova_credito_pagato_acquisto,
)
from personaggi.models import (
    FEATURE_CERIMONIALI,
    FEATURE_INFUSIONI,
    FEATURE_TESSITURE,
    Cerimoniale,
    Infusione,
    Personaggio,
    PersonaggioCerimoniale,
    PersonaggioInfusione,
    PersonaggioTessitura,
    Tessitura,
    TessituraEffettoRuntime,
)

TIPI_TECNICA = ("infusione", "tessitura", "cerimoniale")

_SPEC = {
    "infusione": {
        "model": Infusione,
        "pivot": PersonaggioInfusione,
        "fk": "infusione",
        "m2m": "infusioni_possedute",
        "feature": FEATURE_INFUSIONI,
        "etichetta": "infusione",
        "articolo": "l'",
        "prefisso_acquisto": "Acquisito infusione",
    },
    "tessitura": {
        "model": Tessitura,
        "pivot": PersonaggioTessitura,
        "fk": "tessitura",
        "m2m": "tessiture_possedute",
        "feature": FEATURE_TESSITURE,
        "etichetta": "tessitura",
        "articolo": "la ",
        "prefisso_acquisto": "Acquisito tessitura",
    },
    "cerimoniale": {
        "model": Cerimoniale,
        "pivot": PersonaggioCerimoniale,
        "fk": "cerimoniale",
        "m2m": "cerimoniali_posseduti",
        "feature": FEATURE_CERIMONIALI,
        "etichetta": "cerimoniale",
        "articolo": "il ",
        "prefisso_acquisto": "Appreso cerimoniale",
    },
}


class TipoTecnicaNonValido(ValueError):
    pass


@dataclass
class TecnicaOpResult:
    ok: bool
    error: str = ""
    personaggio: Optional[Personaggio] = None
    status: int = 400


def _spec(tipo: str) -> dict:
    key = (tipo or "").strip().lower()
    spec = _SPEC.get(key)
    if not spec:
        raise TipoTecnicaNonValido("Tipo tecnica non valido (infusione, tessitura, cerimoniale).")
    return spec


def _clip(text: str, max_len: int = 200) -> str:
    text = str(text or "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _tecnica_in_campagna(request, tecnica, feature: str) -> bool:
    if request is None:
        return True
    from personaggi.views import _campaign_feature_filter

    model = tecnica.__class__
    return _campaign_feature_filter(
        request, model.objects.filter(pk=tecnica.pk), feature
    ).exists()


def _nome_aura(tecnica) -> str:
    aura = getattr(tecnica, "aura_richiesta", None)
    return aura.nome if aura else ""


def catalogo_tecniche_per_staff(personaggio, tipo: str, request, q: str = "") -> list[dict]:
    """Catalogo compatto delle tecniche non ancora possedute, filtrate per campagna."""
    tipo = (tipo or "").strip().lower()
    spec = _spec(tipo)
    model = spec["model"]
    possedute_ids = getattr(personaggio, spec["m2m"]).values_list("id", flat=True)
    qs = model.objects.exclude(id__in=possedute_ids).select_related("aura_richiesta")
    if request is not None:
        from personaggi.views import _campaign_feature_filter

        qs = _campaign_feature_filter(request, qs, spec["feature"])
    q = (q or "").strip()
    if q:
        qs = qs.filter(nome__icontains=q)
    if tipo == "cerimoniale":
        rows = []
        for row in qs.order_by("nome"):
            rows.append(
                {
                    "id": row.id,
                    "nome": row.nome,
                    "livello": int(row.liv or 0),
                    "aura": _nome_aura(row),
                    "non_acquistabile": bool(row.non_acquistabile),
                }
            )
        return rows

    rows = []
    annotated = qs.annotate(livello_calc=Sum("componenti__valore")).order_by("nome")
    for row in annotated:
        rows.append(
            {
                "id": row.id,
                "nome": row.nome,
                "livello": int(row.livello_calc or 0),
                "aura": _nome_aura(row),
                "non_acquistabile": bool(row.non_acquistabile),
            }
        )
    return rows


def serializza_tecniche_possedute(personaggio, tipo: str) -> list[dict]:
    tipo = (tipo or "").strip().lower()
    spec = _spec(tipo)
    fk = spec["fk"]
    qs = (
        spec["pivot"]
        .objects.filter(personaggio=personaggio)
        .select_related(fk, f"{fk}__aura_richiesta")
        .order_by(f"{fk}__nome")
    )
    if tipo != "cerimoniale":
        qs = qs.annotate(_livello=Sum(f"{fk}__componenti__valore"))
    out = []
    for pivot in qs:
        tecnica = getattr(pivot, fk)
        if tipo == "cerimoniale":
            livello = int(getattr(tecnica, "liv", 0) or 0)
        else:
            livello = int(getattr(pivot, "_livello", None) or 0)
        pagato = Decimal(pivot.costo_crediti_pagato or 0)
        out.append(
            {
                "id": tecnica.id,
                "nome": tecnica.nome,
                "livello": livello,
                "aura": _nome_aura(tecnica),
                "costo_crediti_pagato": f"{pagato:.2f}",
                "data_acquisizione": (
                    pivot.data_acquisizione.isoformat() if pivot.data_acquisizione else None
                ),
            }
        )
    return out


def _applica_royalty(tecnica, acquirente, costo, *, revoca: bool = False) -> None:
    proposta = getattr(tecnica, "proposta_creazione", None)
    if not proposta:
        return
    creatore = getattr(proposta, "personaggio", None)
    if not creatore or creatore.id == acquirente.id:
        return
    royalty = int(round(float(costo) * 0.10))
    if royalty <= 0:
        return
    if revoca:
        creatore.modifica_crediti(
            -royalty,
            _clip(f"Revocata royalty per '{tecnica.nome}' da {acquirente.nome}"),
            conto="DEPOSITO",
        )
        creatore.aggiungi_log(
            f"Ha ricevuto -{royalty} CR (revoca) di royalty per la tecnica '{tecnica.nome}'."
        )
    else:
        creatore.modifica_crediti(
            royalty,
            _clip(f"Royalty per l'acquisto di '{tecnica.nome}' da parte di {acquirente.nome}"),
            conto="DEPOSITO",
        )
        creatore.aggiungi_log(
            f"Ha ricevuto {royalty} CR di royalty per la tecnica '{tecnica.nome}'."
        )


def _chiudi_runtime_tessitura(personaggio, tessitura) -> None:
    from personaggi.services import TessituraRuntimeService

    attivi = TessituraEffettoRuntime.objects.filter(
        personaggio=personaggio,
        tessitura=tessitura,
        is_attivo=True,
    )
    for runtime in attivi:
        TessituraRuntimeService._close_runtime(runtime, reason="staff_revoca")


def _rimborso_revoca(pivot, tecnica, tipo: str) -> Decimal:
    """Rimborsa il pagato memorizzato o il movimento di acquisto giocatore. Mai il listino."""
    pagato = Decimal(pivot.costo_crediti_pagato or 0)
    if pagato > 0:
        return pagato
    spec = _spec(tipo)
    exact = f"{spec['prefisso_acquisto']}: {tecnica.nome}"
    found = trova_credito_pagato_acquisto(
        pivot.personaggio,
        descrizione_esatta=exact,
        acquired_at=pivot.data_acquisizione,
    )
    return found or Decimal("0")


@transaction.atomic
def acquisisci_tecnica_personaggio(
    personaggio,
    tipo: str,
    tecnica_id,
    request,
    *,
    omaggio: bool = False,
    motivo_staff: str = "",
) -> TecnicaOpResult:
    tipo = (tipo or "").strip().lower()
    spec = _spec(tipo)
    model = spec["model"]
    try:
        tecnica = model.objects.select_related("aura_richiesta", "proposta_creazione").get(pk=tecnica_id)
    except (model.DoesNotExist, ValueError, TypeError):
        return TecnicaOpResult(
            ok=False,
            error=f"{spec['etichetta'].capitalize()} non trovata.",
            status=404,
        )

    if not _tecnica_in_campagna(request, tecnica, spec["feature"]):
        return TecnicaOpResult(
            ok=False,
            error=f"{spec['etichetta'].capitalize()} non disponibile nella campagna attiva.",
            status=403,
        )

    personaggio = Personaggio.objects.select_for_update().get(pk=personaggio.pk)
    if getattr(personaggio, spec["m2m"]).filter(id=tecnica.id).exists():
        return TecnicaOpResult(
            ok=False,
            error=f"{spec['etichetta'].capitalize()} già posseduta.",
            status=400,
        )

    motivo = (motivo_staff or "").strip()
    suffisso = f" ({motivo})" if motivo else ""
    costo_dec = Decimal("0")

    if not omaggio:
        from personaggi.accademia_catalogo import verifica_tecnica_accademia

        try:
            verifica_tecnica_accademia(tecnica)
        except ValidationError as exc:
            return TecnicaOpResult(ok=False, error=str(exc), status=400)

        ok_val, msg_val = personaggio.valida_acquisto_tecnica(tecnica)
        if not ok_val:
            return TecnicaOpResult(ok=False, error=msg_val, status=400)

        costo = int(calcola_costo_tecnica_acquisto(personaggio, tecnica) or 0)
        costo_dec = Decimal(costo)
        if personaggio.crediti < costo_dec:
            return TecnicaOpResult(
                ok=False,
                error=f"Crediti insufficienti. Richiesti: {costo}",
                status=400,
            )
        if costo_dec:
            personaggio.modifica_crediti(
                -costo_dec,
                _clip(f"Staff: {spec['prefisso_acquisto']}: {tecnica.nome}{suffisso}"),
            )
        _applica_royalty(tecnica, personaggio, costo_dec, revoca=False)
        personaggio.aggiungi_log(
            f"Staff: ha appreso {spec['articolo']}{spec['etichetta']} '{tecnica.nome}' "
            f"(Liv. {tecnica.livello}){suffisso}."
        )
    else:
        personaggio.aggiungi_log(
            f"Staff: omaggio {spec['articolo']}{spec['etichetta']} '{tecnica.nome}'{suffisso}."
        )

    spec["pivot"].objects.create(
        personaggio=personaggio,
        **{spec["fk"]: tecnica},
        costo_crediti_pagato=costo_dec,
    )
    personaggio.refresh_from_db()
    return TecnicaOpResult(ok=True, personaggio=personaggio, status=200)


@transaction.atomic
def revoca_tecnica_personaggio(
    personaggio,
    tipo: str,
    tecnica_id,
    *,
    motivo_staff: str = "",
) -> TecnicaOpResult:
    """Revoca staff: sempre consentita (anche in evento). Rimborsa solo il pagato."""
    tipo = (tipo or "").strip().lower()
    spec = _spec(tipo)
    try:
        pivot = (
            spec["pivot"]
            .objects.select_related(spec["fk"], f"{spec['fk']}__proposta_creazione")
            .get(personaggio=personaggio, **{f"{spec['fk']}_id": tecnica_id})
        )
    except spec["pivot"].DoesNotExist:
        return TecnicaOpResult(
            ok=False,
            error=f"{spec['etichetta'].capitalize()} non posseduta.",
            status=404,
        )
    except (ValueError, TypeError):
        return TecnicaOpResult(
            ok=False,
            error=f"{spec['etichetta'].capitalize()} non trovata.",
            status=404,
        )

    tecnica = getattr(pivot, spec["fk"])
    personaggio = Personaggio.objects.select_for_update().get(pk=personaggio.pk)
    refund = _rimborso_revoca(pivot, tecnica, tipo)
    motivo = (motivo_staff or "").strip()
    suffisso = f" ({motivo})" if motivo else ""

    if refund:
        personaggio.modifica_crediti(
            refund,
            _clip(f"Staff: revocato acquisto {spec['etichetta']}: {tecnica.nome}{suffisso}"),
        )
        _applica_royalty(tecnica, personaggio, refund, revoca=True)

    if tipo == "tessitura":
        _chiudi_runtime_tessitura(personaggio, tecnica)

    pivot.delete()
    personaggio.aggiungi_log(
        f"Staff: revocata {spec['articolo']}{spec['etichetta']} '{tecnica.nome}'{suffisso}."
    )
    personaggio.refresh_from_db()
    return TecnicaOpResult(ok=True, personaggio=personaggio, status=200)
