import React, { useMemo } from 'react';
import { Package } from 'lucide-react';

export function selezioneToArray(selection) {
  if (!selection || typeof selection !== 'object') return [];
  return Object.entries(selection)
    .filter(([, q]) => Number(q) > 0)
    .map(([mattone_id, quantita]) => ({ mattone_id, quantita: Number(quantita) }));
}

/**
 * Validazione client allineata a pilotaggio/componenti_riparazione.py
 */
export function validateSelezioneComponenti(vincoli, selection, stivaRighe = []) {
  if (!Array.isArray(vincoli) || vincoli.length === 0) {
    return { ok: false, message: 'Nessun requisito componenti configurato.' };
  }

  const alloc = {};
  for (const [mid, qty] of Object.entries(selection || {})) {
    const q = Number(qty);
    if (mid && q > 0) alloc[mid] = (alloc[mid] || 0) + q;
  }
  if (!Object.keys(alloc).length) {
    return { ok: false, message: 'Seleziona i componenti necessari.' };
  }

  const disponibile = {};
  for (const r of stivaRighe || []) {
    disponibile[r.mattone_id] = Number(r.quantita) || 0;
  }
  for (const [mid, qty] of Object.entries(alloc)) {
    if ((disponibile[mid] || 0) < qty) {
      return { ok: false, message: 'Componenti insufficienti in stiva nave.' };
    }
  }

  const residui = { ...alloc };
  for (const req of vincoli) {
    const qty = Number(req.quantita) || 0;
    if (req.tipo === 'specifico') {
      const mid = req.mattone_id;
      const used = Math.min(residui[mid] || 0, qty);
      if (used < qty) {
        return { ok: false, message: 'Requisiti specifici non soddisfatti.' };
      }
      residui[mid] = (residui[mid] || 0) - used;
    } else if (req.tipo === 'scelta') {
      let remaining = qty;
      for (const mid of req.mattone_ids || []) {
        if (remaining <= 0) break;
        const take = Math.min(residui[mid] || 0, remaining);
        if (take > 0) {
          residui[mid] = (residui[mid] || 0) - take;
          remaining -= take;
        }
      }
      if (remaining > 0) {
        return { ok: false, message: 'Gruppo a scelta non soddisfatto.' };
      }
    }
  }
  for (const qty of Object.values(residui)) {
    if (qty > 0) {
      return { ok: false, message: 'Rimuovi componenti in eccesso dalla selezione.' };
    }
  }
  return { ok: true, message: '' };
}

function labelVincolo(req) {
  const ric = req.ricarica != null ? ` → +${req.ricarica}` : '';
  if (req.tipo === 'specifico') {
    const nome = req.mattone_nome || req.mattone_id;
    const col = req.colore_nome ? ` (${req.colore_nome})` : '';
    return `${req.quantita}× ${nome}${col}${ric}`;
  }
  const nomi = (req.opzioni || []).map((o) => o.colore_nome || o.mattone_nome).filter(Boolean);
  const alt = nomi.length ? nomi.join(' / ') : 'opzioni configurate';
  return `${req.quantita}× a scelta tra ${alt}${ric}`;
}

export default function ComponentiRiparazionePicker({
  vincoli,
  stiva,
  selection,
  onSelectionChange,
  title = 'Componenti da stiva nave',
  hintOk = 'Selezione completa — puoi procedere.',
  hintEmpty = 'Seleziona i componenti necessari.',
}) {
  const righe = stiva?.righe || [];

  const mattoneIdsRilevanti = useMemo(() => {
    const ids = new Set();
    for (const req of vincoli || []) {
      if (req.tipo === 'specifico' && req.mattone_id) ids.add(req.mattone_id);
      if (req.tipo === 'scelta') {
        for (const o of req.opzioni || []) {
          if (o.mattone_id) ids.add(o.mattone_id);
        }
      }
    }
    return ids;
  }, [vincoli]);

  const righePicker = useMemo(() => {
    const byId = Object.fromEntries(righe.map((r) => [r.mattone_id, r]));
    const out = [];
    for (const id of mattoneIdsRilevanti) {
      const row = byId[id];
      out.push(
        row || {
          mattone_id: id,
          nome: 'Componente',
          colore_nome: '',
          quantita: 0,
        },
      );
    }
    return out.sort((a, b) => (a.indice_componente ?? 0) - (b.indice_componente ?? 0));
  }, [righe, mattoneIdsRilevanti]);

  const validation = validateSelezioneComponenti(vincoli, selection, righe);

  const setQty = (mattoneId, next) => {
    const row = righe.find((r) => r.mattone_id === mattoneId);
    const max = row ? Number(row.quantita) || 0 : 0;
    const q = Math.max(0, Math.min(max, Number(next) || 0));
    onSelectionChange((prev) => {
      const copy = { ...(prev || {}) };
      if (q <= 0) delete copy[mattoneId];
      else copy[mattoneId] = q;
      return copy;
    });
  };

  if (!vincoli?.length) {
    return (
      <p className="text-amber-200/90 text-xs border border-amber-800/40 rounded-md p-2 bg-amber-950/30">
        Riparazione a componenti attiva ma nessun requisito configurato sul sottosistema.
      </p>
    );
  }

  return (
    <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-3 space-y-3">
      <div className="flex items-center gap-2 text-emerald-300 text-sm font-semibold">
        <Package size={18} />
        {title}
      </div>

      <ul className="text-xs text-gray-400 space-y-1">
        {vincoli.map((req, i) => (
          <li key={`v-${i}`} className="font-mono">
            • {labelVincolo(req)}
          </li>
        ))}
      </ul>

      <div className="space-y-2">
        {righePicker.map((r) => {
          const sel = Number(selection?.[r.mattone_id]) || 0;
          const inStiva = Number(r.quantita) || 0;
          return (
            <div
              key={r.mattone_id}
              className="flex items-center justify-between gap-2 bg-gray-900/60 rounded-md px-2 py-2 border border-gray-700/80"
            >
              <div className="min-w-0 flex-1">
                <div className="text-sm text-white truncate">{r.nome}</div>
                <div className="text-[10px] text-gray-500">
                  {r.colore_nome ? `${r.colore_nome} · ` : ''}
                  in stiva: <span className="text-gray-300">{inStiva}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  disabled={sel <= 0}
                  className="w-8 h-8 rounded bg-gray-700 text-white disabled:opacity-40"
                  onClick={() => setQty(r.mattone_id, sel - 1)}
                  aria-label="Meno"
                >
                  −
                </button>
                <span className="w-6 text-center font-mono text-sm text-emerald-200">{sel}</span>
                <button
                  type="button"
                  disabled={sel >= inStiva}
                  className="w-8 h-8 rounded bg-emerald-800 text-white disabled:opacity-40"
                  onClick={() => setQty(r.mattone_id, sel + 1)}
                  aria-label="Più"
                >
                  +
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {validation.ok ? (
        <p className="text-emerald-400/90 text-xs">{hintOk}</p>
      ) : (
        <p className="text-amber-200/90 text-xs">{validation.message}</p>
      )}
    </div>
  );
}
