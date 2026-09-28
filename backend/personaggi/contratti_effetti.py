"""
Registry effetti dei contratti e funzioni pure (niente ORM).

Lo staff compone i modelli da questi codici. Un contratto nuovo che riusa
gli stessi effetti non richiede una maschera dedicata.
"""
from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

INNESCO_STIPULA = "ALLA_STIPULA"
INNESCO_INIZIO_EVENTO = "A_INIZIO_EVENTO"
INNESCO_FINE_EVENTO = "A_FINE_EVENTO"
INNESCO_SCADENZA = "A_SCADENZA"
INNESCO_ATTIVAZIONE = "AD_ATTIVAZIONE"
INNESCO_MANUALE = "MANUALE"

INNESCHI_TEMPORALI = [
    INNESCO_STIPULA,
    INNESCO_INIZIO_EVENTO,
    INNESCO_FINE_EVENTO,
    INNESCO_SCADENZA,
    INNESCO_ATTIVAZIONE,
    INNESCO_MANUALE,
]

AMBITI_COSTO = [
    "creazione_infusione",
    "creazione_cerimoniale",
    "creazione_tessitura",
    "forgiatura",
    "consumabile",
]

_PARAM_RE = re.compile(r"^\{\{param:([A-Za-z0-9_]+)\}\}$")
_TOKEN_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)(?:\s*:\s*([A-Za-z0-9_]+))?\s*\}\}")


