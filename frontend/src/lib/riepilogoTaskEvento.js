/**
 * Specchietto staff «Premi task per KORP»: normalizzazione delle righe KORP,
 * totali dell'evento e avvisi che spiegano i totali a zero.
 */

/** Righe KORP con i totali di riga, ricalcolati se il backend non li invia. */
export const righeRiepilogoTask = (evento) => {
    const righe = Array.isArray(evento?.missioni_riepilogo) ? evento.missioni_riepilogo : [];
    return righe.map((row) => ({
        ...row,
        crediti_totale: row.crediti_totale
            ?? Number(row.crediti_korp || 0) + Number(row.crediti_non_korp || 0),
        prestigio_totale: row.prestigio_totale
            ?? Number(row.prestigio_korp || 0) + Number(row.prestigio_non_korp || 0),
        n_task_totale: row.n_task_totale
            ?? Number(row.n_task_korp || 0) + Number(row.n_task_non_korp || 0),
    }));
};

/**
 * Totali dello specchietto. `missioni_riepilogo_totali` arriva dal backend; il
 * fallback copre un backend non ancora aggiornato ricavando i totali dalle sole
 * righe KORP (i contatori delle task spente restano a zero e il totale base,
 * non derivabile, resta `null`).
 */
export const totaliRiepilogoTask = (evento, righe) => {
    const dalBackend = evento?.missioni_riepilogo_totali;
    if (dalBackend && typeof dalBackend === 'object') return dalBackend;
    const max = (campo) => righe.reduce((acc, row) => Math.max(acc, Number(row[campo] || 0)), 0);
    const nTask = max('n_task_totale');
    return {
        n_task_collegate: nTask,
        n_task_attive: nTask,
        n_task_spente_evento: 0,
        n_task_spente_catalogo: 0,
        crediti_base: null,
        prestigio_base: null,
        crediti_max: max('crediti_totale'),
        prestigio_max: max('prestigio_totale'),
    };
};

/** Avvisi che spiegano perché i totali sono a zero o incompleti. */
export const noteRiepilogoTask = (totali) => {
    const note = [];
    const spenteCatalogo = Number(totali?.n_task_spente_catalogo || 0);
    const spenteEvento = Number(totali?.n_task_spente_evento || 0);
    if (spenteCatalogo > 0) {
        note.push(spenteCatalogo === 1
            ? '1 task collegata è spenta nel catalogo (Gestione Tasks → Attiva) '
                + 'e non entra nei totali.'
            : `${spenteCatalogo} task collegate sono spente nel catalogo `
                + '(Gestione Tasks → Attiva) e non entrano nei totali.');
    }
    if (spenteEvento > 0) {
        note.push(spenteEvento === 1
            ? '1 task è disattivata per questo evento dal pannello Tasks evento.'
            : `${spenteEvento} task sono disattivate per questo evento `
                + 'dal pannello Tasks evento.');
    }
    if (
        Number(totali?.n_task_attive || 0) > 0
        && Number(totali?.crediti_max || 0) === 0
        && Number(totali?.prestigio_max || 0) === 0
    ) {
        note.push('Le task conteggiate non hanno premi configurati: i totali restano a zero.');
    }
    return note;
};
