"""
Compattatore Quantico: sacrificio oggetto (testo o QR) → 1–5 componenti in stiva.

Due algoritmi deterministici sul nome normalizzato (tutte le lettere/cifre):
1. quantità (1–5) — ogni carattere contribuisce;
2. tipo (indice 0–9) per ogni unità — ogni carattere contribuisce.

Stessa stringa esatta → stesso risultato; effetto apparentemente casuale.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any, Dict, List

from django.db import transaction
from django.utils import timezone

from .componenti_stiva import mattone_per_indice_colore

_NOME_RE = re.compile(r"[^A-Z0-9]", re.IGNORECASE)


def normalizza_nome_quantico(nome: str) -> str:
    """Mantiene solo lettere e cifre, maiuscolo."""
    return _NOME_RE.sub("", (nome or "").upper())


def _digest_nome(norm: str) -> bytes:
    return hashlib.sha256(norm.encode("utf-8")).digest()


def _calcola_quantita_componenti(norm: str, digest: bytes) -> int:
    """Algoritmo 1: da 1 a 5 unità, con contributo di ogni carattere del nome."""
    acc = 0
    lunghezza = len(norm)
    for i, ch in enumerate(norm):
        acc = (
            acc
            + ord(ch) * (i + 1)
            + digest[i % len(digest)] * lunghezza
            + (ord(ch) ^ digest[(i + 7) % len(digest)])
        ) & 0xFFFFFFFF
    return 1 + (acc % 5)


def _calcola_indice_componente(norm: str, digest: bytes, unita_idx: int) -> int:
    """Algoritmo 2: indice 0–9 per l'unità, con contributo di ogni carattere del nome."""
    acc = 0
    lunghezza = len(norm)
    for i, ch in enumerate(norm):
        mix = (
            ord(ch)
            + digest[(i + unita_idx * 3 + 1) % len(digest)] * (unita_idx + 2)
            + (i + 1) * lunghezza
        )
        acc = (acc ^ (mix * (i + lunghezza + unita_idx * 7 + 1))) & 0xFFFFFFFF
    return acc % 10


def genera_componenti_da_nome(nome: str) -> Dict[str, Any]:
    """
    Da un nome oggetto genera da 1 a 5 unità di componenti (indice 0–9).

    La quantità e il tipo di ogni unità derivano dall'intera stringa normalizzata
    (non da una singola lettera «di partenza»).
    """
    norm = normalizza_nome_quantico(nome)
    if len(norm) < 2:
        raise ValueError("Il nome oggetto deve contenere almeno 2 caratteri alfanumerici.")

    digest = _digest_nome(norm)
    numero = _calcola_quantita_componenti(norm, digest)
    unita: List[dict] = []
    conteggio: Counter[int] = Counter()

    for i in range(numero):
        indice = _calcola_indice_componente(norm, digest, i)
        mattone = mattone_per_indice_colore(indice)
        if mattone is None:
            raise ValueError(f"Catalogo componenti incompleto (indice {indice}).")
        conteggio[indice] += 1
        unita.append(
            {
                "indice_componente": indice,
                "mattone_id": str(mattone.pk),
                "mattone_nome": mattone.nome,
                "colore_nome": mattone.caratteristica_associata.nome
                if mattone.caratteristica_associata
                else "",
            }
        )

    allocazioni = []
    for indice, qty in sorted(conteggio.items()):
        m = mattone_per_indice_colore(indice)
        if m:
            allocazioni.append({"mattone_id": str(m.pk), "quantita": int(qty)})

    return {
        "nome_normalizzato": norm,
        "numero_unit": numero,
        "unita": unita,
        "allocazioni": allocazioni,
    }


@transaction.atomic
def consuma_oggetto_da_qr_inventario(*, personaggio, qr_code) -> str:
    """
    Elimina un Oggetto collegato al QR se presente nell'inventario del personaggio.
    Ritorna il nome dell'oggetto sacrificato.
    """
    from personaggi.models import Oggetto, OggettoInInventario, QrCode

    if not isinstance(qr_code, QrCode):
        qr_code = QrCode.objects.select_related("vista").filter(pk=qr_code).first()
    if qr_code is None or not qr_code.vista_id:
        raise ValueError("QR non collegato a un oggetto valido.")

    oggetto = Oggetto.objects.filter(pk=qr_code.vista_id).first()
    if oggetto is None:
        raise ValueError("Questo QR non punta a un oggetto fisico eliminabile.")

    row = (
        OggettoInInventario.objects.select_for_update()
        .filter(oggetto=oggetto, inventario=personaggio, data_fine__isnull=True)
        .first()
    )
    if row is None:
        raise ValueError("L'oggetto non è nell'inventario del personaggio indicato.")

    nome = oggetto.nome or "Oggetto"
    row.data_fine = timezone.now()
    row.save(update_fields=["data_fine", "updated_at"])
    oggetto.delete()
    return nome


def risolvi_nome_da_qr(qr_code) -> str:
    """Nome descrittivo per l'algoritmo senza consumare l'oggetto."""
    from personaggi.models import Oggetto, Manifesto, QrCode

    if not isinstance(qr_code, QrCode):
        qr_code = QrCode.objects.select_related("vista").filter(pk=qr_code).first()
    if qr_code is None:
        raise ValueError("QR non trovato.")
    if qr_code.vista_id:
        oggetto = Oggetto.objects.filter(pk=qr_code.vista_id).first()
        if oggetto and oggetto.nome:
            return oggetto.nome
        manifesto = Manifesto.objects.filter(pk=qr_code.vista_id).first()
        if manifesto and manifesto.nome:
            return manifesto.nome
        if getattr(qr_code.vista, "nome", None):
            return qr_code.vista.nome
    if (qr_code.testo or "").strip():
        return qr_code.testo.strip()
    raise ValueError("Impossibile ricavare un nome dall'oggetto QR.")
