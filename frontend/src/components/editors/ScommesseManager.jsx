import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, Pencil, Trash2, RefreshCw, Trophy } from 'lucide-react';
import ConfirmDialog from './ConfirmDialog';
import {
  staffScommesseDeleteCalendario,
  staffScommesseDeleteSport,
  staffScommesseDeleteSquadra,
  staffScommesseGetCalendari,
  staffScommesseGetConfig,
  staffScommesseGetSport,
  staffScommesseGetSquadre,
  staffScommesseRigeneraIncontri,
  staffScommesseSaveCalendario,
  staffScommesseSaveConfig,
  staffScommesseSaveSport,
  staffScommesseSaveSquadra,
} from '../../api';
import { TIPI_RISULTATO, labelTipoRisultato, pareggioConsentito } from '../../scommesse/risultatiSport';

const toList = (data) => (Array.isArray(data) ? data : data?.results || []);

const fmtDtLocal = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const ScommesseManager = ({ onBack, onLogout }) => {
  const [subTab, setSubTab] = useState('sport');
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [sport, setSport] = useState([]);
  const [squadre, setSquadre] = useState([]);
  const [calendari, setCalendari] = useState([]);
  const [filterSportId, setFilterSportId] = useState('');
  const [pendingDelete, setPendingDelete] = useState(null);
  const [formSport, setFormSport] = useState(null);
  const [formSquadra, setFormSquadra] = useState(null);
  const [formCalendario, setFormCalendario] = useState(null);
  const [config, setConfig] = useState(null);
  const [saving, setSaving] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, c, cfg] = await Promise.all([
        staffScommesseGetSport(onLogout),
        staffScommesseGetCalendari(onLogout),
        staffScommesseGetConfig(onLogout),
      ]);
      setSport(toList(s));
      setCalendari(toList(c));
      setConfig(cfg || null);
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  const loadSquadre = useCallback(async (sportId) => {
    try {
      const data = await staffScommesseGetSquadre(sportId || '', onLogout);
      setSquadre(toList(data));
    } catch {
      setSquadre([]);
    }
  }, [onLogout]);

  useEffect(() => { loadAll(); }, [loadAll]);
  useEffect(() => { loadSquadre(filterSportId); }, [filterSportId, loadSquadre]);

  const handleSaveSport = async () => {
    if (!formSport?.nome?.trim()) {
      setStatus({ type: 'warning', message: 'Nome sport obbligatorio.' });
      return;
    }
    setSaving(true);
    try {
      await staffScommesseSaveSport(
        {
          nome: formSport.nome,
          descrizione: formSport.descrizione || '',
          attivo: formSport.attivo !== false,
          tipo_risultato: formSport.tipo_risultato || 'calcio',
        },
        onLogout,
        formSport.id || null,
      );
      setFormSport(null);
      await loadAll();
      setStatus({ type: 'success', message: 'Sport salvato.' });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSquadra = async () => {
    if (!formSquadra?.nome?.trim() || !formSquadra?.sport) {
      setStatus({ type: 'warning', message: 'Sport e nome squadra obbligatori.' });
      return;
    }
    setSaving(true);
    try {
      await staffScommesseSaveSquadra(
        {
          sport: formSquadra.sport,
          nome: formSquadra.nome,
          potenza: Number(formSquadra.potenza) || 50,
          attiva: formSquadra.attiva !== false,
        },
        onLogout,
        formSquadra.id || null,
      );
      setFormSquadra(null);
      await loadSquadre(filterSportId);
      await loadAll();
      setStatus({ type: 'success', message: 'Squadra salvata.' });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveCalendario = async () => {
    if (!formCalendario?.sport || !formCalendario?.data_risoluzione) {
      setStatus({ type: 'warning', message: 'Sport e data risoluzione obbligatori.' });
      return;
    }
    setSaving(true);
    try {
      const payload = {
        sport: formCalendario.sport,
        titolo: formCalendario.titolo || '',
        data_apertura: new Date(formCalendario.data_apertura || Date.now()).toISOString(),
        data_risoluzione: new Date(formCalendario.data_risoluzione).toISOString(),
        importo_max_senza_codice: formCalendario.importo_max_senza_codice || '10.00',
        attivo: formCalendario.attivo !== false,
      };
      await staffScommesseSaveCalendario(payload, onLogout, formCalendario.id || null);
      setFormCalendario(null);
      await loadAll();
      setStatus({ type: 'success', message: 'Calendario salvato con incontri generati.' });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    try {
      if (pendingDelete.type === 'sport') await staffScommesseDeleteSport(pendingDelete.id, onLogout);
      if (pendingDelete.type === 'squadra') await staffScommesseDeleteSquadra(pendingDelete.id, onLogout);
      if (pendingDelete.type === 'calendario') await staffScommesseDeleteCalendario(pendingDelete.id, onLogout);
      setPendingDelete(null);
      await loadAll();
      await loadSquadre(filterSportId);
      setStatus({ type: 'success', message: 'Eliminato.' });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    }
  };

  const handleSaveConfig = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const saved = await staffScommesseSaveConfig(config, onLogout);
      setConfig(saved);
      setStatus({ type: 'success', message: 'Parametri salvati.' });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    } finally {
      setSaving(false);
    }
  };

  const handleRigenera = async (calId) => {
    try {
      await staffScommesseRigeneraIncontri(calId, onLogout);
      await loadAll();
      setStatus({ type: 'success', message: 'Incontri rigenerati.' });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-gray-400">
        <Loader2 className="animate-spin" size={32} />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-gray-900 text-gray-100">
      <div className="border-b border-gray-700 bg-gray-800 px-4 py-3">
        <div className="flex items-center gap-3">
          {onBack && (
            <button type="button" onClick={onBack} className="text-sm text-indigo-400 hover:underline">← Indietro</button>
          )}
          <Trophy className="text-amber-400" size={22} />
          <h1 className="text-lg font-bold">Gestione scommesse</h1>
        </div>
        <div className="mt-3 flex gap-2">
          {['sport', 'squadre', 'calendari', 'parametri'].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setSubTab(t)}
              className={`rounded px-3 py-1 text-xs font-bold uppercase ${subTab === t ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300'}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {status.message && (
        <div className={`mx-4 mt-3 rounded px-3 py-2 text-sm ${status.type === 'error' ? 'bg-red-900/50 text-red-200' : status.type === 'success' ? 'bg-emerald-900/50 text-emerald-200' : 'bg-amber-900/50 text-amber-200'}`}>
          {status.message}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4">
        {subTab === 'sport' && (
          <div>
            <button type="button" onClick={() => setFormSport({ nome: '', descrizione: '', attivo: true, tipo_risultato: 'calcio' })} className="mb-4 flex items-center gap-2 rounded bg-emerald-700 px-3 py-2 text-sm font-bold">
              <Plus size={16} /> Nuovo sport
            </button>
            <div className="space-y-2">
              {sport.map((s) => (
                <div key={s.id} className="flex items-center justify-between rounded border border-gray-700 bg-gray-800 px-3 py-2">
                  <div>
                    <div className="font-bold">{s.nome}</div>
                    <div className="text-xs text-gray-400">
                      {labelTipoRisultato(s.tipo_risultato)}
                      {pareggioConsentito(s.tipo_risultato) ? '' : ' · no X'}
                      {' · '}{s.num_squadre} squadre · {s.attivo ? 'attivo' : 'disattivo'}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => setFormSport(s)} className="text-indigo-400"><Pencil size={16} /></button>
                    <button type="button" onClick={() => setPendingDelete({ type: 'sport', id: s.id })} className="text-red-400"><Trash2 size={16} /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {subTab === 'squadre' && (
          <div>
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <select value={filterSportId} onChange={(e) => setFilterSportId(e.target.value)} className="rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm">
                <option value="">Tutti gli sport</option>
                {sport.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
              </select>
              <button
                type="button"
                onClick={() => setFormSquadra({ sport: filterSportId || sport[0]?.id || '', nome: '', potenza: 50, attiva: true })}
                className="flex items-center gap-2 rounded bg-emerald-700 px-3 py-2 text-sm font-bold"
              >
                <Plus size={16} /> Nuova squadra
              </button>
            </div>
            <div className="space-y-2">
              {squadre.map((sq) => (
                <div key={sq.id} className="flex items-center justify-between rounded border border-gray-700 bg-gray-800 px-3 py-2">
                  <div>
                    <div className="font-bold">{sq.nome}</div>
                    <div className="text-xs text-gray-400">{sq.sport_nome} · potenza {sq.potenza}</div>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => setFormSquadra(sq)} className="text-indigo-400"><Pencil size={16} /></button>
                    <button type="button" onClick={() => setPendingDelete({ type: 'squadra', id: sq.id })} className="text-red-400"><Trash2 size={16} /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {subTab === 'calendari' && (
          <div>
            <button
              type="button"
              onClick={() => setFormCalendario({
                sport: sport[0]?.id || '',
                titolo: '',
                data_apertura: fmtDtLocal(new Date().toISOString()),
                data_risoluzione: '',
                importo_max_senza_codice: config?.importo_max_senza_codice_default || '15.00',
                attivo: true,
              })}
              className="mb-4 flex items-center gap-2 rounded bg-emerald-700 px-3 py-2 text-sm font-bold"
            >
              <Plus size={16} /> Genera calendario
            </button>
            <div className="space-y-3">
              {calendari.map((cal) => (
                <div key={cal.id} className="rounded border border-gray-700 bg-gray-800 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-bold">{cal.titolo || cal.sport_nome}</div>
                      <div className="mt-1 text-xs text-gray-400">
                        {cal.sport_tipo_risultato_label || labelTipoRisultato(cal.sport_tipo_risultato)}
                        {' · '}{cal.num_incontri} incontri · risoluzione {new Date(cal.data_risoluzione).toLocaleString('it-IT')}
                      </div>
                      <div className="text-xs text-gray-500">
                        Max senza codice: {cal.importo_max_senza_codice} CR · {cal.scommesse_aperte ? 'scommesse aperte' : cal.risultati_visibili ? 'risultati pubblicati' : 'in attesa'}
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button type="button" title="Rigenera incontri" onClick={() => handleRigenera(cal.id)} className="text-cyan-400"><RefreshCw size={16} /></button>
                      <button type="button" onClick={() => setPendingDelete({ type: 'calendario', id: cal.id })} className="text-red-400"><Trash2 size={16} /></button>
                    </div>
                  </div>
                  {cal.incontri?.length > 0 && (
                    <div className="mt-2 space-y-1 border-t border-gray-700 pt-2">
                      {cal.incontri.map((inc) => (
                        <div key={inc.id} className="flex justify-between text-xs text-gray-300">
                          <span>{inc.squadra_casa_nome} vs {inc.squadra_trasferta_nome}</span>
                          <span className="text-gray-500">
                            {inc.quota_casa}/{inc.pareggio_consentito !== false ? `${inc.quota_pareggio}/` : ''}{inc.quota_trasferta}
                            {inc.esito ? ` → ${inc.esito} (${inc.risultato_formattato || `${inc.gol_casa}-${inc.gol_trasferta}`})` : ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {subTab === 'parametri' && config && (
          <div className="max-w-lg space-y-4">
            <p className="text-sm text-gray-400">Parametri di equilibrio per la campagna corrente. I nuovi calendari ereditano il max CR senza codice.</p>
            {[
              { key: 'importo_max_senza_codice_default', label: 'Max CR senza codice (default calendari)', step: '0.01' },
              { key: 'scadenza_calendario_ore', label: 'Ore visibilità dopo risultati', step: '1' },
              { key: 'commissione_allibratore_pct', label: 'Commissione allibratore (0.08 = 8%)', step: '0.001' },
              { key: 'margine_book_default', label: 'Margine book standard', step: '0.001' },
              { key: 'margine_book_min', label: 'Margine book minimo (codice ALL)', step: '0.001' },
              { key: 'riduzione_margine_per_punto_all', label: 'Riduzione margine per punto ALL', step: '0.001' },
              { key: 'variabilita_potenza_pct', label: 'Variabilità potenza squadre (±%)', step: '1' },
              { key: 'max_selezioni_combinata', label: 'Max eventi scommessa combinata', step: '1' },
              { key: 'potenza_delta_vittoria', label: 'Delta potenza base vincitrice (× fattore incontro)', step: '1' },
              { key: 'potenza_delta_sconfitta', label: 'Delta potenza base perdente (× fattore incontro)', step: '1' },
            ].map(({ key, label, step }) => (
              <label key={key} className="block text-sm">
                <span className="mb-1 block text-gray-300">{label}</span>
                <input
                  type="number"
                  step={step}
                  className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2"
                  value={config[key] ?? ''}
                  onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
                />
              </label>
            ))}
            <button
              type="button"
              disabled={saving}
              onClick={handleSaveConfig}
              className="rounded bg-emerald-600 px-4 py-2 text-sm font-bold disabled:opacity-50"
            >
              {saving ? 'Salvataggio…' : 'Salva parametri'}
            </button>
          </div>
        )}
      </div>

      {(formSport || formSquadra || formCalendario) && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-lg border border-gray-600 bg-gray-800 p-4 shadow-xl">
            <h3 className="mb-3 font-bold">
              {formSport && (formSport.id ? 'Modifica sport' : 'Nuovo sport')}
              {formSquadra && (formSquadra.id ? 'Modifica squadra' : 'Nuova squadra')}
              {formCalendario && (formCalendario.id ? 'Modifica calendario' : 'Nuovo calendario')}
            </h3>

            {formSport && (
              <div className="space-y-3">
                <input className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" placeholder="Nome" value={formSport.nome} onChange={(e) => setFormSport({ ...formSport, nome: e.target.value })} />
                <textarea className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" placeholder="Descrizione" rows={2} value={formSport.descrizione || ''} onChange={(e) => setFormSport({ ...formSport, descrizione: e.target.value })} />
                <label className="block text-sm">
                  <span className="mb-1 block text-gray-300">Tipo risultato</span>
                  <select
                    className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2"
                    value={formSport.tipo_risultato || 'calcio'}
                    onChange={(e) => setFormSport({ ...formSport, tipo_risultato: e.target.value })}
                  >
                    {TIPI_RISULTATO.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.label}{t.pareggio ? '' : ' (senza pareggio)'}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={formSport.attivo !== false} onChange={(e) => setFormSport({ ...formSport, attivo: e.target.checked })} /> Attivo</label>
              </div>
            )}

            {formSquadra && (
              <div className="space-y-3">
                <select className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formSquadra.sport} onChange={(e) => setFormSquadra({ ...formSquadra, sport: e.target.value })}>
                  <option value="">Seleziona sport</option>
                  {sport.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
                </select>
                <input className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" placeholder="Nome squadra" value={formSquadra.nome} onChange={(e) => setFormSquadra({ ...formSquadra, nome: e.target.value })} />
                <input type="number" min={1} max={999} className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" placeholder="Potenza" value={formSquadra.potenza} onChange={(e) => setFormSquadra({ ...formSquadra, potenza: e.target.value })} />
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={formSquadra.attiva !== false} onChange={(e) => setFormSquadra({ ...formSquadra, attiva: e.target.checked })} /> Attiva</label>
              </div>
            )}

            {formCalendario && (
              <div className="space-y-3">
                <select className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formCalendario.sport} onChange={(e) => setFormCalendario({ ...formCalendario, sport: e.target.value })}>
                  <option value="">Seleziona sport</option>
                  {sport.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
                </select>
                <input className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" placeholder="Titolo (opzionale)" value={formCalendario.titolo || ''} onChange={(e) => setFormCalendario({ ...formCalendario, titolo: e.target.value })} />
                <label className="text-xs text-gray-400">Apertura scommesse</label>
                <input type="datetime-local" className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formCalendario.data_apertura?.slice(0, 16) || ''} onChange={(e) => setFormCalendario({ ...formCalendario, data_apertura: e.target.value })} />
                <label className="text-xs text-gray-400">Pubblicazione risultati</label>
                <input type="datetime-local" className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formCalendario.data_risoluzione?.slice(0, 16) || ''} onChange={(e) => setFormCalendario({ ...formCalendario, data_risoluzione: e.target.value })} />
                <input type="number" step="0.01" className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" placeholder="Max CR senza codice" value={formCalendario.importo_max_senza_codice} onChange={(e) => setFormCalendario({ ...formCalendario, importo_max_senza_codice: e.target.value })} />
              </div>
            )}

            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => { setFormSport(null); setFormSquadra(null); setFormCalendario(null); }} className="rounded px-3 py-2 text-sm text-gray-300">Annulla</button>
              <button
                type="button"
                disabled={saving}
                onClick={formSport ? handleSaveSport : formSquadra ? handleSaveSquadra : handleSaveCalendario}
                className="rounded bg-emerald-600 px-4 py-2 text-sm font-bold disabled:opacity-50"
              >
                {saving ? 'Salvataggio…' : 'Salva'}
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        title="Conferma eliminazione"
        message="Eliminare questo elemento? L'operazione non è reversibile."
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
};

export default ScommesseManager;
