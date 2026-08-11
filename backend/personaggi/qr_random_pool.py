"""
Pool QR randomico: membership, estrazione pesata effetti, apply trappola/serie.
"""
from __future__ import annotations

import random
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone


def get_pool_membership(qr_code):
    from .models import RandomQrPoolMembership

    try:
        return (
            RandomQrPoolMembership.objects.select_related("pool")
            .prefetch_related("pool__effetti")
            .get(qr_code=qr_code)
        )
    except RandomQrPoolMembership.DoesNotExist:
        return None


def get_active_pool_for_qr(qr_code):
    membership = get_pool_membership(qr_code)
    if not membership:
        return None
    pool = membership.pool
    if not pool.attivo:
        return None
    return pool


class PoolMinigiocoConfigAdapter:
    """
    Adattatore duck-typed come MinigiocoQrConfig, alimentato dai campi del pool.
    Usato dal gate minigioco senza materializzare una riga MinigiocoQrConfig per ogni QR.
    """

    def __init__(self, pool):
        self._pool = pool
        self.sezione_attiva = bool(pool.minigioco_sezione_attiva)
        self.attivo = bool(pool.minigioco_attivo)
        self.tipi_abilitati = pool.minigioco_tipi_abilitati or []
        self.difficolta = int(pool.minigioco_difficolta or 4)
        self.difficolta_min = 1
        self.requisiti_attivazione = pool.minigioco_requisiti_attivazione or []
        self.messaggio_accesso_negato = pool.minigioco_messaggio_accesso_negato or ""
        self.esclusioni_minigioco = pool.minigioco_esclusioni or []
        self.regole_difficolta = pool.minigioco_regole_difficolta or []
        self.messaggio_pre = pool.minigioco_messaggio_pre or ""
        self.messaggio_vittoria = pool.minigioco_messaggio_vittoria or ""
        self.timer_secondi = pool.minigioco_timer_secondi
        self.timer_scadenza_azione = pool.minigioco_timer_scadenza_azione
        self.usa_biblioteca_se_vuota = bool(pool.minigioco_usa_biblioteca_se_vuota)
        self.modalita_sblocco = pool.minigioco_modalita_sblocco
        self.sblocco_secondi = pool.minigioco_sblocco_secondi
        self.immagine = pool.minigioco_immagine
        self.tipo = ""
        self.usa_default_pagina = False
        # Attributo usato in alcuni path; non esiste OneToOne reale
        self.qr_code = None
        self.qr_code_id = None

    def __repr__(self):
        return f"<PoolMinigiocoConfigAdapter pool={self._pool.pk}>"


def resolve_minigioco_config_for_qr(qr_code):
    """
    Override per-QR (MinigiocoQrConfig con sezione attiva) vince;
    altrimenti config a monte del pool se presente.
    """
    from .models import MinigiocoQrConfig

    try:
        cfg = qr_code.configurazione_minigioco
        if getattr(cfg, "sezione_attiva", False):
            return cfg
    except MinigiocoQrConfig.DoesNotExist:
        pass

    pool = get_active_pool_for_qr(qr_code)
    if pool and pool.minigioco_sezione_attiva:
        return PoolMinigiocoConfigAdapter(pool)
    return None


def effetti_attivi(pool) -> List:
    return [
        e
        for e in pool.effetti.all()
        if e.attivo and int(e.frequenza or 0) > 0
    ]


def scegli_effetto(pool, *, rng=None):
    """Estrae un effetto pesato. Ritorna None se nessun effetto disponibile."""
    rows = effetti_attivi(pool)
    if not rows:
        return None
    weights = [max(1, int(e.frequenza or 1)) for e in rows]
    chooser = rng.choices if rng is not None else random.choices
    return chooser(rows, weights=weights, k=1)[0]


def _broadcast_timer_trappola(
    *,
    nome: str,
    data_fine,
    recipient_personaggio_ids: List[int],
    testo: str = "",
):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "kor35_notifications",
        {
            "type": "send_notification",
            "message": {
                "action": "TIMER_TRAPPOLA_SYNC",
                "payload": {
                    "nome": nome,
                    "data_fine": data_fine.isoformat(),
                    "variant": "danger",
                    "testo": testo or "",
                    "alert_suono": True,
                    "notifica_push": True,
                    "messaggio_in_app": True,
                    "recipient_personaggio_ids": recipient_personaggio_ids,
                },
            },
        },
    )


