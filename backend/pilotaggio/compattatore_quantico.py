"""
Compattatore Quantico: sacrificio oggetto (testo o QR) → 1–5 componenti in stiva.

Algoritmo deterministico sul nome normalizzato (lettere A–Z e cifre).
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any, Dict, List

from django.db import transaction
from django.utils import timezone

from .componenti_stiva import mattone_per_indice_colore, staff_modifica_stiva

_NOME_RE = re.compile(r"[^A-Z0-9]", re.IGNORECASE)


def normalizza_nome_quantico(nome: str) -> str:
    """Mantiene solo lettere e cifre, maiuscolo."""
    return _NOME_RE.sub("", (nome or "").upper())


def genera_componenti_da_nome(nome: str) -> Dict[str, Any]:
    """
    Da un nome oggetto genera da 1 a 5 unità di componenti (indice 0–9).

    Per ogni unità i:
    - lettera sorgente = nome[i % len(nome)]
    - indice = (ord(lettera) + digest[i+1] + i) mod 10
    - numero unità = 1 + (digest[0] mod 5)
    """
    norm = normalizza_nome_quantico(nome)
    if len(norm) < 2:
        raise ValueError("Il nome oggetto deve contenere almeno 2 caratteri alfanumerici.")

    digest = hashlib.sha256(norm.encode("utf-8")).digest()
    numero = 1 + (digest[0] % 5)
    unita: List[dict] = []
    conteggio: Counter[int] = Counter()

    for i in range(numero):
        lettera = norm[i % len(norm)]
        indice = (ord(lettera) + digest[(i + 1) % len(digest)] + i) % 10
        mattone = mattone_per_indice_colore(indice)
        if mattone is None:
            raise ValueError(f"Catalogo componenti incompleto (indice {indice}).")
        conteggio[indice] += 1
        unita.append(
            {
                "indice_componente": indice,
                "lettera_fonte": lettera,
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
