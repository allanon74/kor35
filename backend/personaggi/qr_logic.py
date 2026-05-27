"""
Logica QR lato server: manifesti, inventario a doppia scansione, innesco timer, permessi oggetti.
"""
from __future__ import annotations

from datetime import timedelta
import random
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def personaggio_soddisfa_requisiti_manifesto(personaggio, manifesto) -> Tuple[bool, str]:
    """Ritorna (ok, messaggio). Lista requisiti vuota = accesso libero."""
    from .models import Abilita, Statistica

    reqs = manifesto.requisiti_lettura or []
    if not reqs:
        return True, ""

    for req in reqs:
        if not isinstance(req, dict):
            continue
        tipo = (req.get("tipo") or "").strip().lower()
        if tipo == "statistica":
            sigla = (req.get("sigla") or "").strip().upper()
            min_v = int(req.get("min", 1) or 1)
            if not sigla:
                continue
            cur = personaggio.get_valore_statistica(sigla)
            if cur < min_v:
                st = Statistica.objects.filter(sigla=sigla).first()
                nome = st.nome if st else sigla
                return False, f"Richiesto {nome} ({sigla}) ≥ {min_v} (hai {cur})."
        elif tipo == "abilita":
            aid = req.get("id")
            if aid is None:
                continue
            if not personaggio.abilita_possedute.filter(pk=aid).exists():
                ab = Abilita.objects.filter(pk=aid).first()
                nome = ab.nome if ab else str(aid)
                return False, f"È richiesta l'abilità: {nome}."
        elif tipo == "punteggio":
            # Alias: valore aura per nome punteggio (tipo AURA)
            from .models import Punteggio, AURA

            nome = (req.get("nome") or "").strip()
            min_v = int(req.get("min", 1) or 1)
            if not nome:
                continue
            p = Punteggio.objects.filter(nome=nome, tipo=AURA).first()
            if not p:
                return False, f"Requisito aura sconosciuto: {nome}."
            cur = personaggio.get_valore_aura_effettivo(p)
            if cur < min_v:
                return False, f"Richiesta aura {nome} ≥ {min_v} (hai {cur})."
    return True, ""


def permessi_oggetto_inventario_qr(personaggio, oggetto) -> Dict[str, Any]:
    """
    Visibilità e azioni per oggetti in inventario scansionato via QR (non PG).
    """
    from .models import (
        TIPO_OGGETTO_FISICO,
        TIPO_OGGETTO_MATERIA,
        TIPO_OGGETTO_MOD,
        TIPO_OGGETTO_POTENZIAMENTO,
        TIPO_OGGETTO_INNESTO,
        TIPO_OGGETTO_MUTAZIONE,
        TIPO_OGGETTO_AUMENTO,
    )

    livello = oggetto.livello or 0
    if oggetto.aura_id:
        visibile = personaggio.get_valore_aura_effettivo(oggetto.aura) >= 1
    else:
        visibile = True

    libero = not oggetto.ospitato_su_id

    is_mat = oggetto.tipo_oggetto == TIPO_OGGETTO_MATERIA or (
        oggetto.tipo_oggetto == TIPO_OGGETTO_POTENZIAMENTO and not oggetto.is_tecnologico
    )
    is_mod = oggetto.tipo_oggetto == TIPO_OGGETTO_MOD or (
        oggetto.tipo_oggetto == TIPO_OGGETTO_POTENZIAMENTO and oggetto.is_tecnologico
    )

    ams = personaggio.get_valore_statistica("AMS")
    ate = personaggio.get_valore_statistica("ATE")

    # Prendi: materia/mod "liberi" (non montati) se visibili; altri tipi se visibili
    puo_prendere = False
    if visibile:
        if is_mat or is_mod:
            puo_prendere = libero
        elif oggetto.tipo_oggetto in (
            TIPO_OGGETTO_FISICO,
            TIPO_OGGETTO_INNESTO,
            TIPO_OGGETTO_MUTAZIONE,
            TIPO_OGGETTO_AUMENTO,
        ):
            puo_prendere = True

    puo_smonta_materia = visibile and is_mat and ams >= livello
    puo_smonta_mod = visibile and is_mod and ate >= livello

    return {
        "visibile_inventario_qr": visibile,
        "puo_prendere": puo_prendere,
        "puo_smonta_materia": puo_smonta_materia,
        "puo_smonta_mod": puo_smonta_mod,
    }


