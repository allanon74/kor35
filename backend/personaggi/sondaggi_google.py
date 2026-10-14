"""
Lettura di un Google Form pubblico e copia delle risposte nel foglio.

Il formato FB_PUBLIC_LOAD_DATA_ non è un'API ufficiale: se Google lo cambia,
l'importazione fallisce con un messaggio esplicito e le risposte già salvate restano in KOR35.
"""
from __future__ import annotations

import json
import os
import re
from datetime import timedelta
from urllib.parse import urlencode, urljoin, urlsplit

import requests
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone

from kor35.syncing import touch_sync_updated_at

HOST_CONSENTITO = "docs.google.com"
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,128}$")
_MAX_HTML = 2_000_000
_CLAIM_STALE = timedelta(minutes=3)
_USER_AGENT = "KOR35-sondaggio/1.0"

TIPI_GOOGLE = {
    0: "testo_breve",
    1: "testo_lungo",
    2: "scelta_singola",
    3: "menu",
    4: "caselle",
    5: "scala",
    7: "griglia",
    8: "sezione",
    9: "data",
    10: "ora",
}
TIPI_COMPILABILI = {
    "testo_breve",
    "testo_lungo",
    "scelta_singola",
    "menu",
    "caselle",
    "scala",
    "data",
    "ora",
}
TIPI_CON_OPZIONI = {"scelta_singola", "menu", "caselle"}


class ErroreModuloGoogle(Exception):
    """Il modulo non è leggibile o l'invio al foglio è fallito."""


def nodo_puo_inoltrare() -> bool:
    """Solo master e dev-home locale copiano sul foglio. La replica aspetta il sync."""
    ruolo = os.environ.get("KOR35_SYNC_NODE_ROLE", "unset").strip().lower()
    return ruolo in {"master", "local"}


def normalizza_url_modulo(url: str) -> tuple[str, str]:
    """
    Accetta solo il link pubblico «Invia» di Google Moduli.
    Ritorna (url canonico viewform, id del modulo).
    """
    grezzo = (url or "").strip()
    if not grezzo:
        raise ErroreModuloGoogle("Incolla il link del modulo Google.")
    parti = urlsplit(grezzo)
    if parti.scheme != "https" or (parti.hostname or "").lower() != HOST_CONSENTITO:
        raise ErroreModuloGoogle(
            "Il link deve essere un modulo pubblico su https://docs.google.com/forms/…"
        )
    if parti.username or parti.password:
        raise ErroreModuloGoogle("Link del modulo non valido.")
    pezzi = [p for p in parti.path.split("/") if p]
    form_id = ""
    if len(pezzi) >= 4 and pezzi[0] == "forms" and pezzi[1] == "d" and pezzi[2] == "e":
        form_id = pezzi[3]
    if not _ID_RE.match(form_id):
        raise ErroreModuloGoogle(
            "Usa il link pubblico da Invia (docs.google.com/forms/d/e/…/viewform), "
            "non il link di modifica."
        )
    canonico = f"https://{HOST_CONSENTITO}/forms/d/e/{form_id}/viewform"
    return canonico, form_id


def _estrai_fb(html: str):
    indice = html.find("FB_PUBLIC_LOAD_DATA_")
    if indice < 0:
        raise ErroreModuloGoogle(
            "Non trovo le domande. Il modulo deve essere pubblico e il link quello di Invia."
        )
    inizio = html.find("[", indice)
    if inizio < 0:
        raise ErroreModuloGoogle("Il modulo Google non ha un elenco di domande leggibile.")
    try:
        dati, _ = json.JSONDecoder().raw_decode(html[inizio:])
    except json.JSONDecodeError as exc:
        raise ErroreModuloGoogle("Il modulo Google ha un formato che non riesco a leggere.") from exc
    if not isinstance(dati, list):
        raise ErroreModuloGoogle("Il modulo Google ha un formato che non riesco a leggere.")
    return dati


