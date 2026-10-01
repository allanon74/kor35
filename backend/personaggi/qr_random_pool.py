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
            RandomQrPoolMembership.objects.select_related("pool", "pool__minigioco_pattern")
            .prefetch_related("pool__effetti", "pool__minigioco_pattern__entries")
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
        self.pesi_difficolta = getattr(pool, "minigioco_pesi_difficolta", None) or {}
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
        self.pattern = getattr(pool, "minigioco_pattern", None)
        self.pattern_id = getattr(pool, "minigioco_pattern_id", None)
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


def _serie_immagine_url(serie_immagine) -> Optional[str]:
    """Path relativo (/media/…) per l'immagine assegnata; None se assente."""
    if not serie_immagine:
        return None
    field = getattr(serie_immagine, "immagine", None)
    if not field:
        return None
    try:
        url = field.url
    except (ValueError, AttributeError):
        return None
    return url or None


def scegli_immagine_serie(*, serie, indice: int, totale: int):
    """
    Seleziona l'immagine da associare all'indice assegnato.

    - 0 immagini → None
    - count >= totale → una diversa per indice, ordine alfabetico su nome_file_originale
      (usa le prime `totale` in ordine alfa)
    - count < totale → scelta random con ripetizioni
    """
    from .models import SerieImmagine

    immagini = list(
        SerieImmagine.objects.filter(serie=serie).order_by(
            "nome_file_originale", "created_at", "id"
        )
    )
    if not immagini:
        return None
    n = len(immagini)
    if n >= totale:
        # Indice 1..N → posizione 0..N-1 sulle prime N in ordine alfabetico
        pos = max(0, min(int(indice) - 1, totale - 1))
        return immagini[pos]
    return random.choice(immagini)


def _serie_rimanenti(serie, *, totale: Optional[int] = None) -> Optional[int]:
    totale = int(totale if totale is not None else (serie.totale or 0))
    if getattr(serie, "ammetti_duplicati", False):
        return None
    return max(0, totale - serie.assegnazioni.count())


