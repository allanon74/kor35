import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, RefreshCw, Save } from 'lucide-react';
import {
  staffCreateCartaComboReliquiario,
  staffDeleteCartaComboReliquiario,
  staffGetCarteComboReliquiario,
  staffUpdateCartaComboReliquiario,
  getPunteggiList,
} from '../../api';
import StatModInline from './inlines/StatModInline';

const TRIGGER_OPTIONS = [
  { value: 'LEGAME', label: 'Stesso legame_id' },
  { value: 'SET', label: 'Stesso set_collezione' },
  { value: 'CARTE', label: 'Carte specifiche (codici)' },
  { value: 'ENERGIE_NAT', label: 'Energie naturali distinte' },
  { value: 'ENERGIE_SOP', label: 'Energie soprannaturali distinte' },
];

const emptyCombo = () => ({
  codice: '',
  nome: '',
  testo: '',
  colore: '#10b981',
  tipo_trigger: 'LEGAME',
  param_legame_id: '',
  param_set_collezione: '',
  param_carte_codici: [],
  param_min_count: 2,
  ordine: 0,
  attiva: true,
  statistiche: [],
});

function normalizeStats(rows) {
  return (rows || []).map((row) => ({
    ...row,
    statistica: row.statistica?.id || row.statistica,
    limit_a_aure: row.limit_a_aure || [],
    limit_a_elementi: row.limit_a_elementi || [],
    tipo_modificatore: row.tipo_modificatore || 'ADD',
    valore: row.valore ?? 0,
  }));
}

