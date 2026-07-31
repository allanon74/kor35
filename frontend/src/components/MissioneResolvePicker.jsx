import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { assegnaMissioneRisoluzione, getMissioni } from '../api';
import SearchableSelect from './editors/SearchableSelect';

/** Combobox staff/master per segnare risoluzione task. */
export default function MissioneResolvePicker({
  onLogout,
  tipoRisoluzione,
  eventoId,
  personaggioId,
  propostaTecnicaId,
  socialPostId,
  questId,
  giornoId,
  label = 'Risolve task',
  onAssigned,
}) {
  const [options, setOptions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    if (!eventoId) { setOptions([]); return; }
    try {
      const data = await getMissioni(
        { evento: eventoId, tipo_risoluzione: tipoRisoluzione, attiva: '1' },
        onLogout,
      );
      const rows = Array.isArray(data) ? data : data?.results || [];
      setOptions(rows.map((m) => ({
        value: m.id,
        label: `${m.titolo}${m.korp_nome ? ` [${m.korp_nome}]` : ''}${m.esclusiva ? ' ★' : ''}`,
      })));
    } catch {
      setOptions([]);
    }
  }, [eventoId, tipoRisoluzione, onLogout]);

  useEffect(() => { load(); }, [load]);

  const canSubmit = useMemo(
    () => selected && eventoId && personaggioId && !busy,
    [selected, eventoId, personaggioId, busy],
  );

  const assign = async () => {
    if (!canSubmit) return;
    setBusy(true);
    setMsg('');
    try {
      await assegnaMissioneRisoluzione({
        missione_id: selected,
        evento_id: Number(eventoId),
        personaggio_id: Number(personaggioId),
        proposta_tecnica_id: propostaTecnicaId || null,
        social_post_id: socialPostId || null,
        quest_id: questId || null,
        giorno_id: giornoId || null,
      }, onLogout);
      setMsg('Task assegnata — ricompensa accreditata');
      setSelected(null);
      onAssigned?.();
      await load();
    } catch (err) {
      setMsg(err?.message || 'Assegnazione fallita');
    } finally {
      setBusy(false);
    }
  };

  if (!eventoId) {
    return <p className="text-[10px] text-gray-500">{label}: serve un evento associato.</p>;
  }

  return (
    <div className="space-y-1.5 rounded border border-lime-900/50 bg-lime-950/20 p-2">
      <div className="text-[10px] font-bold uppercase text-lime-300">{label}</div>
      <SearchableSelect
        options={[{ value: null, label: '— Seleziona task —' }, ...options]}
        value={selected}
        onChange={setSelected}
        placeholder="Task…"
        minOptionsForSearch={0}
      />
      <button
        type="button"
        disabled={!canSubmit}
        onClick={assign}
        className="rounded bg-lime-800 px-2 py-1 text-[10px] font-bold uppercase text-white disabled:opacity-40"
      >
        Segna risoluzione
      </button>
      {msg ? <p className="text-[10px] text-gray-400">{msg}</p> : null}
    </div>
  );
}
