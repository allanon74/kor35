"""
Valutazione prontezza negozi mercante (staff / plot quest).
"""
from __future__ import annotations

from personaggi.negozio_mercante_models import (
    NEGOZIO_TIPO_ALTERNATIVO,
    STOCK_DISPONIBILE,
    NegozioMercante,
    NegozioMercanteStock,
    NegozioMercanteVoce,
)


def valuta_prontezza_negozio(negozio: NegozioMercante) -> dict:
    """Ritorna stato sintetico e lista controlli per UI plot/staff."""
    checks = []
    ok_all = True

    def add(ok: bool, code: str, label: str, detail: str = ""):
        nonlocal ok_all
        if not ok:
            ok_all = False
        checks.append({"ok": ok, "code": code, "label": label, "detail": detail})

    if not negozio.attivo:
        add(False, "attivo", "Negozio attivo", "Disattivato in anagrafica.")
    else:
        add(True, "attivo", "Negozio attivo")

    if negozio.tipo_negozio == NEGOZIO_TIPO_ALTERNATIVO:
        if negozio.qr_code_id:
            add(True, "qr", "QR collegato", f"ID QR {negozio.qr_code_id}")
        else:
            add(False, "qr", "QR collegato", "Scansiona un QR dal plot o da staff.")
    else:
        add(True, "qr", "QR (non richiesto)", "Negozio corporativo: tab in app.")

    voci_attive = NegozioMercanteVoce.objects.filter(negozio=negozio, attivo=True).count()
    stock_disp = NegozioMercanteStock.objects.filter(
        negozio=negozio, stato=STOCK_DISPONIBILE
    ).count()
    if voci_attive > 0 or stock_disp > 0:
        add(
            True,
            "catalogo",
            "Catalogo / stock",
            f"{voci_attive} voci, {stock_disp} usati in vendita.",
        )
    else:
        add(
            False,
            "catalogo",
            "Catalogo / stock",
            "Aggiungi almeno una voce catalogo o uno stock usato.",
        )

    saldo = negozio.saldo_crediti or 0
    if saldo > 0:
        add(True, "cassa", "Cassa mercante", f"{int(saldo)} CR disponibili.")
    else:
        add(
            False,
            "cassa",
            "Cassa mercante",
            "Saldo zero: il mercante non può ricomprare oggetti dai PG.",
        )

    if (negozio.nome or "").strip():
        add(True, "nome", "Nome configurato")
    else:
        add(False, "nome", "Nome configurato", "Nome negozio mancante.")

    return {
        "pronto": ok_all,
        "checks": checks,
        "voci_attive": voci_attive,
        "stock_disponibili": stock_disp,
        "saldo_crediti": int(saldo),
        "ha_qr": bool(negozio.qr_code_id),
        "tipo_negozio": negozio.tipo_negozio,
    }