def _testo(valore, limite: int) -> str:
    if not isinstance(valore, str):
        return ""
    return valore.replace("\x00", "").strip()[:limite]


def _opzioni(dettaglio) -> list[str]:
    if not isinstance(dettaglio, list) or len(dettaglio) < 2 or not isinstance(dettaglio[1], list):
        return []
    trovate = []
    for voce in dettaglio[1]:
        if isinstance(voce, list) and voce and isinstance(voce[0], str):
            etichetta = _testo(voce[0], 300)
        elif isinstance(voce, str):
            etichetta = _testo(voce, 300)
        else:
            etichetta = ""
        if etichetta and etichetta not in trovate:
            trovate.append(etichetta)
    return trovate


def _obbligatoria(dettaglio) -> bool:
    if not isinstance(dettaglio, list) or len(dettaglio) < 3:
        return False
    return dettaglio[2] in (1, True)


def _scala(dettaglio) -> tuple[int | None, int | None, str, str]:
    minimo = massimo = None
    etichetta_min = etichetta_max = ""
    if not isinstance(dettaglio, list):
        return minimo, massimo, etichetta_min, etichetta_max
    for voce in dettaglio:
        if (
            isinstance(voce, list)
            and len(voce) == 2
            and all(isinstance(x, int) and not isinstance(x, bool) for x in voce)
        ):
            minimo, massimo = voce
        elif isinstance(voce, list) and len(voce) == 2 and all(isinstance(x, str) for x in voce):
            etichetta_min = _testo(voce[0], 80)
            etichetta_max = _testo(voce[1], 80)
    if minimo is not None and massimo is not None and minimo > massimo:
        minimo, massimo = massimo, minimo
    return minimo, massimo, etichetta_min, etichetta_max


def _analizza_dati(dati) -> dict:
    if len(dati) < 2 or not isinstance(dati[1], list):
        raise ErroreModuloGoogle("Il modulo Google non contiene domande.")
    blocco = dati[1]
    titolo = "Sondaggio"
    if len(blocco) > 8:
        titolo = _testo(blocco[8], 200) or titolo
    descrizione = _testo(blocco[0], 8000) if blocco else ""
    grezze = blocco[1] if len(blocco) > 1 and isinstance(blocco[1], list) else []
    domande = []
    avvisi = []
    for indice, voce in enumerate(grezze):
        if not isinstance(voce, list) or len(voce) < 4:
            continue
        if len(domande) >= 80:
            avvisi.append("Il modulo ha più di 80 domande: le successive non sono state importate.")
            break
        tipo_codice = voce[3] if len(voce) > 3 else None
        tipo = TIPI_GOOGLE.get(tipo_codice, "non_supportato")
        titolo_domanda = _testo(voce[1] if len(voce) > 1 else "", 500) or "Domanda"
        descrizione_domanda = _testo(voce[2] if len(voce) > 2 else "", 2000)
        dettagli = voce[4] if len(voce) > 4 and isinstance(voce[4], list) else []
        dettagli_utili = [d for d in dettagli if isinstance(d, list) and d and isinstance(d[0], int)]
        if tipo == "sezione" or (not dettagli_utili and tipo == "sezione"):
            domande.append({
                "id": f"sezione-{indice}",
                "entry_id": "",
                "titolo": titolo_domanda,
                "descrizione": descrizione_domanda,
                "tipo": "sezione",
                "obbligatoria": False,
                "opzioni": [],
                "scala_min": None,
                "scala_max": None,
                "scala_min_etichetta": "",
                "scala_max_etichetta": "",
                "supportata": True,
            })
            continue
        if len(dettagli_utili) != 1:
            tipo = "non_supportato"
            dettaglio = dettagli_utili[0] if dettagli_utili else []
        else:
            dettaglio = dettagli_utili[0]
        entry = str(dettaglio[0]) if dettaglio else ""
        opzioni = _opzioni(dettaglio)
        scala_min, scala_max, scala_min_etichetta, scala_max_etichetta = _scala(dettaglio)
        if tipo == "scala" and (scala_min is None or scala_max is None):
            scala_min, scala_max = 1, 5
        supportata = (
            tipo in TIPI_COMPILABILI
            and bool(entry)
            and (tipo not in TIPI_CON_OPZIONI or bool(opzioni))
        )
        if not supportata:
            avvisi.append(f"«{titolo_domanda}» non è compilabile nell'app (tipo non supportato).")
        domande.append({
            "id": f"entry.{entry}" if entry else f"domanda-{indice}",
            "entry_id": entry,
            "titolo": titolo_domanda,
            "descrizione": descrizione_domanda,
            "tipo": tipo if tipo in TIPI_COMPILABILI or tipo == "non_supportato" else "non_supportato",
            "obbligatoria": _obbligatoria(dettaglio) if supportata else False,
            "opzioni": opzioni,
            "scala_min": scala_min,
            "scala_max": scala_max,
            "scala_min_etichetta": scala_min_etichetta,
            "scala_max_etichetta": scala_max_etichetta,
            "supportata": supportata,
        })
    if not any(d["tipo"] != "sezione" for d in domande):
        raise ErroreModuloGoogle("Il modulo non contiene domande compilabili.")
    return {"titolo": titolo, "descrizione": descrizione, "domande": domande, "avvisi": avvisi}