def personaggio_match_innesco_timer(personaggio, innesco) -> bool:
    from .models import InnescoTimer, PersonaggioCarrieraMembership

    if innesco.modalita_target == InnescoTimer.INNESCO_TARGET_GLOBAL:
        return True

    checks: List[bool] = []
    if innesco.target_ere.exists():
        checks.append(bool(personaggio.era_id and innesco.target_ere.filter(pk=personaggio.era_id).exists()))
    if innesco.target_regioni.exists():
        reg_id = getattr(getattr(personaggio, "prefettura", None), "regione_id", None)
        checks.append(bool(reg_id and innesco.target_regioni.filter(pk=reg_id).exists()))
    if innesco.target_korps.exists():
        ok_k = PersonaggioCarrieraMembership.objects.filter(
            personaggio=personaggio,
            data_a__isnull=True,
            carriera__in=innesco.target_korps.all(),
        ).exists()
        checks.append(ok_k)
    if not checks:
        return True
    return all(checks)


def _broadcast_timer_innesco(
    *,
    nome: str,
    data_fine,
    segnale_luminoso: bool,
    recipient_personaggio_ids: List[int],
):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "kor35_notifications",
        {
            "type": "send_notification",
            "message": {
                "action": "TIMER_INNESCO_SYNC",
                "payload": {
                    "nome": nome,
                    "data_fine": data_fine.isoformat(),
                    "segnale_luminoso": segnale_luminoso,
                    "recipient_personaggio_ids": recipient_personaggio_ids,
                },
            },
        },
    )


