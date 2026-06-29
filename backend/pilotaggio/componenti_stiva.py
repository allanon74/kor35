"""
Stiva componenti nave: inventario globale, annichilamento coppie opposte.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .componenti_nave_constants import (
    AURA_COMPONENTI_SIGLA,
    TICK_COESISTENZA_OPPOSITI_MAX,
)


def aura_componenti_qs():
    from personaggi.models import Punteggio

    return Punteggio.objects.filter(tipo="AU", sigla=AURA_COMPONENTI_SIGLA)


def mattoni_componente_qs():
    from personaggi.models import Mattone

    return (
        Mattone.objects.filter(aura__sigla=AURA_COMPONENTI_SIGLA)
        .select_related("aura", "caratteristica_associata")
        .order_by("indice_componente", "ordine", "nome")
    )


def _quantita_colore(colore_id) -> int:
    from .models import StivaComponenteNave

    total = (
        StivaComponenteNave.objects.filter(
            mattone__aura__sigla=AURA_COMPONENTI_SIGLA,
            mattone__caratteristica_associata_id=colore_id,
            quantita__gt=0,
        ).aggregate(total=Sum("quantita"))["total"]
        or 0
    )
    return int(total)


def _consuma_colore(colore_id, quantita: int) -> int:
    """Decrementa fino a `quantita` unità del colore; ritorna quantità effettivamente consumata."""
    from .models import StivaComponenteNave

    if quantita <= 0:
        return 0

    remaining = int(quantita)
    consumed = 0
    rows = list(
        StivaComponenteNave.objects.select_for_update()
        .filter(
            mattone__aura__sigla=AURA_COMPONENTI_SIGLA,
            mattone__caratteristica_associata_id=colore_id,
            quantita__gt=0,
        )
        .select_related("mattone")
        .order_by("mattone__indice_componente", "mattone__ordine", "mattone__nome")
    )
    for row in rows:
        if remaining <= 0:
            break
        take = min(int(row.quantita), remaining)
        row.quantita = int(row.quantita) - take
        row.save(update_fields=["quantita", "updated_at"])
        remaining -= take
        consumed += take
    return consumed


def _aggiungi_mattone(mattone, quantita: int) -> None:
    from .models import StivaComponenteNave

    if quantita <= 0:
        return
    row, _ = StivaComponenteNave.objects.select_for_update().get_or_create(
        mattone=mattone,
        defaults={"quantita": 0},
    )
    row.quantita = int(row.quantita) + int(quantita)
    row.save(update_fields=["quantita", "updated_at"])


@transaction.atomic
def applica_annichilamento_opposti_stiva() -> Dict[str, Any]:
    """
    Per ogni coppia opposta: se entrambi i colori sono in stiva, avanza tick coesistenza.
    Dopo TICK_COESISTENZA_OPPOSITI_MAX tick, annichila min(qty_a, qty_b) in un colpo.
    """
    from .models import (
        CoppiaColoriComponente,
        PilotRuntimeConfig,
        StivaCoppiaOppositiStato,
    )

    cfg = PilotRuntimeConfig.get_solo()
    if not cfg.annichilamento_opposti_abilitato:
        return {"skipped": True, "reason": "annichilamento_disabilitato"}

    eventi: List[dict] = []
    for coppia in CoppiaColoriComponente.objects.select_related("colore_a", "colore_b").order_by(
        "ordine"
    ):
        stato, _ = StivaCoppiaOppositiStato.objects.select_for_update().get_or_create(
            coppia=coppia
        )
        qa = _quantita_colore(coppia.colore_a_id)
        qb = _quantita_colore(coppia.colore_b_id)

        if qa > 0 and qb > 0:
            stato.tick_coesistenza = int(stato.tick_coesistenza) + 1
            annichilato = 0
            if stato.tick_coesistenza > TICK_COESISTENZA_OPPOSITI_MAX:
                n = min(qa, qb)
                ca = _consuma_colore(coppia.colore_a_id, n)
                cb = _consuma_colore(coppia.colore_b_id, n)
                annichilato = min(ca, cb)
                stato.tick_coesistenza = 0
                if annichilato > 0:
                    eventi.append(
                        {
                            "coppia_id": str(coppia.pk),
                            "colore_a": coppia.colore_a.sigla or coppia.colore_a.nome,
                            "colore_b": coppia.colore_b.sigla or coppia.colore_b.nome,
                            "annichilato": annichilato,
                        }
                    )
            stato.save(update_fields=["tick_coesistenza", "updated_at"])
        elif stato.tick_coesistenza:
            stato.tick_coesistenza = 0
            stato.save(update_fields=["tick_coesistenza", "updated_at"])

    return {"skipped": False, "eventi": eventi}


def applica_stiva_tick_se_dovuto(*, force: bool = False) -> Optional[Dict[str, Any]]:
    """Esegue al più un tick stiva per intervallo runtime (evita doppio conteggio su più sessioni)."""
    from .models import PilotRuntimeConfig

    cfg = PilotRuntimeConfig.get_solo()
    now = timezone.now()
    interval = float(cfg.tick_interval_secondi or 5.0)
    if not force and cfg.stiva_ultimo_tick_at is not None:
        elapsed = (now - cfg.stiva_ultimo_tick_at).total_seconds()
        if elapsed < max(0.5, interval * 0.85):
            return None

    result = applica_annichilamento_opposti_stiva()
    cfg.stiva_ultimo_tick_at = now
    cfg.save(update_fields=["stiva_ultimo_tick_at", "updated_at"])
    return result


def build_stiva_payload() -> dict:
    from .models import CoppiaColoriComponente, StivaComponenteNave, StivaCoppiaOppositiStato

    righe = []
    for row in (
        StivaComponenteNave.objects.filter(quantita__gt=0)
        .select_related("mattone", "mattone__caratteristica_associata", "mattone__aura")
        .order_by("mattone__indice_componente", "mattone__ordine")
    ):
        m = row.mattone
        col = m.caratteristica_associata
        righe.append(
            {
                "mattone_id": str(m.pk),
                "indice_componente": m.indice_componente,
                "nome": m.nome,
                "colore_id": str(col.pk) if col else None,
                "colore_nome": col.nome if col else "",
                "colore_sigla": col.sigla if col else "",
                "quantita": int(row.quantita),
            }
        )

    coppie = []
    for coppia in CoppiaColoriComponente.objects.select_related("colore_a", "colore_b").order_by(
        "ordine"
    ):
        stato = StivaCoppiaOppositiStato.objects.filter(coppia=coppia).first()
        tick = int(stato.tick_coesistenza) if stato else 0
        qa = _quantita_colore(coppia.colore_a_id)
        qb = _quantita_colore(coppia.colore_b_id)
        coppie.append(
            {
                "id": str(coppia.pk),
                "colore_a": {
                    "id": str(coppia.colore_a_id),
                    "nome": coppia.colore_a.nome,
                    "sigla": coppia.colore_a.sigla,
                    "quantita": qa,
                },
                "colore_b": {
                    "id": str(coppia.colore_b_id),
                    "nome": coppia.colore_b.nome,
                    "sigla": coppia.colore_b.sigla,
                    "quantita": qb,
                },
                "tick_coesistenza": tick,
                "tick_coesistenza_max": TICK_COESISTENZA_OPPOSITI_MAX,
                "entrambi_presenti": qa > 0 and qb > 0,
            }
        )

    return {"righe": righe, "coppie_opposite": coppie}


def build_staff_stiva_payload() -> dict:
    """Payload completo per staff (inventario + catalogo mattoni per la tabella)."""
    payload = build_stiva_payload()
    payload["mattoni_catalogo"] = [
        {
            "id": str(m.pk),
            "nome": m.nome,
            "indice_componente": m.indice_componente,
            "colore_id": str(m.caratteristica_associata_id),
            "colore_nome": m.caratteristica_associata.nome if m.caratteristica_associata else "",
        }
        for m in mattoni_componente_qs()
    ]
    return payload


@transaction.atomic
def staff_modifica_stiva(*, mattone_id, delta: int) -> dict:
    """Aggiunge (delta>0) o rimuove (delta<0) quantità in stiva."""
    from personaggi.models import Mattone

    from .models import StivaComponenteNave

    mattone = Mattone.objects.filter(pk=mattone_id, aura__sigla=AURA_COMPONENTI_SIGLA).first()
    if mattone is None:
        raise ValueError("Mattone componente non valido.")

    row, _ = StivaComponenteNave.objects.select_for_update().get_or_create(
        mattone=mattone,
        defaults={"quantita": 0},
    )
    nuova = int(row.quantita) + int(delta)
    if nuova < 0:
        raise ValueError("Quantità insufficiente in stiva.")
    row.quantita = nuova
    row.save(update_fields=["quantita", "updated_at"])
    return build_staff_stiva_payload()


@transaction.atomic
def consuma_mattoni_stiva(allocazioni: List[dict]) -> None:
    """
    allocazioni: [{mattone_id, quantita}, ...]
    """
    from personaggi.models import Mattone

    from .models import StivaComponenteNave

    for item in allocazioni:
        mattone_id = item.get("mattone_id")
        qty = int(item.get("quantita") or 0)
        if qty <= 0:
            continue
        mattone = Mattone.objects.filter(pk=mattone_id, aura__sigla=AURA_COMPONENTI_SIGLA).first()
        if mattone is None:
            raise ValueError(f"Mattone componente non valido: {mattone_id}")
        row = (
            StivaComponenteNave.objects.select_for_update()
            .filter(mattone=mattone)
            .first()
        )
        disponibile = int(row.quantita) if row else 0
        if disponibile < qty:
            raise ValueError(f"Componenti insufficienti: {mattone.nome} ({disponibile}<{qty}).")
        row.quantita = disponibile - qty
        row.save(update_fields=["quantita", "updated_at"])


def _colori_componente_ordinati():
    from personaggi.models import Punteggio

    return list(
        Punteggio.objects.filter(tipo="CA", sigla__startswith="0C")
        .order_by("ordine", "sigla")
    )[:10]


def indice_colore_componente(colore) -> int:
    if colore is None:
        raise ValueError("Colore componente mancante.")
    sigla = (colore.sigla or "").strip()
    if sigla.startswith("0C") and len(sigla) >= 3 and sigla[2:].isdigit():
        return int(sigla[2:])
    colori = _colori_componente_ordinati()
    for i, c in enumerate(colori):
        if c.pk == colore.pk:
            return i
    raise ValueError("Colore componente non riconosciuto nella scala 0–9.")


def _azzera_quantita_colore(colore_id) -> int:
    from .models import StivaComponenteNave

    removed = 0
    rows = StivaComponenteNave.objects.select_for_update().filter(
        mattone__aura__sigla=AURA_COMPONENTI_SIGLA,
        mattone__caratteristica_associata_id=colore_id,
        quantita__gt=0,
    )
    for row in rows:
        removed += int(row.quantita)
        row.quantita = 0
        row.save(update_fields=["quantita", "updated_at"])
    return removed


@transaction.atomic
def azzera_stiva_colori(colore_ids: List) -> int:
    total = 0
    for cid in colore_ids:
        total += _azzera_quantita_colore(cid)
    return total


@transaction.atomic
def azzera_stiva_tranne_colori(colore_ids_da_tenere: List) -> int:
    from .models import StivaComponenteNave

    keep = set(colore_ids_da_tenere)
    removed = 0
    rows = StivaComponenteNave.objects.select_for_update().filter(
        mattone__aura__sigla=AURA_COMPONENTI_SIGLA,
        quantita__gt=0,
    ).select_related("mattone")
    for row in rows:
        cid = row.mattone.caratteristica_associata_id
        if cid in keep:
            continue
        removed += int(row.quantita)
        row.quantita = 0
        row.save(update_fields=["quantita", "updated_at"])
    return removed


def colori_presenti_in_stiva() -> set:
    from .models import StivaComponenteNave

    ids = (
        StivaComponenteNave.objects.filter(quantita__gt=0)
        .values_list("mattone__caratteristica_associata_id", flat=True)
        .distinct()
    )
    return {i for i in ids if i}


def mattone_per_indice_colore(indice: int):
    from personaggi.models import Mattone

    return (
        Mattone.objects.filter(
            aura__sigla=AURA_COMPONENTI_SIGLA,
            indice_componente=int(indice) % 10,
        )
        .order_by("ordine", "nome")
        .first()
    )
