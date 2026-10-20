"""
Creazione istanze da infusione e montaggio d'ufficio per la dashboard staff.

Lo staff non passa dai controlli di competenza del personaggio (check_skills).
La compatibilità hardware dell'oggetto ospite resta attiva: una materia non
finisce su un host che il regolamento non accetta.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from personaggi.models import (
    SCELTA_RISULTATO_AUMENTO,
    SLOT_CORPO_CHOICES,
    Oggetto,
    TIPO_OGGETTO_FISICO,
    TIPO_OGGETTO_INNESTO,
    TIPO_OGGETTO_MATERIA,
    TIPO_OGGETTO_MOD,
    TIPO_OGGETTO_MUTAZIONE,
    TIPO_OGGETTO_POTENZIAMENTO,
)
from personaggi.services import GestioneOggettiService

TIPI_POTENZIAMENTO = (
    TIPO_OGGETTO_MATERIA,
    TIPO_OGGETTO_MOD,
    TIPO_OGGETTO_POTENZIAMENTO,
)
TIPI_CORPO = (TIPO_OGGETTO_INNESTO, TIPO_OGGETTO_MUTAZIONE)

_SLOT_LABEL = dict(SLOT_CORPO_CHOICES)


def messaggio_validazione(exc: ValidationError) -> str:
    if hasattr(exc, "messages"):
        return " ".join(str(m) for m in exc.messages)
    return str(exc)


def tipo_oggetto_previsto(infusione) -> str:
    """Stessa regola di GestioneOggettiService.crea_oggetto_da_infusione."""
    aura = infusione.aura_infusione if infusione.aura_infusione_id else infusione.aura_richiesta
    tecnologico = bool(aura and getattr(aura, "sigla", None) == "ATE")
    if getattr(infusione, "tipo_risultato", None) == SCELTA_RISULTATO_AUMENTO:
        return TIPO_OGGETTO_INNESTO if tecnologico else TIPO_OGGETTO_MUTAZIONE
    return TIPO_OGGETTO_MOD if tecnologico else TIPO_OGGETTO_MATERIA


def _pk(value):
    if value in (None, "", 0, "0"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Identificativo non valido.") from exc


def oggetto_nel_inventario(personaggio, oggetto) -> bool:
    inv = oggetto.inventario_corrente
    if inv is None or personaggio is None:
        return False
    return inv.pk == personaggio.inventario_ptr_id


def _payload_oggetto(oggetto, personaggio, detail: str) -> dict:
    return {
        "id": oggetto.id,
        "nome": oggetto.nome,
        "tipo_oggetto": oggetto.tipo_oggetto,
        "slot_corpo": oggetto.slot_corpo or "",
        "ospitato_su_id": oggetto.ospitato_su_id,
        "personaggio_id": getattr(personaggio, "id", None),
        "detail": detail,
    }


def crea_istanza_da_infusione_staff(
    infusione,
    *,
    personaggio=None,
    nome=None,
    slot_corpo=None,
    oggetto_ospite_id=None,
    motivo="",
):
    """
    Crea l'istanza. Senza personaggio resta senza inventario.
    Con personaggio: mutazione/innesto richiedono uno slot libero;
    materia/mod possono essere installate su un oggetto fisico dello stesso PG.
    """
    tipo = tipo_oggetto_previsto(infusione)
    slot = (slot_corpo or "").strip()
    host_id = _pk(oggetto_ospite_id)
    motivo = (motivo or "Assegnazione staff").strip()
    nome_custom = (nome or "").strip() or None

    if personaggio is None and (slot or host_id):
        raise ValidationError("Per associare uno slot o un oggetto serve un personaggio.")
    if personaggio is not None and tipo in TIPI_CORPO and not slot:
        raise ValidationError(
            "Per mutazione o innesto scegli uno slot corporeo libero del personaggio."
        )
    if host_id and tipo not in TIPI_POTENZIAMENTO:
        raise ValidationError("Solo materia o mod possono essere installate su un oggetto.")
    if slot and tipo not in TIPI_CORPO:
        raise ValidationError("Lo slot corporeo vale solo per mutazione e innesto.")

    host = None
    if host_id:
        host = Oggetto.objects.filter(pk=host_id).first()
        if host is None:
            raise ValidationError("Oggetto ospite non trovato.")
        if not oggetto_nel_inventario(personaggio, host):
            raise ValidationError("L'oggetto ospite non è nell'inventario del personaggio.")
        if host.tipo_oggetto != TIPO_OGGETTO_FISICO:
            raise ValidationError("Materia e mod si installano solo su un oggetto fisico.")

    with transaction.atomic():
        oggetto = GestioneOggettiService.crea_oggetto_da_infusione(
            infusione,
            personaggio,
            nome_personalizzato=nome_custom,
        )
        if personaggio is not None and tipo in TIPI_CORPO:
            GestioneOggettiService.installa_innesto(personaggio, oggetto, slot)
        if host is not None:
            ok, msg = GestioneOggettiService.verifica_compatibilita_hardware(
                host, oggetto, personaggio=personaggio
            )
            if not ok:
                raise ValidationError(msg)
            GestioneOggettiService.assembla_mod(
                personaggio, host, oggetto, check_skills=False
            )

        oggetto.refresh_from_db()
        if personaggio is None:
            detail = f"Istanza «{oggetto.nome}» creata, senza personaggio."
        elif host is not None:
            detail = (
                f"Istanza «{oggetto.nome}» creata e installata su «{host.nome}» "
                f"({personaggio.nome})."
            )
        elif slot:
            etichetta = _SLOT_LABEL.get(slot, slot)
            detail = (
                f"Istanza «{oggetto.nome}» creata e installata nello slot {etichetta} "
                f"di {personaggio.nome}."
            )
        else:
            detail = f"Istanza «{oggetto.nome}» aggiunta all'inventario di {personaggio.nome}."

        if personaggio is not None:
            personaggio.aggiungi_log(f"Staff: {detail} ({motivo}).")

    return _payload_oggetto(oggetto, personaggio, detail)


def monta_potenziamento_staff(personaggio, componente_id, oggetto_ospite_id, motivo=""):
    """Monta d'ufficio una materia o mod su un oggetto fisico dello stesso personaggio."""
    motivo = (motivo or "Montaggio staff").strip()
    comp_id = _pk(componente_id)
    host_id = _pk(oggetto_ospite_id)
    if not comp_id or not host_id:
        raise ValidationError("Servono la materia (o mod) e l'oggetto ospite.")
    if comp_id == host_id:
        raise ValidationError("Non si può montare un oggetto su se stesso.")

    componente = Oggetto.objects.filter(pk=comp_id).first()
    host = Oggetto.objects.filter(pk=host_id).first()
    if componente is None or host is None:
        raise ValidationError("Oggetto non trovato.")
    if componente.tipo_oggetto not in TIPI_POTENZIAMENTO:
        raise ValidationError("Si possono montare d'ufficio solo materie e mod.")
    if not oggetto_nel_inventario(personaggio, componente) or not oggetto_nel_inventario(
        personaggio, host
    ):
        raise ValidationError(
            "Materia e oggetto devono essere entrambi nell'inventario di questo personaggio."
        )

    with transaction.atomic():
        ok, msg = GestioneOggettiService.verifica_compatibilita_hardware(
            host, componente, personaggio=personaggio
        )
        if not ok:
            raise ValidationError(msg)
        GestioneOggettiService.assembla_mod(
            personaggio, host, componente, check_skills=False
        )
        detail = (
            f"«{componente.nome}» montata d'ufficio su «{host.nome}» ({motivo})."
        )
        personaggio.aggiungi_log(f"Staff: {detail}")
    return {"detail": detail, "componente_id": componente.id, "oggetto_ospite_id": host.id}


