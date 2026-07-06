import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import {
  staffCreateCartaComboReliquiario,
  staffDeleteCartaComboReliquiario,
  staffGetCarteComboReliquiario,
  staffUpdateCartaComboReliquiario,
  getPunteggiList,
} from '../../api';
import {
  LabeledField,
  StaffFieldGrid,
  StaffListRow,
  StaffListToolbar,
  StaffModal,
  StaffSection,
  staffInputClass,
} from '../../staff/StaffCrudUi';
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
  const [editTarget, setEditTarget] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
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

  const openModal = (c = null) => {
    setEditTarget(c);
    setForm(c ? { ...emptyCombo(), ...c, statistiche: normalizeStats(c.statistiche) } : emptyCombo());
    setCodiciText((c?.param_carte_codici || []).join('\n'));
    setModalOpen(true);
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
      if (editTarget?.id) {
        await staffUpdateCartaComboReliquiario(editTarget.id, payload, onLogout);
      } else {
        await staffCreateCartaComboReliquiario(payload, onLogout);
      }
      setMsg('Combo salvata.');
      setModalOpen(false);
      setEditTarget(null);
      setForm(emptyCombo());
      setCodiciText('');
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio fallito.');
    }
  };

  const deleteCombo = async (id) => {
    try {
      await staffDeleteCartaComboReliquiario(id, onLogout);
      setMsg('Combo eliminata.');
      if (editTarget?.id === id) {
        setModalOpen(false);
        setEditTarget(null);
      }
      await load();
    } catch (e) {
      setMsg(e?.message || 'Eliminazione fallita.');
    }
  };

  return (
    <div>
      {msg && <p className="mb-2 text-xs text-amber-300">{msg}</p>}
      <StaffListToolbar
        title="Combo reliquiario"
        count={combos.length}
        onAdd={() => openModal(null)}
        addLabel="Nuova combo"
      />
      <p className="mb-3 text-xs text-gray-500">
        Le combo non compaiono sulla carta. Se attive, mostrano testo sotto il reliquiario e applicano modificatori al personaggio.
      </p>
      <ul className="max-h-[70vh] space-y-1 overflow-y-auto">
        {combos.map((c) => (
          <StaffListRow
            key={c.id}
            onEdit={() => openModal(c)}
            onDelete={() => deleteCombo(c.id)}
            deleteConfirm={`Eliminare la combo «${c.nome}»?`}
          >
            <p className="font-bold" style={{ color: c.colore || '#10b981' }}>{c.nome}</p>
            <p className="text-xs text-gray-500">
              <span className="text-gray-400">Codice:</span> {c.codice}
              {' · '}
              <span className="text-gray-400">Trigger:</span> {c.tipo_trigger}
              {!c.attiva && <span className="ml-2 text-amber-500">(disattiva)</span>}
            </p>
          </StaffListRow>
        ))}
      </ul>
      <button type="button" className="mt-2 text-xs text-gray-400 underline" onClick={load}>
        <RefreshCw size={12} className="inline" /> Aggiorna
      </button>

      <StaffModal
        open={modalOpen}
        wide
        title={editTarget?.id ? `Modifica combo — ${form.nome}` : 'Nuova combo reliquiario'}
        onClose={() => setModalOpen(false)}
        onSave={save}
      >
        <div className="space-y-4">
          <StaffFieldGrid>
            <LabeledField label="Codice" required>
              <input
                className={staffInputClass('font-mono')}
                value={form.codice || ''}
                onChange={(e) => setForm((p) => ({ ...p, codice: e.target.value }))}
              />
            </LabeledField>
            <LabeledField label="Nome" required>
              <input
                className={staffInputClass()}
                value={form.nome || ''}
                onChange={(e) => setForm((p) => ({ ...p, nome: e.target.value }))}
              />
            </LabeledField>
          </StaffFieldGrid>
          <LabeledField label="Testo combo" hint="Visibile al giocatore quando la combo è attiva.">
            <textarea
              className={staffInputClass('min-h-[80px]')}
              value={form.testo || ''}
              onChange={(e) => setForm((p) => ({ ...p, testo: e.target.value }))}
            />
          </LabeledField>
          <StaffFieldGrid>
            <LabeledField label="Colore UI">
              <input
                type="color"
                className="mt-1 h-9 w-full rounded border border-gray-600 bg-gray-900"
                value={form.colore || '#10b981'}
                onChange={(e) => setForm((p) => ({ ...p, colore: e.target.value }))}
              />
            </LabeledField>
            <LabeledField label="Ordine">
              <input
                type="number"
                className={staffInputClass()}
                value={form.ordine ?? 0}
                onChange={(e) => setForm((p) => ({ ...p, ordine: Number(e.target.value) }))}
              />
            </LabeledField>
          </StaffFieldGrid>
          <LabeledField label="Tipo trigger">
            <select
              className={staffInputClass()}
              value={form.tipo_trigger}
              onChange={(e) => setForm((p) => ({ ...p, tipo_trigger: e.target.value }))}
            >
              {TRIGGER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </LabeledField>
          {form.tipo_trigger === 'LEGAME' && (
            <LabeledField label="Legame ID" hint="Stesso valore del campo Legame sulle carte.">
              <input
                className={staffInputClass()}
                value={form.param_legame_id || ''}
                onChange={(e) => setForm((p) => ({ ...p, param_legame_id: e.target.value }))}
              />
            </LabeledField>
          )}
          {form.tipo_trigger === 'SET' && (
            <LabeledField label="Set cronaca">
              <input
                className={staffInputClass()}
                value={form.param_set_collezione || ''}
                onChange={(e) => setForm((p) => ({ ...p, param_set_collezione: e.target.value }))}
              />
            </LabeledField>
          )}
          {form.tipo_trigger === 'CARTE' && (
            <LabeledField label="Codici carta" hint="Uno per riga.">
              <textarea
                className={staffInputClass('min-h-[80px] font-mono text-xs')}
                value={codiciText}
                onChange={(e) => setCodiciText(e.target.value)}
                placeholder={carteCatalogo.slice(0, 3).map((c) => c.codice).join('\n')}
              />
            </LabeledField>
          )}
          {form.tipo_trigger !== 'CARTE' && (
            <LabeledField label="Soglia minima">
              <input
                type="number"
                min={1}
                className={staffInputClass()}
                value={form.param_min_count ?? 2}
                onChange={(e) => setForm((p) => ({ ...p, param_min_count: Number(e.target.value) }))}
              />
            </LabeledField>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!form.attiva}
              onChange={(e) => setForm((p) => ({ ...p, attiva: e.target.checked }))}
            />
            Combo attiva
          </label>
          <StaffSection
            title="Modificatori statistiche personaggio"
            hint="Applicati al PG quando la combo è attiva (reliquiario)."
          >
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
          </StaffSection>
        </div>
      </StaffModal>
    </div>
  );
}