def q2(value) -> Decimal:
    return Decimal(str(value if value is not None else 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def risolvi_valore(raw, parametri: dict):
    if isinstance(raw, str):
        match = _PARAM_RE.match(raw.strip())
        if match:
            return parametri.get(match.group(1))
    return raw


def risolvi_config(config: dict, parametri: dict) -> dict:
    out = {}
    for key, value in (config or {}).items():
        if isinstance(value, str):
            out[key] = risolvi_valore(value, parametri)
        elif isinstance(value, list):
            out[key] = [risolvi_valore(item, parametri) for item in value]
        else:
            out[key] = value
    return out


def calcola_post_tetto(n_post: int, massimo: int, importo) -> dict:
    """
    Cliente sempre al massimo. L'indennizzo dei post mancanti lo versa il proponente.
    I post oltre il tetto non contano.
    """
    massimo = max(0, int(massimo or 0))
    n = min(max(0, int(n_post or 0)), massimo)
    mancanti = massimo - n
    cifra = q2(importo)
    creato = q2(n * cifra)
    indennizzo = q2(mancanti * cifra)
    return {
        "n": n,
        "mancanti": mancanti,
        "creato_ciascuno": creato,
        "indennizzo": indennizzo,
        "netto_cliente": q2(creato + indennizzo),
        "netto_proponente": q2(creato - indennizzo),
    }


EFFETTI_REGISTRY = [
    {
        "codice": "credito_creato",
        "label": "Credito creato",
        "descrizione": "Accredita crediti nuovi sul deposito.",
        "campi": [
            {"key": "innesco", "tipo": "scelta", "scelte": INNESCHI_TEMPORALI},
            {"key": "beneficiario", "tipo": "scelta", "scelte": ["CLIENTE", "PROPONENTE", "ENTRAMBI"]},
            {"key": "importo", "tipo": "importo"},
        ],
    },
    {
        "codice": "trasferimento",
        "label": "Trasferimento",
        "descrizione": "Sposta crediti da un contraente all'altro. Non li crea.",
        "campi": [
            {"key": "innesco", "tipo": "scelta", "scelte": INNESCHI_TEMPORALI},
            {"key": "da", "tipo": "scelta", "scelte": ["CLIENTE", "PROPONENTE"]},
            {"key": "a", "tipo": "scelta", "scelte": ["CLIENTE", "PROPONENTE"]},
            {"key": "importo", "tipo": "importo"},
            {"key": "se_scoperto", "tipo": "scelta", "scelte": ["BLOCCA", "DEBITO"]},
        ],
    },
    {
        "codice": "percentuale_task",
        "label": "Percentuale sulla task del cliente",
        "descrizione": "Alla ricompensa crediti di una task del cliente, bonus a entrambi sul deposito.",
        "campi": [
            {"key": "pct_cliente", "tipo": "percentuale"},
            {"key": "pct_proponente", "tipo": "percentuale"},
        ],
    },
    {
        "codice": "sconto_costo",
        "label": "Sconto e bonus su un costo",
        "descrizione": "Sconto al cliente e bonus al proponente sul costo pieno, prima degli altri sconti già applicati si sommano.",
        "campi": [
            {"key": "ambiti", "tipo": "multi", "scelte": AMBITI_COSTO},
            {"key": "pct_sconto_cliente", "tipo": "percentuale"},
            {"key": "pct_bonus_proponente", "tipo": "percentuale"},
        ],
    },
    {
        "codice": "post_tetto_evento",
        "label": "Post social con tetto per evento",
        "descrizione": "A fine evento il cliente riceve il massimo; i post mancanti li indennizza il proponente.",
        "campi": [
            {"key": "massimo_post", "tipo": "intero"},
            {"key": "crediti_per_post", "tipo": "importo"},
        ],
    },
    {
        "codice": "contatore_servizi",
        "label": "Contatore servizi",
        "descrizione": "Tetto di ore o quest per evento. Non muove crediti.",
        "campi": [
            {"key": "unita", "tipo": "scelta", "scelte": ["ORE", "QUEST"]},
            {"key": "massimo_per_evento", "tipo": "importo"},
        ],
    },
    {
        "codice": "penale_confermata",
        "label": "Penale o rimborso con conferma",
        "descrizione": "Ferita o morte: il trasferimento parte dopo la conferma.",
        "campi": [
            {"key": "evento", "tipo": "scelta", "scelte": ["FERITA", "MORTE"]},
            {"key": "da", "tipo": "scelta", "scelte": ["CLIENTE", "PROPONENTE"]},
            {"key": "a", "tipo": "scelta", "scelte": ["CLIENTE", "PROPONENTE", "EREDE"]},
            {"key": "importo", "tipo": "importo"},
            {"key": "conferma", "tipo": "scelta", "scelte": ["CONTROPARTE", "STAFF"]},
            {"key": "a_morte_paga", "tipo": "scelta", "scelte": ["CLIENTE", "EREDE"]},
        ],
    },
    {
        "codice": "attivazione",
        "label": "Attivazione",
        "descrizione": "Azione del proponente. Sblocca gli effetti con innesco attivazione.",
        "campi": [
            {"key": "richiede_staff", "tipo": "bool"},
            {"key": "risolvi_contratto", "tipo": "bool"},
        ],
    },
]

EFFETTI_PER_CODICE = {row["codice"]: row for row in EFFETTI_REGISTRY}


def codice_noto(codice: str) -> bool:
    return codice in EFFETTI_PER_CODICE


def render_testo_contratto(
    modello_testo: str,
    *,
    proponente: str = "",
    cliente: str = "il sottoscrittore",
    korp: str = "",
    scadenza: str = "",
    parametri: dict | None = None,
    etichette: dict | None = None,
    clausole: list | None = None,
    compensi: list | None = None,
) -> str:
    """Sostituisce i segnaposto del modello. ``{{param:chiave}}`` tollera spazi interni."""
    valori = dict(parametri or {})
    nomi = dict(etichette or {})
    linee_param = "\n".join(
        f"- {nomi.get(chiave) or chiave}: {'' if valore is None else valore}"
        for chiave, valore in valori.items()
    )
    linee_clausole = "\n".join(f"- {riga}" for riga in (clausole or [])) or "—"
    linee_compensi = "\n".join(f"- {riga}" for riga in (compensi or [])) or "—"
    mappa = {
        "proponente": proponente or "",
        "cliente": cliente or "il sottoscrittore",
        "korp": korp or "",
        "scadenza": scadenza or "",
        "parametri": linee_param,
        "clausole": linee_clausole,
        "compensi": linee_compensi,
    }

    def sostituisci(match: re.Match) -> str:
        nome = match.group(1)
        chiave = match.group(2)
        if nome == "param" and chiave:
            if chiave not in valori:
                return match.group(0)
            valore = valori[chiave]
            if valore is None or valore == "":
                return ""
            return str(valore)
        if nome in mappa:
            return str(mappa[nome])
        return match.group(0)

    return _TOKEN_RE.sub(sostituisci, modello_testo or "")