def smonta_potenziamento_staff(personaggio, componente_id, motivo=""):
    """Smonta d'ufficio una materia o mod e la rimette nell'inventario del personaggio."""
    motivo = (motivo or "Smontaggio staff").strip()
    comp_id = _pk(componente_id)
    if not comp_id:
        raise ValidationError("componente_id obbligatorio.")

    componente = Oggetto.objects.select_related("ospitato_su").filter(pk=comp_id).first()
    if componente is None:
        raise ValidationError("Componente non trovato.")
    if componente.tipo_oggetto not in TIPI_POTENZIAMENTO:
        raise ValidationError("Si possono smontare d'ufficio solo materie e mod.")
    host = componente.ospitato_su
    if host is None:
        raise ValidationError("Il componente non è montato su un oggetto.")
    if not oggetto_nel_inventario(personaggio, host):
        raise ValidationError("L'oggetto ospite non è nell'inventario di questo personaggio.")

    with transaction.atomic():
        GestioneOggettiService.rimuovi_mod(
            personaggio, host, componente, check_skills=False
        )
        detail = (
            f"«{componente.nome}» smontata d'ufficio da «{host.nome}» ({motivo})."
        )
        personaggio.aggiungi_log(f"Staff: {detail}")
    return {"detail": detail, "componente_id": componente.id, "oggetto_ospite_id": host.id}
