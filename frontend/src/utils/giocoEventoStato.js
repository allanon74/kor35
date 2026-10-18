/** Stato live dell'evento (gate azioni, scan, allibratore). Non è contenuto wiki. */
export const GIOCO_EVENTO_STATO_VUOTO = {
  evento_aperto: false,
  evento_titolo: null,
  azioni_live_abilitate: false,
  bypass_evento_gate: false,
  transazioni_giocatore_abilitate: false,
  nodo_scan_abilitato: false,
  allibratore_codici_abilitati: false,
};

function giocoEventoStatoDaPayload(data) {
  return {
    evento_aperto: !!data.evento_aperto,
    evento_titolo: data.evento_titolo || null,
    azioni_live_abilitate: !!data.azioni_live_abilitate,
    bypass_evento_gate: !!data.bypass_evento_gate,
    transazioni_giocatore_abilitate: !!data.transazioni_giocatore_abilitate,
    nodo_scan_abilitato: !!data.nodo_scan_abilitato,
    allibratore_codici_abilitati: !!data.allibratore_codici_abilitati,
  };
}

/**
 * Se il poll restituisce la stessa foto, torna `prev` (stesso riferimento).
 * Un oggetto nuovo a ogni minuto farebbe ridisegnare tutta l'app, wiki inclusa.
 */
export function mergeGiocoEventoStato(prev, data) {
  if (!data || typeof data !== 'object') return prev;
  const next = giocoEventoStatoDaPayload(data);
  if (!prev) return next;
  const uguale = Object.keys(GIOCO_EVENTO_STATO_VUOTO).every((key) => prev[key] === next[key]);
  return uguale ? prev : next;
}