def applica_trappola(
    *,
    personaggio,
    nome: str,
    testo: str = "",
    durata_secondi: Optional[int] = None,
    chiave: str,
    trappola=None,
) -> Dict[str, Any]:
    """
    Applica effetto trappola: testo + timer personale opzionale.
    """
    from .models import StatoTrappolaPersonaggio

    payload: Dict[str, Any] = {
        "nome": nome,
        "testo": testo or "",
        "durata_secondi": durata_secondi,
        "timer_attivo": False,
        "scadenza": None,
        "variant": "danger",
    }

    if not durata_secondi or int(durata_secondi) <= 0:
        return payload

    now = timezone.now()
    data_fine = now + timedelta(seconds=int(durata_secondi))
    with transaction.atomic():
        stato, _ = StatoTrappolaPersonaggio.objects.select_for_update().update_or_create(
            personaggio=personaggio,
            chiave=str(chiave)[:64],
            defaults={
                "nome": (nome or "Trappola")[:120],
                "testo": testo or "",
                "data_fine": data_fine,
                "trappola": trappola,
            },
        )

    _broadcast_timer_trappola(
        nome=stato.nome,
        data_fine=stato.data_fine,
        recipient_personaggio_ids=[personaggio.pk],
        testo=testo or "",
    )
    payload["timer_attivo"] = True
    payload["scadenza"] = stato.data_fine
    payload["nome"] = stato.nome
    return payload


