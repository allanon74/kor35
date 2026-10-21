"""Note datate delle proposte tecniche (infusioni, tessiture, cerimoniali)."""

from django.utils import timezone
from django.utils.html import strip_tags

from .models import (
    ORIGINE_NOTA_INVIO,
    ORIGINE_NOTA_STAFF,
    TESTO_NOTA_INVIO_PROPOSTA,
    PropostaTecnicaNota,
)


def testo_nota_utile(raw) -> str:
    """HTML o testo con contenuto visibile. Stringa vuota se è solo markup."""
    if raw is None:
        return ""
    html = str(raw).strip()
    if not html:
        return ""
    plain = strip_tags(html).replace("\xa0", " ").replace("&nbsp;", " ")
    plain = " ".join(plain.split())
    if not plain:
        return ""
    return html


def registra_nota_proposta(proposta, testo, origine, creata_il=None):
    """
    Accoda una nota e, se è dello staff, aggiorna ``note_staff`` all'ultima.
    Non modifica le note precedenti. Ritorna None se il testo è vuoto.
    """
    if origine == ORIGINE_NOTA_INVIO:
        utile = TESTO_NOTA_INVIO_PROPOSTA
    else:
        utile = testo_nota_utile(testo)
    if not utile:
        return None
    nota = PropostaTecnicaNota.objects.create(
        proposta=proposta,
        testo=utile,
        origine=origine,
        creata_il=creata_il or timezone.now(),
    )
    if origine == ORIGINE_NOTA_STAFF:
        proposta.note_staff = utile
        proposta.save(update_fields=["note_staff", "updated_at"])
    return nota


def registra_nota_invio(proposta, quando=None):
    """Nota di sistema all'invio in valutazione."""
    return registra_nota_proposta(
        proposta,
        TESTO_NOTA_INVIO_PROPOSTA,
        origine=ORIGINE_NOTA_INVIO,
        creata_il=quando or proposta.data_invio or timezone.now(),
    )


def formato_note_messaggio(proposta) -> str:
    """Elenco leggibile per il messaggio al giocatore, in ordine cronologico."""
    righe = []
    for nota in proposta.note_log.order_by("creata_il", "created_at"):
        when = timezone.localtime(nota.creata_il) if timezone.is_aware(nota.creata_il) else nota.creata_il
        stamp = when.strftime("%d/%m/%Y %H:%M")
        plain = strip_tags(nota.testo or "").replace("\xa0", " ").strip()
        righe.append(f"[{stamp}] {plain}")
    if righe:
        return "\n".join(righe)
    return (proposta.note_staff or "").strip()
