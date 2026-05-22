/** Valori iniziali e mapping form modali creazione guidata (staff). */

export const TIPO_AZIONE_OPTIONS = [
  { value: 'naviga', label: 'Naviga (passo successivo)' },
  { value: 'imposta_campo', label: 'Imposta campo personaggio' },
  { value: 'aggiungi_abilita', label: 'Aggiungi abilità suggerite' },
  { value: 'combo', label: 'Combinata (campo + abilità + navigazione)' },
  { value: 'fine', label: 'Fine percorso' },
];

export const PRESENTAZIONE_OPTIONS = [
  { value: 'pulsanti', label: 'Pulsanti' },
  { value: 'si_no', label: 'Sì / No' },
  { value: 'radio', label: 'Radio (scelta unica)' },
  { value: 'radio_abilita', label: 'Radio abilità' },
];

export const REWIND_OPTIONS = [
  { value: 'ramo', label: 'Ramo (torna indietro nel percorso)' },
  { value: 'toggle', label: 'Toggle (sì/no: solo cambia abilità)' },
];

export const CAMPO_OPTIONS = [
  { value: 'era', label: 'Era' },
  { value: 'prefettura', label: 'Prefettura' },
  { value: 'prefettura_esterna', label: 'Prefettura esterna' },
  { value: 'tipologia', label: 'Tipologia personaggio' },
];

export function emptyFlussoForm() {
  return {
    slug: '',
    titolo: '',
    attivo: false,
    modalita_test: false,
    flusso_produzione: null,
    passo_iniziale: null,
  };
}

export function flussoFormFromDetail(data) {
  if (!data) return emptyFlussoForm();
  return {
    slug: data.slug || '',
    titolo: data.titolo || '',
    attivo: !!data.attivo,
    modalita_test: !!data.modalita_test,
    flusso_produzione: data.flusso_produzione || null,
    passo_iniziale: data.passo_iniziale || null,
  };
}

export function emptyPassoForm(ordine = 0) {
  return {
    slug: '',
    titolo: '',
    contenuto: '',
    ordine,
    opzioni_ui: {
      presentazione: 'pulsanti',
      gruppo_id: '',
      modalita_rewind: 'ramo',
      widget_fondo: null,
    },
  };
}

export function passoFormFrom(p) {
  const oui = p?.opzioni_ui && typeof p.opzioni_ui === 'object' ? p.opzioni_ui : {};
  return {
    slug: p.slug || '',
    titolo: p.titolo || '',
    contenuto: p.contenuto || '',
    ordine: p.ordine || 0,
    opzioni_ui: {
      presentazione: oui.presentazione || 'pulsanti',
      gruppo_id: oui.gruppo_id || '',
      modalita_rewind: oui.modalita_rewind || 'ramo',
      widget_fondo: oui.widget_fondo || null,
    },
  };
}

export function emptySceltaForm() {
  return {
    id: null,
    etichetta: '',
    descrizione: '',
    ordine: 0,
    tipo_azione: 'naviga',
    passo_destinazione: null,
    payloadJson: '{}',
    payloadField: 'era',
    payloadSyncId: '',
    payloadAbilitaSyncIds: [],
    gruppoId: '',
    modalitaRewind: '',
  };
}

export function sceltaFormFrom(s) {
  return {
    id: s.id,
    etichetta: s.etichetta,
    descrizione: s.descrizione || '',
    ordine: s.ordine || 0,
    tipo_azione: s.tipo_azione,
    passo_destinazione: s.passo_destinazione,
    payloadJson: JSON.stringify(s.payload || {}, null, 2),
    payloadField: s.payload?.field || 'era',
    payloadSyncId: s.payload?.sync_id || '',
    payloadAbilitaSyncIds: (s.payload?.abilita_sync_ids || []).map(String),
    gruppoId: s.payload?.gruppo_id || '',
    modalitaRewind: s.payload?.modalita_rewind || '',
  };
}

export function parsePayloadJson(raw) {
  if (!raw || !String(raw).trim()) return {};
  return JSON.parse(String(raw));
}

export function buildPayloadFromSceltaForm(sceltaForm) {
  const tipo = sceltaForm.tipo_azione;
  const base = {};
  if (sceltaForm.gruppoId) base.gruppo_id = sceltaForm.gruppoId;
  if (sceltaForm.modalitaRewind) base.modalita_rewind = sceltaForm.modalitaRewind;

  const abilitaIds = (sceltaForm.payloadAbilitaSyncIds || [])
    .map((s) => String(s).trim())
    .filter(Boolean);

  if (tipo === 'imposta_campo') {
    if (sceltaForm.payloadField === 'prefettura_esterna') {
      return { ...base, field: 'prefettura_esterna', value: true };
    }
    return { ...base, field: sceltaForm.payloadField, sync_id: sceltaForm.payloadSyncId || null };
  }
  if (tipo === 'aggiungi_abilita') {
    return { ...base, abilita_sync_ids: abilitaIds };
  }
  if (tipo === 'combo') {
    const combo = { ...base };
    if (abilitaIds.length) combo.abilita_sync_ids = abilitaIds;
    if (sceltaForm.payloadField && sceltaForm.payloadField !== 'prefettura_esterna') {
      combo.field = sceltaForm.payloadField;
      combo.sync_id = sceltaForm.payloadSyncId || null;
    } else if (sceltaForm.payloadField === 'prefettura_esterna') {
      combo.field = 'prefettura_esterna';
      combo.value = true;
    }
    try {
      Object.assign(combo, parsePayloadJson(sceltaForm.payloadJson));
    } catch {
      /* ignore */
    }
    return combo;
  }
  try {
    return { ...base, ...parsePayloadJson(sceltaForm.payloadJson) };
  } catch {
    return base;
  }
}