def applica_serie(
    *,
    personaggio,
    serie,
    qr_code=None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Assegna un indice unico globale della serie e crea oggetto in inventario.
    Ritorna (payload, errore, tipo_modello_override).
    tipo_modello_override = 'serie_esaurita' se non restano pezzi.
    """
    from .models import Oggetto, SerieAssegnazione, TIPO_OGGETTO_FISICO

    if not personaggio:
        return None, "Parametro personaggio_id richiesto.", None
    if not serie:
        return None, "Serie non configurata.", None

    totale = int(serie.totale or 0)
    if totale < 1:
        return None, "Serie non valida (totale < 1).", None

    with transaction.atomic():
        # Lock sulla collezione per evitare doppie assegnazioni in race
        locked = type(serie).objects.select_for_update().get(pk=serie.pk)
        presi = set(
            SerieAssegnazione.objects.filter(serie=locked).values_list("indice", flat=True)
        )
        liberi = [i for i in range(1, totale + 1) if i not in presi]
        if not liberi:
            return {
                "nome": locked.nome,
                "totale": totale,
                "rimanenti": 0,
                "messaggio": f"La serie «{locked.nome}» è esaurita: tutti i {totale} pezzi sono stati trovati.",
            }, None, "serie_esaurita"

        indice = random.choice(liberi)
        nome_oggetto = f"{locked.nome} {indice} di {totale}"
        oggetto = Oggetto.objects.create(
            nome=nome_oggetto,
            testo=locked.descrizione or f"Pezzo della serie «{locked.nome}».",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
        )
        oggetto.sposta_in_inventario(personaggio)
        assegnazione = SerieAssegnazione.objects.create(
            serie=locked,
            indice=indice,
            personaggio=personaggio,
            oggetto=oggetto,
            qr_code=qr_code,
        )

    rimanenti = totale - len(presi) - 1
    return {
        "nome": locked.nome,
        "indice": indice,
        "totale": totale,
        "etichetta": nome_oggetto,
        "rimanenti": max(0, rimanenti),
        "oggetto_id": oggetto.pk,
        "assegnazione_id": str(assegnazione.pk),
        "messaggio": f"Hai trovato: {nome_oggetto}",
    }, None, None


def apply_pool_effect(
    *,
    effect,
    personaggio,
    qr_code,
    request=None,
) -> Dict[str, Any]:
    """Applica un RandomQrPoolEffect e ritorna il payload scan standard."""
    from .models import RandomQrPoolEffect
    from . import qr_logic

    tipo = effect.tipo
    base = {
        "pool_id": str(effect.pool_id),
        "effect_id": str(effect.pk),
        "effect_tipo": tipo,
        "qrcode_id": qr_code.id,
    }

    if tipo == RandomQrPoolEffect.TIPO_TESTO:
        titolo = (effect.titolo or effect.pool.nome or "Messaggio").strip()
        return {
            **base,
            "tipo_modello": "pool_testo",
            "messaggio": titolo,
            "dati": {
                "nome": titolo,
                "testo": effect.testo or "",
                "puo_leggere": True,
            },
        }

    if tipo == RandomQrPoolEffect.TIPO_NODO:
        if not effect.nodo_id:
            return {
                **base,
                "tipo_modello": "pool_errore",
                "messaggio": "Effetto nodo senza Nodo collegato.",
                "dati": {},
            }
        if not personaggio:
            return {
                "blocked": True,
                "error": "Parametro personaggio_id richiesto per effetto nodo.",
            }
        from .serializers import NodoSerializer

        res = qr_logic.applica_effetto_nodo_scan(personaggio, effect.nodo)
        if not res.get("ok"):
            if res.get("error") == "nodo_in_cooldown":
                return {
                    **base,
                    "tipo_modello": "nodo",
                    "messaggio": "Nodo in cooldown. Riprova più tardi.",
                    "dati": {
                        "nome": effect.nodo.nome,
                        "tipo_nodo": effect.nodo.tipo_nodo,
                        "cooldown_until": getattr(effect.nodo, "disponibile_dal", None),
                    },
                }
            return {"blocked": True, "error": "Impossibile attivare il nodo."}
        payload = dict(NodoSerializer(effect.nodo).data)
        payload.update(
            {
                "era_abbreviazione": res.get("era_abbreviazione"),
                "tipo_nodo_pre": res.get("tipo_nodo_pre"),
                "tipo_nodo_post": res.get("tipo_nodo_post"),
                "reward": {
                    "pool": res.get("pool"),
                    "crediti": res.get("crediti"),
                    "note": res.get("note"),
                },
                "cooldown_until": res.get("cooldown_until"),
            }
        )
        return {
            **base,
            "tipo_modello": "nodo",
            "messaggio": "Nodo attivato.",
            "dati": payload,
        }

    if tipo == RandomQrPoolEffect.TIPO_TRAPPOLA:
        if not personaggio:
            return {
                "blocked": True,
                "error": "Parametro personaggio_id richiesto per la trappola.",
            }
        nome = (effect.titolo or "Trappola").strip() or "Trappola"
        dati = applica_trappola(
            personaggio=personaggio,
            nome=nome,
            testo=effect.testo or "",
            durata_secondi=effect.durata_secondi,
            chiave=f"pool:{effect.pk}",
            trappola=None,
        )
        return {
            **base,
            "tipo_modello": "trappola",
            "messaggio": nome,
            "dati": dati,
        }

    if tipo == RandomQrPoolEffect.TIPO_SERIE:
        payload, err, override = applica_serie(
            personaggio=personaggio,
            serie=effect.serie,
            qr_code=qr_code,
        )
        if err:
            return {"blocked": True, "error": err}
        tipo_modello = override or "serie"
        return {
            **base,
            "tipo_modello": tipo_modello,
            "messaggio": (payload or {}).get("messaggio") or (payload or {}).get("nome") or "Serie",
            "dati": payload or {},
        }

    return {
        **base,
        "tipo_modello": "pool_errore",
        "messaggio": f"Tipo effetto sconosciuto: {tipo}",
        "dati": {},
    }


def handle_pool_qr_scan(
    *,
    qr_code,
    personaggio,
    request=None,
    bypass_session_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Se il QR appartiene a un pool attivo: gate minigioco + roll effetto.
    Ritorna None se il QR non è in un pool (flusso legacy).
    """
    from . import qr_minigioco

    pool = get_active_pool_for_qr(qr_code)
    if not pool:
        return None

    gate = qr_minigioco.check_gate_minigioco(
        qr_code=qr_code,
        personaggio=personaggio,
        request=request,
        bypass_session_id=bypass_session_id,
        config_override=resolve_minigioco_config_for_qr(qr_code),
    )
    if gate:
        return gate

    effect = scegli_effetto(pool)
    if not effect:
        return {
            "tipo_modello": "pool_errore",
            "messaggio": f"Il pool «{pool.nome}» non ha effetti attivi configurati.",
            "dati": {"pool_id": str(pool.pk), "pool_nome": pool.nome},
            "qrcode_id": qr_code.id,
        }

    result = apply_pool_effect(
        effect=effect,
        personaggio=personaggio,
        qr_code=qr_code,
        request=request,
    )
    if result.get("blocked"):
        return result
    result.setdefault("qrcode_id", qr_code.id)
    return result


def apply_trappola_standalone(*, trappola, personaggio, qr_code=None) -> Dict[str, Any]:
    """Applica trappola collegata via OneToOne QrCode (non A_vista)."""
    dati = applica_trappola(
        personaggio=personaggio,
        nome=trappola.nome or "Trappola",
        testo=trappola.testo or "",
        durata_secondi=trappola.durata_secondi,
        chiave=f"trappola:{trappola.pk}",
        trappola=trappola,
    )
    return {
        "tipo_modello": "trappola",
        "messaggio": trappola.nome or "Trappola",
        "dati": dati,
        "qrcode_id": getattr(qr_code, "id", None),
    }


# Alias retrocompatibile
apply_trappola_avista = apply_trappola_standalone


def apply_serie_standalone(*, serie_qr, personaggio, qr_code=None) -> Dict[str, Any]:
    """Applica serie da QR SerieQr (UUID + OneToOne)."""
    payload, err, override = applica_serie(
        personaggio=personaggio,
        serie=serie_qr.serie,
        qr_code=qr_code,
    )
    if err:
        return {"blocked": True, "error": err}
    return {
        "tipo_modello": override or "serie",
        "messaggio": (payload or {}).get("messaggio") or serie_qr.nome,
        "dati": payload or {},
        "qrcode_id": getattr(qr_code, "id", None),
    }


apply_serie_avista = apply_serie_standalone


def _conflict_payload(qr, *, tipo: str, nome: str, elemento_id) -> Dict[str, Any]:
    return {
        "error": "QR già associato",
        "already_associated": True,
        "qr_id": str(qr.id),
        "associazione_attuale": {
            "tipo": tipo,
            "nome": nome,
            "elemento_id": str(elemento_id),
        },
        "message": (
            f'Questo QR è già collegato a «{nome}» ({tipo}). '
            "Confermi di spostarlo?"
        ),
    }


def associa_qr_a_trappola(trappola, qr, *, force: bool = False) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Collega un QrCode a Trappola (OneToOne). Non usa QrCode.vista."""
    from .models import SerieQr, Trappola
    from .qr_logic import descrivi_avista_per_associazione_qr

    altro = Trappola.objects.filter(qr_code=qr).exclude(pk=trappola.pk).first()
    if altro and not force:
        return False, _conflict_payload(qr, tipo="trappola", nome=altro.nome, elemento_id=altro.pk)

    serie_altro = SerieQr.objects.filter(qr_code=qr).first()
    if serie_altro and not force:
        return False, _conflict_payload(
            qr, tipo="serie_qr", nome=serie_altro.nome, elemento_id=serie_altro.pk
        )

    if qr.vista_id and not force:
        info = descrivi_avista_per_associazione_qr(qr.vista) or {
            "tipo": "sconosciuto",
            "nome": getattr(qr.vista, "nome", "?"),
            "elemento_id": str(qr.vista_id),
        }
        return False, {
            "error": "QR già associato",
            "already_associated": True,
            "qr_id": str(qr.id),
            "associazione_attuale": info,
            "message": (
                f'Questo QR punta ancora a «{info["nome"]}» ({info["tipo"]}). '
                "Confermi di collegarlo a questa trappola?"
            ),
        }

    with transaction.atomic():
        Trappola.objects.filter(qr_code=qr).exclude(pk=trappola.pk).update(qr_code=None)
        SerieQr.objects.filter(qr_code=qr).update(qr_code=None)
        if qr.vista_id:
            qr.vista = None
            qr.save(update_fields=["vista", "updated_at"])
        trappola.qr_code = qr
        trappola.save(update_fields=["qr_code", "updated_at"])
    return True, None


def scollega_qr_da_trappola(trappola) -> None:
    if trappola.qr_code_id:
        trappola.qr_code = None
        trappola.save(update_fields=["qr_code", "updated_at"])


def associa_qr_a_serie_qr(serie_qr, qr, *, force: bool = False) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Collega un QrCode a SerieQr (OneToOne). Non usa QrCode.vista."""
    from .models import SerieQr, Trappola
    from .qr_logic import descrivi_avista_per_associazione_qr

    altro = SerieQr.objects.filter(qr_code=qr).exclude(pk=serie_qr.pk).first()
    if altro and not force:
        return False, _conflict_payload(qr, tipo="serie_qr", nome=altro.nome, elemento_id=altro.pk)

    trap_altro = Trappola.objects.filter(qr_code=qr).first()
    if trap_altro and not force:
        return False, _conflict_payload(
            qr, tipo="trappola", nome=trap_altro.nome, elemento_id=trap_altro.pk
        )

    if qr.vista_id and not force:
        info = descrivi_avista_per_associazione_qr(qr.vista) or {
            "tipo": "sconosciuto",
            "nome": getattr(qr.vista, "nome", "?"),
            "elemento_id": str(qr.vista_id),
        }
        return False, {
            "error": "QR già associato",
            "already_associated": True,
            "qr_id": str(qr.id),
            "associazione_attuale": info,
            "message": (
                f'Questo QR punta ancora a «{info["nome"]}» ({info["tipo"]}). '
                "Confermi di collegarlo a questo QR Serie?"
            ),
        }

    with transaction.atomic():
        SerieQr.objects.filter(qr_code=qr).exclude(pk=serie_qr.pk).update(qr_code=None)
        Trappola.objects.filter(qr_code=qr).update(qr_code=None)
        if qr.vista_id:
            qr.vista = None
            qr.save(update_fields=["vista", "updated_at"])
        serie_qr.qr_code = qr
        serie_qr.save(update_fields=["qr_code", "updated_at"])
    return True, None


def scollega_qr_da_serie_qr(serie_qr) -> None:
    if serie_qr.qr_code_id:
        serie_qr.qr_code = None
        serie_qr.save(update_fields=["qr_code", "updated_at"])
