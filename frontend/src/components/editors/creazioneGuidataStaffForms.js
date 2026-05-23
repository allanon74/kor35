/** Valori iniziali e mapping form modali creazione guidata (staff). */

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
    navigazioneFine: false,
    flagImpostaCampo: false,
    flagAggiungiAbilita: false,
    passo_destinazione: null,
    payloadJson: '{}',
    payloadField: 'era',
    payloadSyncId: '',
    payloadAbilitaSyncIds: [],
    gruppoId: '',
    modalitaRewind: '',
  };
}

function flagsFromSceltaTipoPayload(tipo, payload = {}) {
  const hasField = Boolean(payload.field);
  const hasAbilita = Array.isArray(payload.abilita_sync_ids) && payload.abilita_sync_ids.length > 0;
  return {
    navigazioneFine: tipo === 'fine',
    flagImpostaCampo: tipo === 'imposta_campo' || tipo === 'combo' || hasField,
    flagAggiungiAbilita: tipo === 'aggiungi_abilita' || tipo === 'combo' || hasAbilita,
  };
}

export function sceltaFormFrom(s) {
  const payload = s.payload || {};
  const flags = flagsFromSceltaTipoPayload(s.tipo_azione, payload);
  return {
    id: s.id,
    etichetta: s.etichetta,
    descrizione: s.descrizione || '',
    ordine: s.ordine || 0,
    ...flags,
    passo_destinazione: s.passo_destinazione,
    payloadJson: JSON.stringify(s.payload || {}, null, 2),
    payloadField: payload.field || 'era',
    payloadSyncId: payload.sync_id || '',
    payloadAbilitaSyncIds: (payload.abilita_sync_ids || []).map(String),
    gruppoId: payload.gruppo_id || '',
    modalitaRewind: payload.modalita_rewind || '',
  };
}

/** Deriva tipo_azione backend da radio/checkbox del form. */
export function buildTipoAzioneFromSceltaForm(sceltaForm) {
  if (sceltaForm.navigazioneFine) return 'fine';
  if (sceltaForm.flagImpostaCampo && sceltaForm.flagAggiungiAbilita) return 'combo';
  if (sceltaForm.flagImpostaCampo) return 'imposta_campo';
  if (sceltaForm.flagAggiungiAbilita) return 'aggiungi_abilita';
  return 'naviga';
}

/** Etichetta sintetica per la lista scelte. */
export function formatSceltaAzioneSummary(scelta) {
  const parts = [];
  if (scelta?.tipo_azione === 'fine') parts.push('Fine percorso');
  else parts.push('Naviga');
  const p = scelta?.payload || {};
  if (p.field) parts.push('campo PG');
  if (p.abilita_sync_ids?.length) parts.push('abilità');
  return parts.join(' · ');
}

export function parsePayloadJson(raw) {
  if (!raw || !String(raw).trim()) return {};
  return JSON.parse(String(raw));
}

export function buildPayloadFromSceltaForm(sceltaForm) {
  const base = {};
  if (sceltaForm.gruppoId) base.gruppo_id = sceltaForm.gruppoId;
  if (sceltaForm.modalitaRewind) base.modalita_rewind = sceltaForm.modalitaRewind;

  const abilitaIds = (sceltaForm.payloadAbilitaSyncIds || [])
    .map((s) => String(s).trim())
    .filter(Boolean);

  const payload = { ...base };

  if (sceltaForm.flagImpostaCampo) {
    if (sceltaForm.payloadField === 'prefettura_esterna') {
      payload.field = 'prefettura_esterna';
      payload.value = true;
    } else {
      payload.field = sceltaForm.payloadField;
      payload.sync_id = sceltaForm.payloadSyncId || null;
    }
  }

  if (sceltaForm.flagAggiungiAbilita) {
    payload.abilita_sync_ids = abilitaIds;
  }

  if (!sceltaForm.navigazioneFine) {
    try {
      Object.assign(payload, parsePayloadJson(sceltaForm.payloadJson));
    } catch {
      /* ignore */
    }
  }

  return payload;
}
