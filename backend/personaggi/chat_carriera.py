"""Chat di gruppo permanenti per Korp e Dipartimenti.

I membri con appartenenza ancora aperta vedono la chat in automatico,
possono scrivere e leggono tutto lo storico. La lettura è per personaggio
(LetturaMessaggio): aprendo la chat i non letti tornano a zero.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from personaggi.models import Gruppo, LetturaMessaggio, Messaggio, PersonaggioCarrieraMembership

_CODICI_CHAT = {"korp", "dipartimento"}
_NOMI_CHAT = {"korp", "korps", "dipartimento", "dipartimenti"}


def carriera_ha_chat_di_gruppo(carriera) -> bool:
    """True per Korp e Dipartimenti, non per le altre carriere."""
    if carriera is None:
        return False
    tipo = getattr(carriera, "tipo_carriera", None)
    if tipo is None:
        return False
    codice = str(getattr(tipo, "codice", "") or "").strip().lower()
    nome = str(getattr(tipo, "nome", "") or "").strip().lower()
    return codice in _CODICI_CHAT or nome in _NOMI_CHAT


def etichetta_chat_carriera(carriera) -> str:
    tipo = getattr(carriera, "tipo_carriera", None)
    codice = str(getattr(tipo, "codice", "") or "").strip().lower() if tipo else ""
    nome = str(getattr(tipo, "nome", "") or "").strip().lower() if tipo else ""
    if codice == "korp" or nome in {"korp", "korps"}:
        return "KORP"
    return "Dipartimento"


def _nome_gruppo_chat(carriera) -> str:
    sid = str(getattr(carriera, "sync_id", "") or carriera.pk)
    return f"chat:{sid}"[:100]


def _ids_membri_attivi(carriera) -> set[int]:
    return set(
        PersonaggioCarrieraMembership.objects.filter(
            carriera=carriera,
            data_a__isnull=True,
        ).values_list("personaggio_id", flat=True)
    )


def sync_chat_gruppo_carriera(carriera):
    """Allinea il gruppo permanente ai membri con appartenenza aperta.

    Le altre carriere non ricevono una chat. Se il tipo cambia, i membri
    vengono svuotati e la chat non compare più.
    """
    if carriera is None:
        return None
    if not carriera_ha_chat_di_gruppo(carriera):
        gruppo = Gruppo.objects.filter(carriera=carriera, chat_permanente=True).first()
        if gruppo is not None and gruppo.membri.exists():
            gruppo.membri.clear()
            gruppo.save(update_fields=["updated_at"])
        return None

    nome = _nome_gruppo_chat(carriera)
    gruppo = (
        Gruppo.objects.filter(carriera=carriera).first()
        or Gruppo.objects.filter(nome=nome).first()
    )
    if gruppo is None:
        gruppo = Gruppo(nome=nome, chat_permanente=True, carriera=carriera)
        gruppo.save()
    else:
        dirty = []
        if gruppo.nome != nome:
            gruppo.nome = nome
            dirty.append("nome")
        if not gruppo.chat_permanente:
            gruppo.chat_permanente = True
            dirty.append("chat_permanente")
        if gruppo.carriera_id != carriera.pk:
            gruppo.carriera = carriera
            dirty.append("carriera")
        if dirty:
            gruppo.save(update_fields=[*dirty, "updated_at"])

    desiderati = _ids_membri_attivi(carriera)
    attuali = set(gruppo.membri.values_list("id", flat=True))
    if attuali != desiderati:
        gruppo.membri.set(desiderati)
        gruppo.save(update_fields=["updated_at"])
    return gruppo


def gruppi_chat_attivi_personaggio(personaggio):
    """Chat Korp/Dipartimento del personaggio, create e allineate se mancano."""
    if personaggio is None:
        return []
    memberships = (
        PersonaggioCarrieraMembership.objects.filter(
            personaggio=personaggio,
            data_a__isnull=True,
        )
        .select_related("carriera", "carriera__tipo_carriera")
        .order_by("carriera__nome", "id")
    )
    gruppi = []
    visti = set()
    for membership in memberships:
        carriera = membership.carriera
        if not carriera_ha_chat_di_gruppo(carriera):
            continue
        gruppo = sync_chat_gruppo_carriera(carriera)
        if gruppo is None or gruppo.id in visti:
            continue
        visti.add(gruppo.id)
        gruppi.append(gruppo)
    return gruppi


def personaggio_puo_scrivere_in_gruppo(personaggio, gruppo) -> bool:
    if personaggio is None or gruppo is None or not gruppo.chat_permanente or not gruppo.carriera_id:
        return False
    return PersonaggioCarrieraMembership.objects.filter(
        personaggio=personaggio,
        carriera_id=gruppo.carriera_id,
        data_a__isnull=True,
    ).exists()


def segna_messaggi_letti(personaggio, messaggio_ids) -> int:
    """Segna come letti i messaggi indicati per quel personaggio. Ritorna quanti erano da leggere."""
    ids = [mid for mid in dict.fromkeys(messaggio_ids) if mid]
    if not ids or personaggio is None:
        return 0
    ora = timezone.now()
    esistenti = {
        row.messaggio_id: row
        for row in LetturaMessaggio.objects.filter(personaggio=personaggio, messaggio_id__in=ids)
    }
    aggiornati = 0
    with transaction.atomic():
        for mid in ids:
            stato = esistenti.get(mid)
            if stato is None:
                LetturaMessaggio.objects.create(
                    messaggio_id=mid,
                    personaggio=personaggio,
                    letto=True,
                    data_lettura=ora,
                )
                aggiornati += 1
                continue
            if stato.letto:
                continue
            stato.letto = True
            if not stato.data_lettura:
                stato.data_lettura = ora
            stato.save(update_fields=["letto", "data_lettura", "updated_at"])
            aggiornati += 1
    return aggiornati


def crea_messaggio_gruppo(*, personaggio, gruppo, testo, titolo="", campagna):
    """Messaggio nel canale permanente. Il mittente lo ha già letto."""
    messaggio = Messaggio.objects.create(
        mittente=getattr(personaggio, "proprietario", None),
        mittente_personaggio=personaggio,
        destinatario_gruppo=gruppo,
        tipo_messaggio=Messaggio.TIPO_GRUPPO,
        titolo=(titolo or "Messaggio")[:150],
        testo=testo,
        is_staff_message=False,
        campagna=campagna,
    )
    LetturaMessaggio.objects.update_or_create(
        messaggio=messaggio,
        personaggio=personaggio,
        defaults={"letto": True, "data_lettura": timezone.now(), "cancellato": False},
    )
    return messaggio
