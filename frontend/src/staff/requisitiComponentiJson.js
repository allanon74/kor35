/**
 * Schema vincoli componenti stiva (allineato a pilotaggio/componenti_riparazione.py).
 *
 * Riparazione:
 *   { tipo: "specifico", mattone_id, quantita }
 *   { tipo: "scelta", mattone_ids: [], quantita }
 *
 * Ricarica (batteria/serbatoio): stesso schema + ricarica (> 0).
 */

export function parseRequisitiJson(raw, { mode = 'riparazione' } = {}) {
  let data = raw;
  if (typeof raw === 'string') {
    try {
      data = JSON.parse(raw || '[]');
    } catch {
      return { ok: false, error: 'JSON non valido.', items: [] };
    }
  }
  if (!Array.isArray(data)) {
    return { ok: false, error: 'Attesa una lista JSON.', items: [] };
  }

  const richiediRicarica = mode === 'ricarica';
  const items = [];
  for (const item of data) {
    if (!item || typeof item !== 'object') continue;
    const tipo = String(item.tipo || '').trim().toLowerCase();
    const quantita = Number.parseInt(item.quantita, 10);
    if (!Number.isFinite(quantita) || quantita <= 0) continue;

    if (tipo === 'specifico') {
      const mattone_id = String(item.mattone_id || '').trim();
      if (!mattone_id) continue;
      const entry = { tipo: 'specifico', mattone_id, quantita };
      if (richiediRicarica) {
        const ricarica = Number(item.ricarica);
        if (!Number.isFinite(ricarica) || ricarica <= 0) continue;
        entry.ricarica = ricarica;
      }
      items.push(entry);
    } else if (tipo === 'scelta') {
      const mattone_ids = (item.mattone_ids || [])
        .map((x) => String(x || '').trim())
        .filter(Boolean);
      if (!mattone_ids.length) continue;
      const entry = { tipo: 'scelta', mattone_ids, quantita };
      if (richiediRicarica) {
        const ricarica = Number(item.ricarica);
        if (!Number.isFinite(ricarica) || ricarica <= 0) continue;
        entry.ricarica = ricarica;
      }
      items.push(entry);
    }
  }

  return { ok: true, error: '', items };
}

export function stringifyRequisitiJson(items, pretty = true) {
  const safe = Array.isArray(items) ? items : [];
  return pretty ? JSON.stringify(safe, null, 2) : JSON.stringify(safe);
}

export function emptyVincolo(tipo = 'specifico', { withRicarica = false } = {}) {
  const base = {
    tipo,
    quantita: 1,
    mattone_id: '',
    mattone_ids: [],
  };
  if (withRicarica) base.ricarica = 10;
  return base;
}

export function vincoliToApiPayload(items, { mode = 'riparazione' } = {}) {
  const parsed = parseRequisitiJson(items, { mode });
  return parsed.ok ? parsed.items : [];
}

export function sumRicaricaConfigurata(items) {
  return (items || []).reduce((acc, v) => acc + (Number(v.ricarica) || 0), 0);
}

export function labelMattone(catalogo, mattoneId) {
  const m = (catalogo || []).find((x) => String(x.id) === String(mattoneId));
  if (!m) return mattoneId || '—';
  const col = m.colore_nome ? ` (${m.colore_nome})` : '';
  const idx = m.indice_componente != null ? `[${m.indice_componente}] ` : '';
  return `${idx}${m.nome || 'Componente'}${col}`;
}