def analizza_html_modulo(html: str) -> dict:
    if not html or not html.strip():
        raise ErroreModuloGoogle("Google ha restituito una pagina vuota.")
    risultato = _analizza_dati(_estrai_fb(html))
    if risultato["titolo"] == "Sondaggio":
        trovato = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        if trovato:
            risultato["titolo"] = _testo(
                trovato.group(1).replace("&amp;", "&").replace("&#39;", "'"),
                200,
            ) or "Sondaggio"
    return risultato


def scarica_html_modulo(url: str) -> str:
    """Scarica il viewform restando su docs.google.com (niente redirect verso altri host)."""
    corrente, _ = normalizza_url_modulo(url)
    headers = {"User-Agent": _USER_AGENT, "Accept": "text/html"}
    for _ in range(4):
        try:
            risposta = requests.get(
                corrente,
                headers=headers,
                timeout=(5, 20),
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as exc:
            raise ErroreModuloGoogle(
                "Non riesco a raggiungere Google. Riprova quando il nodo è online."
            ) from exc
        try:
            if risposta.status_code in (301, 302, 303, 307, 308):
                destinazione = urljoin(corrente, risposta.headers.get("Location") or "")
                corrente, _ = normalizza_url_modulo(destinazione)
                continue
            if risposta.status_code >= 400:
                raise ErroreModuloGoogle(
                    f"Google ha risposto {risposta.status_code}. "
                    "Controlla che il modulo sia pubblico (chiunque abbia il link)."
                )
            pezzi = []
            totale = 0
            for blocco in risposta.iter_content(65536):
                if not blocco:
                    continue
                totale += len(blocco)
                if totale > _MAX_HTML:
                    raise ErroreModuloGoogle("Il modulo è troppo grande da importare.")
                pezzi.append(blocco)
        finally:
            risposta.close()
        return b"".join(pezzi).decode("utf-8", errors="replace")
    raise ErroreModuloGoogle("Troppi reindirizzamenti sul link del modulo.")


def costruisci_corpo_invio(domande, risposte, email: str = "") -> list[tuple[str, str]]:
    coppie: list[tuple[str, str]] = []
    for domanda in domande or []:
        if not domanda.get("supportata") or domanda.get("tipo") == "sezione":
            continue
        chiave = domanda.get("id") or ""
        if not chiave.startswith("entry."):
            continue
        valore = (risposte or {}).get(chiave)
        if valore is None or valore == "" or valore == []:
            continue
        if isinstance(valore, list):
            for voce in valore:
                testo = str(voce).strip()
                if testo:
                    coppie.append((chiave, testo))
        else:
            coppie.append((chiave, str(valore)))
    if email:
        coppie.append(("emailAddress", email))
    coppie.extend([
        ("fvv", "1"),
        ("draftResponse", "[]"),
        ("pageHistory", "0"),
        ("fbzx", "0"),
    ])
    return coppie


def _posta_form(form_id: str, view_url: str, coppie: list[tuple[str, str]]) -> None:
    destinazione = f"https://{HOST_CONSENTITO}/forms/d/e/{form_id}/formResponse"
    try:
        risposta = requests.post(
            destinazione,
            data=urlencode(coppie),
            headers={
                "User-Agent": _USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": view_url or destinazione,
            },
            timeout=(5, 20),
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        raise ErroreModuloGoogle("Invio al foglio Google non riuscito: rete non disponibile.") from exc
    finale = urlsplit(risposta.url or "")
    if (finale.hostname or "").lower() not in {"", HOST_CONSENTITO}:
        raise ErroreModuloGoogle("Google ha dirottato l'invio fuori da docs.google.com.")
    testo = (risposta.text or "")[:4000]
    if risposta.status_code >= 400 or "FB_PUBLIC_LOAD_DATA_" in testo:
        raise ErroreModuloGoogle(
            "Google ha rifiutato la risposta. Se il modulo ha domande obbligatorie "
            "non compilabili nell'app, toglile o rendile facoltative."
        )


def inoltra_risposta_a_google(risposta_id) -> str:
    """
    Copia una risposta sul foglio Google.
    Ritorna: inviata, gia_inviata, in_corso, saltato_nodo, errore.
    """
    from personaggi.sondaggi_models import RispostaSondaggio

    if not nodo_puo_inoltrare():
        return "saltato_nodo"
    adesso = timezone.now()
    with transaction.atomic():
        try:
            riga = (
                RispostaSondaggio.objects.select_for_update()
                .select_related("sondaggio")
                .get(pk=risposta_id)
            )
        except RispostaSondaggio.DoesNotExist:
            return "errore"
        if riga.google_inviato_at:
            return "gia_inviata"
        if riga.google_claim_at and riga.google_claim_at > adesso - _CLAIM_STALE:
            return "in_corso"
        RispostaSondaggio.objects.filter(pk=riga.pk).update(google_claim_at=adesso)
        sondaggio = riga.sondaggio
        form_id = sondaggio.google_form_id
        view_url = sondaggio.google_form_url
        domande = sondaggio.domande
        risposte = riga.risposte
        email = ""
        if sondaggio.inoltra_email and riga.utente_id:
            from django.contrib.auth import get_user_model

            trovata = (
                get_user_model().objects.filter(pk=riga.utente_id).values_list("email", flat=True).first()
                or ""
            )
            email = trovata.strip()
    try:
        _posta_form(form_id, view_url, costruisci_corpo_invio(domande, risposte, email))
    except ErroreModuloGoogle as exc:
        RispostaSondaggio.objects.filter(pk=risposta_id, google_inviato_at__isnull=True).update(
            google_claim_at=None,
            google_errore=str(exc)[:500],
        )
        return "errore"
    RispostaSondaggio.objects.filter(pk=risposta_id).update(
        google_inviato_at=timezone.now(),
        google_claim_at=None,
        google_errore="",
    )
    touch_sync_updated_at(RispostaSondaggio, risposta_id)
    return "inviata"


def _dopo_salvataggio_risposta(sender, instance, **kwargs):
    pk = instance.pk

    def _avvia():
        inoltra_risposta_a_google(pk)

    transaction.on_commit(_avvia)


def registra_segnale_inoltro():
    from personaggi.sondaggi_models import RispostaSondaggio

    post_save.connect(
        _dopo_salvataggio_risposta,
        sender=RispostaSondaggio,
        dispatch_uid="kor35.sondaggio.inoltra_google",
    )