def attiva_innesco_timer_per_personaggio(
    personaggio,
    innesco,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Aggiorna stato cariche, imposta countdown e invia push websocket ai destinatari mirati.
    Ritorna (payload risposta scan, errore).
    """
    from .models import InnescoTimer, Personaggio, StatoInnescoTimerPersonaggio

    if not personaggio_match_innesco_timer(personaggio, innesco):
        return None, "Il tuo personaggio non rientra nel target di questo innesco timer."

    now = timezone.now()
    max_c = int(innesco.max_cariche or 0)
    regen = innesco.rigenera_cariche_ogni_secondi

    with transaction.atomic():
        stato, _created = StatoInnescoTimerPersonaggio.objects.select_for_update().get_or_create(
            personaggio=personaggio,
            innesco_timer=innesco,
            defaults={
                "data_fine": now,
                "cariche_usate_ciclo": 0,
                "ciclo_iniziato_at": now,
            },
        )

        if max_c > 0:
            # Rigenera cariche dopo intervallo (da fine ultimo ciclo esaurito)
            if stato.cariche_usate_ciclo >= max_c and regen and stato.ciclo_iniziato_at:
                prossima = stato.ciclo_iniziato_at + timedelta(seconds=int(regen))
                if now >= prossima:
                    stato.cariche_usate_ciclo = 0
                else:
                    sec = max(0, int((prossima - now).total_seconds()))
                    return None, f"Cariche esaurite. Prossima rigenerazione tra ~{sec}s."
            elif stato.cariche_usate_ciclo >= max_c and not regen:
                return None, "Cariche esaurite per questo innesco."

        stato.data_fine = now + timedelta(seconds=int(innesco.durata_secondi or 60))
        if max_c > 0:
            stato.cariche_usate_ciclo += 1
            if stato.cariche_usate_ciclo >= max_c:
                stato.ciclo_iniziato_at = now
        stato.save()

    # destinatari broadcast
    if innesco.modalita_target == InnescoTimer.INNESCO_TARGET_GLOBAL:
        ids = list(Personaggio.objects.filter(tipologia__giocante=True).values_list("id", flat=True)[:5000])
    else:
        ids = []
        for pg in Personaggio.objects.filter(tipologia__giocante=True).select_related(
            "era", "prefettura", "prefettura__regione"
        ):
            if personaggio_match_innesco_timer(pg, innesco):
                ids.append(pg.id)

    _broadcast_timer_innesco(
        nome=innesco.nome,
        data_fine=stato.data_fine,
        segnale_luminoso=innesco.segnale_luminoso,
        recipient_personaggio_ids=ids,
    )

    return {
        "nome": innesco.nome,
        "scadenza": stato.data_fine,
        "segnale_luminoso": innesco.segnale_luminoso,
        "recipient_personaggio_ids": ids,
    }, None


def gestisci_scansione_inventario_qr(
    *,
    user,
    personaggio,
    qr_code,
    inventario,
) -> Dict[str, Any]:
    """
    Gestisce prima scansione (attesa) o seconda scansione (dati completi).
    """
    from .models import INVENTARIO_QR_ATTESA_SECONDI, QrInventarioScanSession

    now = timezone.now()
    with transaction.atomic():
        sess = (
            QrInventarioScanSession.objects.select_for_update()
            .filter(
                user=user,
                qr_code=qr_code,
                inventario=inventario,
                confermato_at__isnull=True,
            )
            .order_by("-first_scan_at")
            .first()
        )

        if sess and sess.personaggio_id != personaggio.pk:
            sess.delete()
            sess = None

        if not sess:
            sess = QrInventarioScanSession.objects.create(
                user=user,
                personaggio=personaggio,
                qr_code=qr_code,
                inventario=inventario,
            )
            return {
                "fase": "attesa",
                "session_id": str(sess.id),
                "attesa_secondi": INVENTARIO_QR_ATTESA_SECONDI,
                "pronto_dopo": (sess.first_scan_at + timedelta(seconds=INVENTARIO_QR_ATTESA_SECONDI)).isoformat(),
            }

        delta = now - sess.first_scan_at
        if delta.total_seconds() < INVENTARIO_QR_ATTESA_SECONDI:
            resta = int(INVENTARIO_QR_ATTESA_SECONDI - delta.total_seconds())
            return {
                "fase": "attesa",
                "session_id": str(sess.id),
                "attesa_secondi": resta,
                "pronto_dopo": (sess.first_scan_at + timedelta(seconds=INVENTARIO_QR_ATTESA_SECONDI)).isoformat(),
            }

        sess.confermato_at = now
        sess.save(update_fields=["confermato_at", "updated_at"])

    return {"fase": "confermato", "session_id": str(sess.id)}


def oggetto_puo_essere_acquisito_da_qr(personaggio, oggetto) -> Tuple[bool, str]:
    """Regola QR oggetto: almeno 1 nell'aura dell'oggetto, oppure oggetto senza aura."""
    if not oggetto.aura_id:
        return True, ""
    v = personaggio.get_valore_aura_effettivo(oggetto.aura)
    if v >= 1:
        return True, ""
    return False, "Non possiedi un punteggio sufficiente nell'aura richiesta per prendere questo oggetto."


def _abbr_era(pg) -> str:
    return ((getattr(getattr(pg, "era", None), "abbreviazione", "") or "").strip().casefold())


def _find_tipologia_by_candidates(candidates: List[str]):
    from .models import TipologiaEffetto

    for name in candidates:
        row = TipologiaEffetto.objects.filter(nome__icontains=name).order_by("id").first()
        if row:
            return row
    return None


def applica_effetto_nodo_scan(personaggio, nodo) -> Dict[str, Any]:
    """
    Applica reward nodo in base all'era del personaggio.
    - Minore: reward base
    - Maggiore: reward x2
    Dopo la scansione imposta cooldown random 5..25 min e muta stato (10% MAG).
    """
    from .models import (
        NODO_REWARD_CREDITI,
        NODO_REWARD_POOL,
        TIPO_NODO_MAGGIORE,
        TIPO_NODO_MINORE,
    )

    now = timezone.now()
    if nodo.disponibile_dal and now < nodo.disponibile_dal:
        rem = int((nodo.disponibile_dal - now).total_seconds())
        return {"ok": False, "error": "nodo_in_cooldown", "remaining_seconds": max(rem, 0)}

    abbr = _abbr_era(personaggio)
    is_maggiore = nodo.tipo_nodo == TIPO_NODO_MAGGIORE
    mult = 2 if is_maggiore else 1
    rewards: Dict[str, Any] = {"era_abbreviazione": abbr, "tipo_nodo_pre": nodo.tipo_nodo}

    with transaction.atomic():
        # Prima scelta: configurazione DB (reward_config) sul nodo.
        # Fallback legacy hardcoded mantenuto per i nodi preesistenti/non configurati.
        applied_from_config = False
        cfg = getattr(nodo, "reward_config", None)
        if cfg and getattr(personaggio, "era_id", None):
            regola = (
                cfg.regole_era.select_related("statistica_pool")
                .filter(era_id=personaggio.era_id)
                .first()
            )
            if regola:
                delta_effettivo = int(regola.delta_base or 0) * mult
                if regola.tipo_reward == NODO_REWARD_POOL and regola.statistica_pool_id and delta_effettivo:
                    sigla = (regola.statistica_pool.sigla or "").strip().upper()
                    delta = personaggio.regola_risorsa_staff(sigla, delta_effettivo, motivo="Nodo scansionato (config)")
                    rewards["pool"] = {"sigla": sigla, "delta": delta_effettivo, "valore_corrente": delta}
                    rewards["reward_source"] = "config"
                    applied_from_config = True
                elif regola.tipo_reward == NODO_REWARD_CREDITI and delta_effettivo:
                    personaggio.modifica_crediti(delta_effettivo, "Nodo scansionato (config)")
                    rewards["crediti"] = delta_effettivo
                    rewards["reward_source"] = "config"
                    applied_from_config = True

        if not applied_from_config:
            # Fallback legacy hardcoded (retrocompatibilità):
            # usato quando il nodo non ha reward_config o la config non copre l'era corrente.
            rewards["reward_source"] = "fallback_hardcoded"
            if abbr == "eroi":
                delta = personaggio.regola_risorsa_staff("TEO", mult, motivo="Nodo scansionato")
                rewards["pool"] = {"sigla": "TEO", "delta": mult, "valore_corrente": delta}
            elif abbr == "rocche":
                delta = personaggio.regola_risorsa_staff("SIW", mult, motivo="Nodo scansionato")
                rewards["pool"] = {"sigla": "SIW", "delta": mult, "valore_corrente": delta}
            elif abbr in ("verità", "verita"):
                delta = personaggio.regola_risorsa_staff("ROT", mult, motivo="Nodo scansionato")
                rewards["pool"] = {"sigla": "ROT", "delta": mult, "valore_corrente": delta}
            elif abbr in ("imperatore", "capitale"):
                cred = 25 * mult
                personaggio.modifica_crediti(cred, "Nodo scansionato")
                rewards["crediti"] = cred
            elif abbr == "silenzio":
                delta = personaggio.regola_risorsa_staff("AST", mult, motivo="Nodo scansionato")
                rewards["pool"] = {"sigla": "AST", "delta": mult, "valore_corrente": delta}
            elif abbr == "famiglie":
                delta = personaggio.regola_risorsa_staff("MUT", mult, motivo="Nodo scansionato")
                rewards["pool"] = {"sigla": "MUT", "delta": mult, "valore_corrente": delta}
            elif abbr == "paradossi":
                delta = personaggio.regola_risorsa_staff("AVA", mult, motivo="Nodo scansionato")
                rewards["pool"] = {"sigla": "AVA", "delta": mult, "valore_corrente": delta}
            else:
                rewards["note"] = "Nessuna reward configurata per questa era."

        # Cooldown da configurazione (se presente), altrimenti fallback legacy 5..25.
        if cfg:
            cd_min = max(1, int(cfg.cooldown_minuti_min or 5))
            cd_max = max(cd_min, int(cfg.cooldown_minuti_max or 25))
            cd_minutes = random.randint(cd_min, cd_max)
        else:
            cd_minutes = random.randint(5, 25)
        nodo.ultima_scansione_at = now
        nodo.disponibile_dal = now + timedelta(minutes=cd_minutes)
        # Trasformazione tipo nodo:
        # - se esiste reward_config usa le probabilità configurate
        # - altrimenti mantiene fallback legacy 10% MAG / 90% MIN
        if cfg:
            p_min_to_mag = max(0, min(100, int(cfg.prob_minore_to_maggiore or 0))) / 100.0
            p_mag_to_min = max(0, min(100, int(cfg.prob_maggiore_to_minore or 0))) / 100.0
            if nodo.tipo_nodo == TIPO_NODO_MINORE:
                nodo.tipo_nodo = TIPO_NODO_MAGGIORE if random.random() < p_min_to_mag else TIPO_NODO_MINORE
            else:
                nodo.tipo_nodo = TIPO_NODO_MINORE if random.random() < p_mag_to_min else TIPO_NODO_MAGGIORE
        else:
            nodo.tipo_nodo = TIPO_NODO_MAGGIORE if random.random() < 0.10 else TIPO_NODO_MINORE
        nodo.save(update_fields=["ultima_scansione_at", "disponibile_dal", "tipo_nodo", "updated_at"])

    rewards["ok"] = True
    rewards["cooldown_until"] = nodo.disponibile_dal
    rewards["cooldown_minutes"] = cd_minutes
    rewards["tipo_nodo_post"] = nodo.tipo_nodo
    return rewards


def consuma_pool_speciale(personaggio, stat_sigla: str) -> Dict[str, Any]:
    """
    Hook di consumo pool (pulsante già esistente in scheda gioco).
    Restituisce payload extra da allegare alla risposta API.
    """
    from .effetti_casuali import seleziona_effetto_casuale

    sigla = (stat_sigla or "").strip().upper()
    if sigla == "TEO":
        tip = _find_tipologia_by_candidates(["trucchetti", "trucchetto"])
        if not tip:
            return {"note": "Nessuna tipologia effetti per Trucchetti configurata."}
        res = seleziona_effetto_casuale(tip, personaggio)
        return {"speciale": "trucchetto", "risultato": res}
    if sigla == "ROT":
        tip = _find_tipologia_by_candidates(["marchingegni", "marchingegno"])
        if not tip:
            return {"note": "Nessuna tipologia effetti per Marchingegni configurata."}
        res = seleziona_effetto_casuale(tip, personaggio)
        return {"speciale": "marchingegno", "risultato": res}
    if sigla == "SIW":
        return {"speciale": "siw", "note": "Seme Ironwood consumato. Può sostituire un chakra."}
    if sigla == "AST":
        return {"speciale": "ast", "note": "Astuzia consumata. Annotare aiuto prova."}
    if sigla == "MUT":
        cur = personaggio.get_risorsa_corrente("MUT")
        return {"speciale": "mut", "note": "Mutageno consumato. Definire mutazione con lo staff.", "mut_points_left": cur}
    if sigla == "AVA":
        cur = personaggio.get_risorsa_corrente("AVA")
        chance = min(100, cur * 2)
        return {"speciale": "ava", "note": "Regola resurrezione non attiva in questa fase.", "ava_points_left": cur, "resurrect_chance_percent": chance}
    return {}


def annotate_has_qrcode_avista(qs):
    """Annotazione Exists: True se esiste un QrCode con vista_id = pk della riga (sottoclassi A_vista)."""
    from django.db.models import Exists, OuterRef

    from .models import QrCode

    return qs.annotate(has_qrcode=Exists(QrCode.objects.filter(vista_id=OuterRef("pk"))))


def descrivi_avista_per_associazione_qr(vista_obj):
    """
    Risolve la sottoclasse reale collegata a QrCode.vista (ORM carica spesso solo A_vista).
    Usato per messaggi 409 e strumenti staff.
    Ritorna dict: tipo (slug), nome, elemento_id (str).
    """
    from .models import (
        Attivata,
        Cerimoniale,
        Infusione,
        InnescoTimer,
        Inventario,
        Manifesto,
        Nodo,
        Oggetto,
        Personaggio,
        Tessitura,
    )

    if vista_obj is None:
        return None

    pk = vista_obj.pk

    def _out(tipo: str, instance) -> Dict[str, Any]:
        return {
            "tipo": tipo,
            "nome": getattr(instance, "nome", str(instance)),
            "elemento_id": str(instance.pk),
        }

    if InnescoTimer.objects.filter(pk=pk).exists():
        return _out("innesco_timer", InnescoTimer.objects.get(pk=pk))
    if Nodo.objects.filter(pk=pk).exists():
        return _out("nodo", Nodo.objects.get(pk=pk))
    if Personaggio.objects.filter(inventario_ptr_id=pk).exists():
        return _out("personaggio", Personaggio.objects.get(inventario_ptr_id=pk))
    if Oggetto.objects.filter(pk=pk).exists():
        return _out("oggetto", Oggetto.objects.get(pk=pk))
    if Attivata.objects.filter(pk=pk).exists():
        return _out("attivata", Attivata.objects.get(pk=pk))
    if Infusione.objects.filter(pk=pk).exists():
        return _out("infusione", Infusione.objects.get(pk=pk))
    if Tessitura.objects.filter(pk=pk).exists():
        return _out("tessitura", Tessitura.objects.get(pk=pk))
    if Cerimoniale.objects.filter(pk=pk).exists():
        return _out("cerimoniale", Cerimoniale.objects.get(pk=pk))
    if Manifesto.objects.filter(pk=pk).exists():
        return _out("manifesto", Manifesto.objects.get(pk=pk))
    inv = Inventario.objects.filter(pk=pk).first()
    if inv and not Personaggio.objects.filter(inventario_ptr_id=pk).exists():
        return _out("inventario", inv)
    return _out("a_vista", vista_obj)