def applica_serie(
    *,
    personaggio,
    serie,
    qr_code=None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Assegna un pezzo della serie all'inventario serie del personaggio.
    Ritorna (payload, errore, tipo_modello_override).
    tipo_modello_override = 'serie_esaurita' se non restano pezzi (solo senza duplicati).

    Senza `ammetti_duplicati`: indici unici 1..N; ogni QR fisico assegna al massimo
    un pezzo (anti-farm globale sul QR).
    Con `ammetti_duplicati`: indici ripetibili; stesso QR una volta per personaggio.
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
        ammetti_dup = bool(locked.ammetti_duplicati)

        if qr_code is not None:
            gia_stesso_pg = (
                SerieAssegnazione.objects.select_for_update(of=("self",))
                .filter(qr_code=qr_code, personaggio=personaggio)
                .first()
            )
            if gia_stesso_pg is not None:
                img = (
                    gia_stesso_pg.immagine
                    if gia_stesso_pg.immagine_id
                    else None
                )
                return {
                    "nome": locked.nome,
                    "indice": gia_stesso_pg.indice,
                    "totale": totale,
                    "etichetta": f"{locked.nome} {gia_stesso_pg.indice} di {totale}",
                    "rimanenti": _serie_rimanenti(locked, totale=totale),
                    "oggetto_id": gia_stesso_pg.oggetto_id,
                    "assegnazione_id": str(gia_stesso_pg.pk),
                    "immagine_url": _serie_immagine_url(img),
                    "messaggio": (
                        f"Hai già riscosso questo QR: "
                        f"{locked.nome} {gia_stesso_pg.indice} di {totale}."
                    ),
                    "gia_riscattato": True,
                    "in_inventario_serie": True,
                }, None, "serie"

            if not ammetti_dup:
                gia_altro = (
                    SerieAssegnazione.objects.select_for_update(of=("self",))
                    .filter(qr_code=qr_code)
                    .exclude(personaggio=personaggio)
                    .first()
                )
                if gia_altro is not None:
                    return (
                        None,
                        "Questo QR della serie è già stato riscosso da un altro personaggio.",
                        None,
                    )

        if ammetti_dup:
            liberi = list(range(1, totale + 1))
        else:
            presi = set(
                SerieAssegnazione.objects.filter(serie=locked).values_list("indice", flat=True)
            )
            liberi = [i for i in range(1, totale + 1) if i not in presi]
            if not liberi:
                return {
                    "nome": locked.nome,
                    "totale": totale,
                    "rimanenti": 0,
                    "immagine_url": None,
                    "messaggio": (
                        f"La serie «{locked.nome}» è esaurita: "
                        f"tutti i {totale} pezzi sono stati trovati."
                    ),
                }, None, "serie_esaurita"

        indice = random.choice(liberi)
        nome_oggetto = f"{locked.nome} {indice} di {totale}"
        # Metadata oggetto: resta fuori dallo zaino generico (inventario serie dedicato).
        oggetto = Oggetto.objects.create(
            nome=nome_oggetto,
            testo=locked.descrizione or f"Pezzo della serie «{locked.nome}».",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
        )
        img = scegli_immagine_serie(serie=locked, indice=indice, totale=totale)
        assegnazione = SerieAssegnazione.objects.create(
            serie=locked,
            indice=indice,
            personaggio=personaggio,
            oggetto=oggetto,
            qr_code=qr_code,
            immagine=img,
        )

    return {
        "nome": locked.nome,
        "indice": indice,
        "totale": totale,
        "etichetta": nome_oggetto,
        "rimanenti": _serie_rimanenti(locked, totale=totale),
        "oggetto_id": oggetto.pk,
        "assegnazione_id": str(assegnazione.pk),
        "immagine_url": _serie_immagine_url(img),
        "messaggio": f"Hai trovato: {nome_oggetto}. Aggiunto all'inventario serie.",
        "in_inventario_serie": True,
    }, None, None


def serializza_assegnazione_serie(ass, *, request=None) -> Dict[str, Any]:
    """Payload pezzo per inventario serie / staff."""
    img_url = _serie_immagine_url(ass.immagine)
    if request is not None and img_url and img_url.startswith("/"):
        try:
            img_url = request.build_absolute_uri(img_url)
        except Exception:
            pass
    return {
        "id": str(ass.pk),
        "serie_id": str(ass.serie_id),
        "serie_nome": ass.serie.nome,
        "indice": ass.indice,
        "totale": ass.serie.totale,
        "etichetta": ass.etichetta,
        "immagine_url": img_url,
        "assegnato_at": ass.assegnato_at.isoformat() if ass.assegnato_at else None,
        "oggetto_id": ass.oggetto_id,
        "personaggio_id": ass.personaggio_id,
        "personaggio_nome": getattr(ass.personaggio, "nome", None),
        "qr_code_id": str(ass.qr_code_id) if ass.qr_code_id else None,
    }


def inventario_serie_per_personaggio(personaggio, *, request=None) -> List[Dict[str, Any]]:
    """
    Pezzi nell'inventario serie del PG, raggruppati per serie.
    Esclude serie legate solo a eventi chiusi.
    """
    from .models import SerieAssegnazione

    qs = (
        SerieAssegnazione.objects.filter(personaggio=personaggio)
        .select_related("serie", "immagine", "personaggio")
        .prefetch_related("serie__eventi")
        .order_by("serie__nome", "indice", "assegnato_at")
    )
    by_serie: Dict[str, Dict[str, Any]] = {}
    for ass in qs:
        serie = ass.serie
        if not serie.inventario_visibile():
            continue
        key = str(serie.pk)
        if key not in by_serie:
            by_serie[key] = {
                "serie_id": key,
                "serie_nome": serie.nome,
                "totale": serie.totale,
                "descrizione": serie.descrizione or "",
                "ammetti_duplicati": bool(serie.ammetti_duplicati),
                "pezzi": [],
            }
        by_serie[key]["pezzi"].append(serializza_assegnazione_serie(ass, request=request))
    return list(by_serie.values())


def trasferisci_assegnazione_serie(
    *,
    assegnazione,
    destinatario,
    mittente=None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Sposta un pezzo di inventario serie a un altro personaggio."""
    from .models import SerieAssegnazione

    if destinatario is None:
        return None, "Destinatario mancante."
    if mittente is not None and assegnazione.personaggio_id != mittente.pk:
        return None, "Questo pezzo non è nel tuo inventario serie."
    if assegnazione.personaggio_id == destinatario.pk:
        return None, "Il pezzo è già di questo personaggio."
    if not assegnazione.serie.inventario_visibile():
        return None, "Questa serie non è trasferibile (evento chiuso)."

    with transaction.atomic():
        locked = (
            SerieAssegnazione.objects.select_for_update(of=("self",))
            .select_related("serie", "personaggio", "oggetto")
            .get(pk=assegnazione.pk)
        )
        if mittente is not None and locked.personaggio_id != mittente.pk:
            return None, "Questo pezzo non è nel tuo inventario serie."
        locked.personaggio = destinatario
        locked.save(update_fields=["personaggio", "updated_at"])
        # Pezzi legacy nello zaino: sposta l'oggetto al destinatario.
        oggetto = locked.oggetto
        if oggetto is not None:
            try:
                if oggetto.inventario_corrente is not None:
                    oggetto.sposta_in_inventario(destinatario)
            except Exception:
                pass

    locked.refresh_from_db()
    locked = SerieAssegnazione.objects.select_related(
        "serie", "immagine", "personaggio"
    ).get(pk=locked.pk)
    return serializza_assegnazione_serie(locked), None


def reset_serie_collezione(serie) -> Dict[str, Any]:
    """
    Rimuove tutte le assegnazioni (inventario serie) e gli oggetti collegati.
    La consegna riparte da zero; le immagini della collezione restano.
    """
    from .models import Oggetto, SerieAssegnazione

    with transaction.atomic():
        locked = type(serie).objects.select_for_update().get(pk=serie.pk)
        # of=("self",) evita OUTER JOIN su FK nullable (oggetto/immagine).
        assegnazioni = list(
            SerieAssegnazione.objects.select_for_update(of=("self",)).filter(serie=locked)
        )
        oggetto_ids = [a.oggetto_id for a in assegnazioni if a.oggetto_id]
        n = len(assegnazioni)
        SerieAssegnazione.objects.filter(serie=locked).delete()
        if oggetto_ids:
            # Elimina oggetti orfani creati per i pezzi (anche se erano nello zaino).
            Oggetto.objects.filter(pk__in=oggetto_ids).delete()

    return {
        "serie_id": str(locked.pk),
        "serie_nome": locked.nome,
        "assegnazioni_rimosse": n,
        "messaggio": (
            f"Serie «{locked.nome}» resettata: rimossi {n} pezzi dagli inventari. "
            "La consegna riparte da zero."
        ),
    }


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
                "salvabile": True,
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

    if tipo == RandomQrPoolEffect.TIPO_MANIFESTO:
        if not effect.manifesto_id:
            return {
                **base,
                "tipo_modello": "pool_errore",
                "messaggio": "Effetto manifesto senza Manifesto collegato.",
                "dati": {},
            }
        dati = qr_logic.risolvi_payload_manifesto(effect.manifesto, personaggio)
        dati["non_salvabile"] = bool(getattr(effect.manifesto, "non_salvabile", False))
        dati["salvabile"] = not dati["non_salvabile"]
        return {
            **base,
            "tipo_modello": "manifesto",
            "messaggio": dati.get("nome") or "Manifesto",
            "dati": dati,
        }

    if tipo == RandomQrPoolEffect.TIPO_NEGOZIO_MERCANTE:
        if not effect.negozio_mercante_id:
            return {
                **base,
                "tipo_modello": "pool_errore",
                "messaggio": "Effetto negozio senza mercante collegato.",
                "dati": {},
            }
        if not personaggio:
            return {
                "blocked": True,
                "error": "Parametro personaggio_id richiesto per il negozio mercante.",
            }
        negozio = effect.negozio_mercante
        if not negozio or not negozio.attivo:
            return {
                **base,
                "tipo_modello": "pool_errore",
                "messaggio": "Negozio mercante non disponibile.",
                "dati": {},
            }
        from personaggi.negozio_mercante_service import build_listino

        listino = build_listino(negozio, personaggio)
        return {
            **base,
            "tipo_modello": "negozio_mercante",
            "messaggio": listino.get("messaggio_accesso") or f"Negozio: {negozio.nome}",
            "dati": listino,
        }

    if tipo == RandomQrPoolEffect.TIPO_OGGETTO_BASE:
        if not personaggio:
            return {
                "blocked": True,
                "error": "Parametro personaggio_id richiesto per l'oggetto.",
            }
        if not effect.oggetto_base_id:
            return {
                **base,
                "tipo_modello": "pool_errore",
                "messaggio": "Effetto oggetto senza template listino collegato.",
                "dati": {},
            }
        from .services import GestioneCraftingService

        with transaction.atomic():
            oggetto = GestioneCraftingService.crea_istanza_da_oggetto_base(
                effect.oggetto_base, personaggio
            )
        return {
            **base,
            "tipo_modello": "pool_loot",
            "messaggio": f"Hai trovato: {oggetto.nome}",
            "dati": {
                "kind": "oggetto",
                "nome": oggetto.nome,
                "oggetto_id": oggetto.pk,
                "template_id": effect.oggetto_base_id,
                "messaggio": f"Hai trovato: {oggetto.nome}",
                "gia_assegnato": True,
            },
        }

    if tipo == RandomQrPoolEffect.TIPO_DA_INFUSIONE:
        if not personaggio:
            return {
                "blocked": True,
                "error": "Parametro personaggio_id richiesto per Materia/Mod.",
            }
        if not effect.infusione_id:
            return {
                **base,
                "tipo_modello": "pool_errore",
                "messaggio": "Effetto Materia/Mod senza Infusione (matrice) collegata.",
                "dati": {},
            }
        from .services import GestioneOggettiService

        with transaction.atomic():
            oggetto = GestioneOggettiService.crea_oggetto_da_infusione(
                effect.infusione, personaggio
            )
        return {
            **base,
            "tipo_modello": "pool_loot",
            "messaggio": f"Hai trovato: {oggetto.nome}",
            "dati": {
                "kind": "oggetto",
                "tipo_oggetto": oggetto.tipo_oggetto,
                "nome": oggetto.nome,
                "oggetto_id": oggetto.pk,
                "infusione_id": effect.infusione_id,
                "messaggio": f"Hai trovato: {oggetto.nome}",
                "gia_assegnato": True,
            },
        }

    if tipo in (
        RandomQrPoolEffect.TIPO_TESSITURA,
        RandomQrPoolEffect.TIPO_INFUSIONE,
        RandomQrPoolEffect.TIPO_CERIMONIALE,
        RandomQrPoolEffect.TIPO_ATTIVATA,
    ):
        if not personaggio:
            return {
                "blocked": True,
                "error": "Parametro personaggio_id richiesto per la tecnica.",
            }
        tecnica = None
        m2m = None
        if tipo == RandomQrPoolEffect.TIPO_TESSITURA:
            tecnica = effect.tessitura
            m2m = personaggio.tessiture_possedute
        elif tipo == RandomQrPoolEffect.TIPO_INFUSIONE:
            tecnica = effect.infusione
            m2m = personaggio.infusioni_possedute
        elif tipo == RandomQrPoolEffect.TIPO_CERIMONIALE:
            tecnica = effect.cerimoniale
            m2m = personaggio.cerimoniali_posseduti
        elif tipo == RandomQrPoolEffect.TIPO_ATTIVATA:
            tecnica = effect.attivata
            m2m = personaggio.attivate_possedute

        if not tecnica:
            return {
                **base,
                "tipo_modello": "pool_errore",
                "messaggio": f"Effetto {tipo} senza tecnica collegata.",
                "dati": {},
            }

        gia = m2m.filter(pk=tecnica.pk).exists()
        if not gia:
            with transaction.atomic():
                m2m.add(tecnica)
        nome = getattr(tecnica, "nome", None) or str(tecnica.pk)
        return {
            **base,
            "tipo_modello": "pool_loot",
            "messaggio": (
                f"Possedevi già: {nome}" if gia else f"Hai appreso: {nome}"
            ),
            "dati": {
                "kind": tipo,
                "nome": nome,
                "tecnica_id": tecnica.pk,
                "gia_posseduta": gia,
                "gia_assegnato": True,
                "messaggio": (
                    f"Possedevi già: {nome}" if gia else f"Hai appreso: {nome}"
                ),
            },
        }

    return {
        **base,
        "tipo_modello": "pool_errore",
        "messaggio": f"Tipo effetto sconosciuto: {tipo}",
        "dati": {},
    }


def _apply_pool_qr_cooldown(*, membership, pool):
    """
    Spegnimento QR fisico stilizzato come i nodi: range minuti sul pool → disponibile_dal.
    Ritorna il datetime di riattivazione, o None se cooldown disattivo.
    """
    if not getattr(pool, "cooldown_attivo", False):
        return None
    cd_min = max(1, int(pool.cooldown_minuti_min or 5))
    cd_max = max(cd_min, int(pool.cooldown_minuti_max or 25))
    cd_minutes = random.randint(cd_min, cd_max)
    now = timezone.now()
    until = now + timedelta(minutes=cd_minutes)
    membership.ultima_scansione_at = now
    membership.disponibile_dal = until
    membership.save(update_fields=["ultima_scansione_at", "disponibile_dal", "updated_at"])
    return until


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
    from .models import RandomQrPoolClaim, RandomQrPoolMembership

    membership = get_pool_membership(qr_code)
    if not membership or not membership.pool.attivo:
        return None
    pool = membership.pool

    # Spegnimento globale del QR fisico (prima del claim per-PG).
    now = timezone.now()
    if membership.disponibile_dal and now < membership.disponibile_dal:
        rem = int((membership.disponibile_dal - now).total_seconds())
        return {
            "tipo_modello": "pool_cooldown",
            "messaggio": "Questo QR è temporaneamente spento. Riprova più tardi.",
            "dati": {
                "pool_id": str(pool.pk),
                "pool_nome": pool.nome,
                "cooldown_until": membership.disponibile_dal,
                "remaining_seconds": max(rem, 0),
            },
            "qrcode_id": qr_code.id,
        }

    gate = qr_minigioco.check_gate_minigioco(
        qr_code=qr_code,
        personaggio=personaggio,
        request=request,
        bypass_session_id=bypass_session_id,
        config_override=resolve_minigioco_config_for_qr(qr_code),
    )
    if gate:
        return gate

    # Anti-farm: un personaggio può ottenere un solo effetto da ciascun QR del pool.
    if personaggio is not None and RandomQrPoolClaim.objects.filter(
        personaggio=personaggio, qr_code=qr_code
    ).exists():
        return {
            "tipo_modello": "pool_errore",
            "messaggio": "Hai già usato questo QR del pool.",
            "dati": {
                "pool_id": str(pool.pk),
                "pool_nome": pool.nome,
                "gia_usato": True,
            },
            "qrcode_id": qr_code.id,
        }

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
    if personaggio is not None and result.get("tipo_modello") != "pool_errore":
        with transaction.atomic():
            RandomQrPoolClaim.objects.get_or_create(
                personaggio=personaggio,
                qr_code=qr_code,
                defaults={"pool": pool},
            )
            locked = (
                RandomQrPoolMembership.objects.select_for_update()
                .select_related("pool")
                .get(pk=membership.pk)
            )
            until = _apply_pool_qr_cooldown(membership=locked, pool=locked.pool)
            if until is not None:
                result.setdefault("dati", {})
                if isinstance(result.get("dati"), dict):
                    result["dati"]["cooldown_until"] = until
                    result["dati"]["pool_cooldown"] = True
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


def _media_relpath(field_file) -> str:
    if not field_file:
        return ""
    try:
        name = getattr(field_file, "name", None) or ""
    except (ValueError, AttributeError):
        return ""
    return str(name)


def serializza_documento_archiviato(doc, *, request=None) -> Dict[str, Any]:
    """Payload lettura per «Serie e testi» (senza minigioco)."""

    def _url(rel: str) -> Optional[str]:
        if not rel:
            return None
        # Path relativo tipo /media/... per il frontend
        if str(rel).startswith("/"):
            return str(rel)
        return f"/media/{rel.lstrip('/')}"

    testo_cond = (doc.testo_condizionato or "").strip()
    return {
        "id": str(doc.pk),
        "kind": "documento",
        "tipo": doc.tipo,
        "titolo": doc.titolo,
        "etichetta": doc.titolo,
        "testo": doc.testo or "",
        "testo_condizionato": testo_cond or None,
        "mostra_testo_condizionato": bool(testo_cond),
        "immagine_url": _url(doc.immagine_path),
        "audio_url": _url(doc.audio_path),
        "video_url": _url(doc.video_path),
        "puo_leggere": True,
        "salvato_at": doc.salvato_at.isoformat() if doc.salvato_at else None,
        "manifesto_id": doc.manifesto_id,
        "personaggio_id": doc.personaggio_id,
    }


def salva_documento_da_scan(
    *,
    personaggio,
    tipo: str,
    titolo: str,
    testo: str = "",
    testo_condizionato: str = "",
    manifesto=None,
    immagine_url: str = "",
    audio_url: str = "",
    video_url: str = "",
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Archivia snapshot manifesto/testo nell'inventario «Serie e testi».
    """
    from .models import DocumentoArchiviato, Manifesto

    tipo = (tipo or "").strip().lower()
    if tipo not in (DocumentoArchiviato.TIPO_MANIFESTO, DocumentoArchiviato.TIPO_TESTO):
        return None, "Tipo non valido (manifesto|testo)."
    if personaggio is None:
        return None, "Personaggio mancante."
    titolo = (titolo or "").strip() or ("Manifesto" if tipo == "manifesto" else "Testo")
    testo = testo or ""

    if tipo == DocumentoArchiviato.TIPO_MANIFESTO:
        if manifesto is not None and getattr(manifesto, "non_salvabile", False):
            return None, "Questo manifesto non è salvabile."
        if manifesto is None and not testo.strip():
            return None, "Contenuto manifesto vuoto."

    def _strip_media(url: str) -> str:
        u = (url or "").strip()
        if not u:
            return ""
        if u.startswith("/media/"):
            return u[len("/media/") :]
        if u.startswith("media/"):
            return u[len("media/") :]
        # Absolute URL → path after /media/
        idx = u.find("/media/")
        if idx >= 0:
            return u[idx + len("/media/") :]
        return u.lstrip("/")

    img = _strip_media(immagine_url)
    aud = _strip_media(audio_url)
    vid = _strip_media(video_url)

    if manifesto is not None and isinstance(manifesto, Manifesto):
        if not img:
            img = _media_relpath(getattr(manifesto, "immagine_file", None))
        if not aud:
            aud = _media_relpath(getattr(manifesto, "audio_file", None))
        if not vid:
            vid = _media_relpath(getattr(manifesto, "video_file", None))
        if not testo and manifesto.testo:
            testo = manifesto.testo

    with transaction.atomic():
        doc = DocumentoArchiviato.objects.create(
            personaggio=personaggio,
            tipo=tipo,
            titolo=titolo[:200],
            testo=testo,
            testo_condizionato=testo_condizionato or "",
            manifesto=manifesto if tipo == DocumentoArchiviato.TIPO_MANIFESTO else None,
            immagine_path=img[:500],
            audio_path=aud[:500],
            video_path=vid[:500],
        )
    return serializza_documento_archiviato(doc), None


def inventario_documenti_per_personaggio(personaggio, *, request=None) -> List[Dict[str, Any]]:
    from .models import DocumentoArchiviato

    qs = DocumentoArchiviato.objects.filter(personaggio=personaggio).order_by(
        "-salvato_at", "-created_at"
    )
    return [serializza_documento_archiviato(d, request=request) for d in qs]


def trasferisci_documento_archiviato(
    *,
    documento,
    destinatario,
    mittente=None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    from .models import DocumentoArchiviato

    if destinatario is None:
        return None, "Destinatario mancante."
    if mittente is not None and documento.personaggio_id != mittente.pk:
        return None, "Questo documento non è nel tuo archivio."
    if documento.personaggio_id == destinatario.pk:
        return None, "Il documento è già di questo personaggio."

    with transaction.atomic():
        locked = DocumentoArchiviato.objects.select_for_update().get(pk=documento.pk)
        if mittente is not None and locked.personaggio_id != mittente.pk:
            return None, "Questo documento non è nel tuo archivio."
        locked.personaggio = destinatario
        locked.save(update_fields=["personaggio", "updated_at"])
    locked.refresh_from_db()
    return serializza_documento_archiviato(locked), None


def elimina_documento_archiviato(*, documento, personaggio) -> Optional[str]:
    if documento.personaggio_id != personaggio.pk:
        return "Questo documento non è nel tuo archivio."
    documento.delete()
    return None


def elimina_assegnazione_serie(*, assegnazione, personaggio) -> Optional[str]:
    """Il giocatore elimina un pezzo serie dal proprio inventario."""
    from .models import Oggetto, SerieAssegnazione

    if assegnazione.personaggio_id != personaggio.pk:
        return "Questo pezzo non è nel tuo inventario serie."
    with transaction.atomic():
        locked = (
            SerieAssegnazione.objects.select_for_update(of=("self",))
            .select_related("oggetto")
            .get(pk=assegnazione.pk)
        )
        if locked.personaggio_id != personaggio.pk:
            return "Questo pezzo non è nel tuo inventario serie."
        oggetto_id = locked.oggetto_id
        locked.delete()
        if oggetto_id:
            Oggetto.objects.filter(pk=oggetto_id).delete()
    return None