export default function ComboReliquiarioStaffPanel({ onLogout, carteCatalogo = [] }) {
  const [combos, setCombos] = useState([]);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(emptyCombo());
  const [punteggi, setPunteggi] = useState([]);
  const [codiciText, setCodiciText] = useState('');
  const [msg, setMsg] = useState('');

  const statsOptions = useMemo(() => punteggi.filter((p) => p.tipo === 'ST'), [punteggi]);
  const auraOptions = useMemo(() => punteggi.filter((p) => p.tipo === 'AU'), [punteggi]);
  const elementOptions = useMemo(() => punteggi.filter((p) => p.tipo === 'EL'), [punteggi]);

  const load = useCallback(async () => {
    const [comboRows, punt] = await Promise.all([
      staffGetCarteComboReliquiario(onLogout),
      getPunteggiList(onLogout),
    ]);
    setCombos(Array.isArray(comboRows) ? comboRows : comboRows?.results || []);
    setPunteggi(punt || []);
  }, [onLogout]);

  useEffect(() => { load().catch(() => {}); }, [load]);

  const selectCombo = (c) => {
    setSelected(c);
    setForm({
      ...emptyCombo(),
      ...c,
      statistiche: normalizeStats(c.statistiche),
    });
    setCodiciText((c.param_carte_codici || []).join('\n'));
  };

  const save = async () => {
    try {
      const payload = {
        ...form,
        param_carte_codici: codiciText
          .split(/[\n,]+/)
          .map((s) => s.trim())
          .filter(Boolean),
        statistiche: normalizeStats(form.statistiche),
      };
      if (selected?.id) {
        await staffUpdateCartaComboReliquiario(selected.id, payload, onLogout);
      } else {
        await staffCreateCartaComboReliquiario(payload, onLogout);
      }
      setMsg('Combo salvata.');
      setSelected(null);
      setForm(emptyCombo());
      setCodiciText('');
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio fallito.');
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-bold">Combo reliquiario ({combos.length})</h3>
          <button
            type="button"
            className="rounded bg-violet-800 px-2 py-1 text-xs"
            onClick={() => { setSelected(null); setForm(emptyCombo()); setCodiciText(''); }}
          >
            <Plus size={12} className="inline" /> Nuova
          </button>
        </div>
        {msg && <p className="mb-2 text-xs text-amber-300">{msg}</p>}
        <ul className="max-h-[60vh] space-y-1 overflow-y-auto text-sm">
          {combos.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={`w-full rounded px-2 py-2 text-left hover:bg-gray-800 ${selected?.id === c.id ? 'bg-gray-700' : ''}`}
                onClick={() => selectCombo(c)}
              >
                <span className="font-bold" style={{ color: c.colore || '#10b981' }}>{c.nome}</span>
                <span className="ml-2 text-xs text-gray-500">{c.codice} · {c.tipo_trigger}</span>
              </button>
            </li>
          ))}
        </ul>
        <button type="button" className="mt-2 text-xs text-gray-400 underline" onClick={load}>
          <RefreshCw size={12} className="inline" /> Aggiorna
        </button>
      </div>

      <div className="space-y-2 rounded border border-gray-700 p-3">
        <h3 className="font-bold">{selected ? 'Modifica combo' : 'Nuova combo'}</h3>
        <p className="text-[10px] text-gray-500">
          Le combo non compaiono sulla carta. Quando attive, mostrano il testo sotto il reliquiario e applicano i modificatori statistica.
        </p>
        {['codice', 'nome'].map((f) => (
          <input
            key={f}
            className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
            placeholder={f}
            value={form[f] || ''}
            onChange={(e) => setForm((p) => ({ ...p, [f]: e.target.value }))}
          />
        ))}
        <label className="block text-xs text-gray-400">
          Testo combo (visibile al giocatore)
          <textarea
            className="mt-0.5 h-24 w-full rounded border border-gray-600 bg-gray-900 p-2 text-sm"
            value={form.testo || ''}
            onChange={(e) => setForm((p) => ({ ...p, testo: e.target.value }))}
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs text-gray-400">
            Colore
            <input
              type="color"
              className="mt-0.5 h-9 w-full rounded border border-gray-600 bg-gray-900"
              value={form.colore || '#10b981'}
              onChange={(e) => setForm((p) => ({ ...p, colore: e.target.value }))}
            />
          </label>
          <label className="text-xs text-gray-400">
            Ordine
            <input
              type="number"
              className="mt-0.5 w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
              value={form.ordine ?? 0}
              onChange={(e) => setForm((p) => ({ ...p, ordine: Number(e.target.value) }))}
            />
          </label>
        </div>
        <label className="block text-xs text-gray-400">
          Tipo trigger
          <select
            className="mt-0.5 w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
            value={form.tipo_trigger}
            onChange={(e) => setForm((p) => ({ ...p, tipo_trigger: e.target.value }))}
          >
            {TRIGGER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
        {form.tipo_trigger === 'LEGAME' && (
          <input
            className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
            placeholder="legame_id"
            value={form.param_legame_id || ''}
            onChange={(e) => setForm((p) => ({ ...p, param_legame_id: e.target.value }))}
          />
        )}
        {form.tipo_trigger === 'SET' && (
          <input
            className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
            placeholder="set_collezione"
            value={form.param_set_collezione || ''}
            onChange={(e) => setForm((p) => ({ ...p, param_set_collezione: e.target.value }))}
          />
        )}
        {form.tipo_trigger === 'CARTE' && (
          <label className="block text-xs text-gray-400">
            Codici carta (uno per riga)
            <textarea
              className="mt-0.5 h-20 w-full rounded border border-gray-600 bg-gray-900 p-2 font-mono text-xs"
              value={codiciText}
              onChange={(e) => setCodiciText(e.target.value)}
              placeholder={carteCatalogo.slice(0, 3).map((c) => c.codice).join('\n')}
            />
          </label>
        )}
        {form.tipo_trigger !== 'CARTE' && (
          <label className="block text-xs text-gray-400">
            Soglia minima
            <input
              type="number"
              min={1}
              className="mt-0.5 w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
              value={form.param_min_count ?? 2}
              onChange={(e) => setForm((p) => ({ ...p, param_min_count: Number(e.target.value) }))}
            />
          </label>
        )}
        <label className="flex items-center gap-2 text-xs text-gray-400">
          <input
            type="checkbox"
            checked={!!form.attiva}
            onChange={(e) => setForm((p) => ({ ...p, attiva: e.target.checked }))}
          />
          Attiva
        </label>
        <StatModInline
          items={form.statistiche || []}
          options={statsOptions}
          auraOptions={auraOptions}
          elementOptions={elementOptions}
          onAdd={() => setForm((p) => ({
            ...p,
            statistiche: [...(p.statistiche || []), {
              statistica: null,
              valore: 0,
              tipo_modificatore: 'ADD',
              usa_limitazione_aura: false,
              usa_limitazione_elemento: false,
              usa_condizione_text: false,
              condizione_text: '',
              limit_a_aure: [],
              limit_a_elementi: [],
            }],
          }))}
          onChange={(i, field, val) => setForm((p) => {
            const next = [...(p.statistiche || [])];
            next[i] = { ...next[i], [field]: val };
            return { ...p, statistiche: next };
          })}
          onRemove={(i) => setForm((p) => ({
            ...p,
            statistiche: (p.statistiche || []).filter((_, idx) => idx !== i),
          }))}
        />
        <div className="flex gap-2">
          <button type="button" className="flex items-center gap-1 rounded bg-emerald-800 px-3 py-1 text-sm" onClick={save}>
            <Save size={14} /> Salva
          </button>
          {selected?.id && (
            <button
              type="button"
              className="rounded bg-red-900 px-3 py-1 text-sm"
              onClick={async () => {
                await staffDeleteCartaComboReliquiario(selected.id, onLogout);
                setSelected(null);
                setForm(emptyCombo());
                await load();
              }}
            >
              Elimina
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
