"""
Sandbox test + pubblicazione su flusso di produzione (creazione guidata).
"""

from django.db import transaction

from .models import CreazioneGuidataFlusso, CreazioneGuidataPasso, CreazioneGuidataScelta


def _clone_passi_e_scelte(source_flusso, target_flusso):
    """Copia passi e scelte da source a target (target deve essere vuoto)."""
    passo_map = {}
    for tp in (
        CreazioneGuidataPasso.objects.filter(flusso=source_flusso)
        .prefetch_related('scelte')
        .order_by('ordine', 'titolo')
    ):
        np = CreazioneGuidataPasso.objects.create(
            flusso=target_flusso,
            slug=tp.slug,
            titolo=tp.titolo,
            contenuto=tp.contenuto,
            immagine=tp.immagine,
            ordine=tp.ordine,
            opzioni_ui=dict(tp.opzioni_ui or {}),
        )
        passo_map[tp.id] = np

    for tp in CreazioneGuidataPasso.objects.filter(flusso=source_flusso).prefetch_related('scelte'):
        np = passo_map[tp.id]
        for scelta in tp.scelte.all().order_by('ordine', 'etichetta'):
            dest_id = scelta.passo_destinazione_id
            dest = passo_map.get(dest_id) if dest_id else None
            CreazioneGuidataScelta.objects.create(
                passo=np,
                etichetta=scelta.etichetta,
                descrizione=scelta.descrizione,
                ordine=scelta.ordine,
                tipo_azione=scelta.tipo_azione,
                passo_destinazione=dest,
                payload=dict(scelta.payload or {}),
            )

    if source_flusso.passo_iniziale_id and source_flusso.passo_iniziale_id in passo_map:
        target_flusso.passo_iniziale = passo_map[source_flusso.passo_iniziale_id]
    else:
        target_flusso.passo_iniziale = None
    target_flusso.save(update_fields=['passo_iniziale', 'updated_at'])
    return passo_map


@transaction.atomic
def crea_sandbox_test_da_produzione(flusso_produzione):
    """
    Crea (o resetta) un flusso test collegato, clonando lo stato attuale della produzione.
    """
    if flusso_produzione.modalita_test:
        raise ValueError('Il flusso sorgente deve essere di produzione.')
    if not flusso_produzione.passo_iniziale_id:
        raise ValueError('Imposta un passo iniziale sul flusso di produzione prima della sandbox.')

    sandbox = CreazioneGuidataFlusso.objects.filter(
        flusso_produzione=flusso_produzione,
        modalita_test=True,
    ).first()

    if sandbox:
        CreazioneGuidataPasso.objects.filter(flusso=sandbox).delete()
    else:
        base_slug = flusso_produzione.slug[:60]
        test_slug = f'{base_slug}-test'
        n = 0
        while CreazioneGuidataFlusso.objects.filter(slug=test_slug).exists():
            n += 1
            test_slug = f'{base_slug}-test-{n}'[:80]

        sandbox = CreazioneGuidataFlusso.objects.create(
            slug=test_slug,
            titolo=f'{flusso_produzione.titolo} (sandbox test)',
            attivo=True,
            modalita_test=True,
            flusso_produzione=flusso_produzione,
            campagna=flusso_produzione.campagna,
        )

    _clone_passi_e_scelte(flusso_produzione, sandbox)
    return sandbox


@transaction.atomic
def pubblica_sandbox_su_produzione(flusso_test):
    """
    Sovrascrive il flusso di produzione con passi/scelte della sandbox test.
    Il flusso test resta invariato per ulteriori iterazioni.
    """
    if not flusso_test.modalita_test:
        raise ValueError('Solo un flusso sandbox (modalità test) può essere pubblicato.')
    prod = flusso_test.flusso_produzione
    if not prod:
        raise ValueError('Sandbox non collegata a un flusso di produzione.')
    if prod.modalita_test:
        raise ValueError('Il flusso di destinazione non è di produzione.')

    CreazioneGuidataPasso.objects.filter(flusso=prod).delete()
    _clone_passi_e_scelte(flusso_test, prod)

    prod.titolo = flusso_test.titolo.replace(' (sandbox test)', '').strip() or prod.titolo
    prod.save(update_fields=['titolo', 'updated_at'])
    return prod


def get_sandbox_for_produzione(flusso_produzione):
    if not flusso_produzione or flusso_produzione.modalita_test:
        return None
    return CreazioneGuidataFlusso.objects.filter(
        flusso_produzione=flusso_produzione,
        modalita_test=True,
    ).first()


def sandbox_ha_modifiche_non_pubblicate(flusso_produzione):
    """True se la sandbox esiste ed è stata aggiornata dopo l'ultima modifica produzione."""
    sandbox = get_sandbox_for_produzione(flusso_produzione)
    if not sandbox:
        return False
    return sandbox.updated_at > flusso_produzione.updated_at
