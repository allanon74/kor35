import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, Pencil, Trash2, RefreshCw, Trophy, CalendarClock } from 'lucide-react';
import ConfirmDialog from './ConfirmDialog';
import {
  staffScommesseDeleteCalendario,
  staffScommesseDeleteProgrammazione,
  staffScommesseDeleteSport,
  staffScommesseDeleteSquadra,
  staffScommesseGeneraCalendarioPerEvento,
  staffScommesseGetCalendari,
  staffScommesseGetConfig,
  staffScommesseGetProgrammazioni,
  staffScommesseGetSport,
  staffScommesseGetSquadre,
  staffScommesseRigeneraIncontri,
  staffScommesseSaveCalendario,
  staffScommesseSaveConfig,
  staffScommesseSaveProgrammazione,
  staffScommesseSaveSport,
  staffScommesseSaveSquadra,
  staffScommesseSincronizzaProgrammazione,
  staffScommesseSincronizzaTutteProgrammazioni,
  scommesseGetClassificaSport,
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
  const [programmazioni, setProgrammazioni] = useState([]);
  const [formProgrammazione, setFormProgrammazione] = useState(null);
  const [classificaStaff, setClassificaStaff] = useState(null);
  const [classificaSportId, setClassificaSportId] = useState('');

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, c, cfg, prog] = await Promise.all([
        staffScommesseGetSport(onLogout),
        staffScommesseGetCalendari(onLogout),
        staffScommesseGetConfig(onLogout),
        staffScommesseGetProgrammazioni('', onLogout),
      ]);
      setSport(toList(s));
      setCalendari(toList(c));
      setConfig(cfg || null);
      setProgrammazioni(toList(prog));
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
      if (pendingDelete.type === 'programmazione') await staffScommesseDeleteProgrammazione(pendingDelete.id, onLogout);
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

  const handleSaveProgrammazione = async () => {
    if (!formProgrammazione?.sport) {
      setStatus({ type: 'warning', message: 'Seleziona uno sport.' });
      return;
    }
    setSaving(true);
    try {
      await staffScommesseSaveProgrammazione(
        {
          sport: formProgrammazione.sport,
          attiva: formProgrammazione.attiva !== false,
          auto_genera: formProgrammazione.auto_genera !== false,
          strategia_accoppiamento: formProgrammazione.strategia_accoppiamento || 'ROUND_ROBIN',
          ore_apertura_prima_evento: Number(formProgrammazione.ore_apertura_prima_evento) || 336,
          ore_chiusura_prima_evento: Number(formProgrammazione.ore_chiusura_prima_evento) || 2,
        },
        onLogout,
        formProgrammazione.id || null,
      );
      setFormProgrammazione(null);
      await loadAll();
      setStatus({ type: 'success', message: 'Programmazione salvata.' });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    } finally {
      setSaving(false);
    }
  };

  const handleSincronizzaProgrammazione = async (progId) => {
    try {
      const res = await staffScommesseSincronizzaProgrammazione(progId, onLogout, 1);
      await loadAll();
      setStatus({ type: 'success', message: `Creati ${res.creati || 0} calendari.` });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    }
  };

  const handleSincronizzaTutte = async () => {
    try {
      const res = await staffScommesseSincronizzaTutteProgrammazioni(onLogout, 1);
      await loadAll();
      const n = (res.creati || []).length;
      setStatus({ type: 'success', message: n ? `Creati ${n} calendari.` : 'Nessun nuovo calendario.' });
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    }
  };

  const loadClassificaStaff = async (sportId) => {
    if (!sportId) {
      setClassificaStaff(null);
      return;
    }
    try {
      const data = await scommesseGetClassificaSport(sportId, onLogout);
      setClassificaStaff(data);
    } catch (e) {
      setStatus({ type: 'error', message: e.message });
    }
  };

  useEffect(() => {
    if (subTab === 'classifiche' && classificaSportId) {
      loadClassificaStaff(classificaSportId);
    }
  }, [subTab, classificaSportId]);

  useEffect(() => {
    if (subTab === 'classifiche' && sport.length && !classificaSportId) {
      setClassificaSportId(String(sport[0].id));
    }
  }, [subTab, sport, classificaSportId]);

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
          {['sport', 'squadre', 'calendari', 'programmazione', 'classifiche', 'parametri'].map((t) => (
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
                        {cal.giornata_numero ? ` · Giornata ${cal.giornata_numero}` : ''}
                        {cal.evento_titolo ? ` · ${cal.evento_titolo}` : ''}
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
                      {cal.incontri.map((inc) => {
                        const pareggioOk = inc.pareggio_consentito ?? pareggioConsentito(cal.sport_tipo_risultato);
                        return (
                        <div key={inc.id} className="flex justify-between text-xs text-gray-300">
                          <span>{inc.squadra_casa_nome} vs {inc.squadra_trasferta_nome}</span>
                          <span className="text-gray-500">
                            {pareggioOk ? `${inc.quota_casa}/${inc.quota_pareggio}/${inc.quota_trasferta}` : `${inc.quota_casa}/${inc.quota_trasferta}`}
                            {inc.esito ? ` → ${inc.esito} (${inc.risultato_formattato || `${inc.gol_casa}-${inc.gol_trasferta}`})` : ''}
                          </span>
                        </div>
                      );})}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {subTab === 'programmazione' && (
          <div>
            <div className="mb-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setFormProgrammazione({
                  sport: sport[0]?.id || '',
                  attiva: true,
                  auto_genera: true,
                  strategia_accoppiamento: 'ROUND_ROBIN',
                  intervallo_giorni: 14,
                  sfasamento_giorni: programmazioni.length * 3,
                  giorni_apertura: 12,
                  ora_risoluzione: '18:00',
                  ore_apertura_prima_evento: 336,
                  ore_chiusura_prima_evento: 2,
                })}
                className="flex items-center gap-2 rounded bg-emerald-700 px-3 py-2 text-sm font-bold"
              >
                <Plus size={16} /> Nuova programmazione
              </button>
              <button
                type="button"
                onClick={handleSincronizzaTutte}
                className="flex items-center gap-2 rounded bg-cyan-800 px-3 py-2 text-sm font-bold"
              >
                <CalendarClock size={16} /> Sincronizza tutte
              </button>
            </div>
            <p className="mb-4 text-sm text-gray-400">
              Tra un evento LARP e l&apos;altro, ogni sport può pubblicare una giornata ogni 14 giorni (o intervallo
              personalizzato), sfalsata rispetto agli altri sport. Le giornate in evento si creano manualmente
              dal tab Calendari o con «Genera» sotto un evento. Il timer giornaliero (o «Sincronizza tutte») crea
              le giornate automatiche quando scade la cadenza.
            </p>
            <div className="space-y-3">
              {programmazioni.map((p) => (
                <div key={p.id} className="rounded border border-gray-700 bg-gray-800 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-bold">{p.sport_nome}</div>
                      <div className="mt-1 text-xs text-gray-400">
                        {p.attiva ? 'Attiva' : 'Spenta'} · {p.strategia_accoppiamento === 'ROUND_ROBIN' ? 'Girone' : 'Casuale'}
                        {' · '}Giornata {p.giornata_corrente}
                        {p.ultimo_evento_titolo ? ` · ultimo: ${p.ultimo_evento_titolo}` : ''}
                      </div>
                      <div className="text-xs text-gray-500">
                        Ogni {p.intervallo_giorni ?? 14} giorni
                        {p.sfasamento_giorni ? ` · sfasamento +${p.sfasamento_giorni}g` : ''}
                        {' · '}apertura {p.giorni_apertura ?? 12}g prima della risoluzione
                      </div>
                      {p.stato?.prossima_giornata_cadenza && (
                        <div className="mt-1 text-xs text-cyan-300/80">
                          Prossima auto: giornata {p.stato.prossima_giornata_cadenza.giornata_numero}
                          {' · '}apre {new Date(p.stato.prossima_giornata_cadenza.data_apertura_prevista).toLocaleString('it-IT')}
                          {p.stato.prossima_giornata_cadenza.pronta ? ' · pronta da creare' : ''}
                        </div>
                      )}
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button type="button" title="Sincronizza cadenza" onClick={() => handleSincronizzaProgrammazione(p.id)} className="text-cyan-400"><RefreshCw size={16} /></button>
                      <button type="button" onClick={() => setFormProgrammazione(p)} className="text-indigo-400"><Pencil size={16} /></button>
                      <button type="button" onClick={() => setPendingDelete({ type: 'programmazione', id: p.id })} className="text-red-400"><Trash2 size={16} /></button>
                    </div>
                  </div>
                  {p.stato?.prossimi_eventi?.length > 0 && (
                    <div className="mt-2 border-t border-gray-700 pt-2 text-xs text-gray-400">
                      Eventi LARP — generazione manuale:
                      <ul className="mt-1 space-y-1">
                        {p.stato.prossimi_eventi.slice(0, 3).map((ev) => (
                          <li key={ev.evento_id} className="flex flex-wrap items-center justify-between gap-2">
                            <span>{ev.evento_titolo} ({new Date(ev.data_inizio_evento).toLocaleDateString('it-IT')})</span>
                            <button
                              type="button"
                              className="text-cyan-300 hover:underline"
                              onClick={() => staffScommesseGeneraCalendarioPerEvento(p.id, ev.evento_id, onLogout).then(() => loadAll())}
                            >
                              Genera
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
              {!programmazioni.length && (
                <p className="text-sm text-gray-500">Nessuna programmazione configurata.</p>
              )}
            </div>
          </div>
        )}

        {subTab === 'classifiche' && (
          <div>
            <select
              value={classificaSportId}
              onChange={(e) => setClassificaSportId(e.target.value)}
              className="mb-4 rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm"
            >
              <option value="">Seleziona sport</option>
              {sport.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
            </select>
            {classificaStaff?.classifica?.length > 0 ? (
              <div className="overflow-x-auto rounded border border-gray-700">
                <table className="w-full min-w-[480px] text-left text-sm">
                  <thead className="bg-gray-800 text-xs uppercase text-gray-400">
                    <tr>
                      <th className="px-2 py-2">#</th>
                      <th className="px-2 py-2">Squadra</th>
                      <th className="px-2 py-2 text-center">Pt</th>
                      <th className="px-2 py-2 text-center">G</th>
                      <th className="px-2 py-2 text-center">V</th>
                      {classificaStaff.pareggio_consentito && <th className="px-2 py-2 text-center">P</th>}
                      <th className="px-2 py-2 text-center">S</th>
                      <th className="px-2 py-2 text-center">DR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {classificaStaff.classifica.map((r) => (
                      <tr key={r.squadra_id} className="border-t border-gray-700">
                        <td className="px-2 py-1">{r.posizione}</td>
                        <td className="px-2 py-1">{r.nome}</td>
                        <td className="px-2 py-1 text-center font-bold">{r.punti}</td>
                        <td className="px-2 py-1 text-center">{r.giocate}</td>
                        <td className="px-2 py-1 text-center">{r.vinte}</td>
                        {classificaStaff.pareggio_consentito && <td className="px-2 py-1 text-center">{r.pareggiate}</td>}
                        <td className="px-2 py-1 text-center">{r.perse}</td>
                        <td className="px-2 py-1 text-center">{r.differenza_reti}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-gray-500">Nessun risultato liquidato per questo sport.</p>
            )}
          </div>
        )}

        {subTab === 'parametri' && config && (
          <div className="max-w-lg space-y-4">
            <p className="text-sm text-gray-400">Parametri di equilibrio per la campagna corrente. I nuovi calendari ereditano il max CR senza codice.</p>
            {[
              { key: 'importo_max_senza_codice_default', label: 'Max CR senza codice (default calendari)', step: '0.01' },
              { key: 'scadenza_calendario_ore', label: 'Ore visibilità dopo risultati', step: '1' },
              { key: 'commissione_allibratore_pct', label: 'Commissione allibratore su vincita (0.08 = 8%)', step: '0.001' },
              { key: 'bonus_quota_allibratore_pct', label: 'Bonus quota con codice (0.10 = +10%)', step: '0.001' },
              { key: 'margine_book_default', label: 'Margine book standard', step: '0.001' },
              { key: 'margine_book_min', label: 'Margine book minimo (legacy, non usato)', step: '0.001' },
              { key: 'riduzione_margine_per_punto_all', label: 'Riduzione margine per punto ALL (legacy)', step: '0.001' },
              { key: 'variabilita_potenza_pct', label: 'Variabilità potenza squadre (±%)', step: '1' },
              { key: 'max_selezioni_combinata', label: 'Max eventi scommessa combinata', step: '1' },
              { key: 'potenza_delta_vittoria', label: 'Delta potenza base vincitrice (× fattore incontro)', step: '1' },
              { key: 'potenza_delta_sconfitta', label: 'Delta potenza base perdente (× fattore incontro)', step: '1' },
              { key: 'soglia_vincita_rilevante', label: 'Soglia vincita rilevante (CR)', step: '0.01' },
              { key: 'max_ritiro_vincita_calendario', label: 'Max ritiro contanti per calendario (CR)', step: '0.01' },
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

      {(formSport || formSquadra || formCalendario || formProgrammazione) && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-lg border border-gray-600 bg-gray-800 p-4 shadow-xl">
            <h3 className="mb-3 font-bold">
              {formSport && (formSport.id ? 'Modifica sport' : 'Nuovo sport')}
              {formSquadra && (formSquadra.id ? 'Modifica squadra' : 'Nuova squadra')}
              {formCalendario && (formCalendario.id ? 'Modifica calendario' : 'Nuovo calendario')}
              {formProgrammazione && (formProgrammazione.id ? 'Modifica programmazione' : 'Nuova programmazione')}
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

            {formProgrammazione && (
              <div className="space-y-3">
                <select
                  className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2"
                  value={formProgrammazione.sport}
                  onChange={(e) => setFormProgrammazione({ ...formProgrammazione, sport: e.target.value })}
                  disabled={!!formProgrammazione.id}
                >
                  <option value="">Seleziona sport</option>
                  {sport.map((s) => <option key={s.id} value={s.id}>{s.nome}</option>)}
                </select>
                <select
                  className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2"
                  value={formProgrammazione.strategia_accoppiamento || 'ROUND_ROBIN'}
                  onChange={(e) => setFormProgrammazione({ ...formProgrammazione, strategia_accoppiamento: e.target.value })}
                >
                  <option value="ROUND_ROBIN">Girone all&apos;italiana</option>
                  <option value="RANDOM">Accoppiamenti casuali</option>
                </select>
                <label className="block text-sm">
                  <span className="mb-1 block text-gray-300">Intervallo tra giornate (giorni)</span>
                  <input type="number" min={1} className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formProgrammazione.intervallo_giorni ?? 14} onChange={(e) => setFormProgrammazione({ ...formProgrammazione, intervallo_giorni: e.target.value })} />
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block text-gray-300">Sfasamento (giorni)</span>
                  <input type="number" min={0} className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formProgrammazione.sfasamento_giorni ?? 0} onChange={(e) => setFormProgrammazione({ ...formProgrammazione, sfasamento_giorni: e.target.value })} />
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block text-gray-300">Giorni apertura scommesse</span>
                  <input type="number" min={1} className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formProgrammazione.giorni_apertura ?? 12} onChange={(e) => setFormProgrammazione({ ...formProgrammazione, giorni_apertura: e.target.value })} />
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block text-gray-300">Ora risoluzione (cadenza)</span>
                  <input type="time" className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={(formProgrammazione.ora_risoluzione || '18:00').slice(0, 5)} onChange={(e) => setFormProgrammazione({ ...formProgrammazione, ora_risoluzione: e.target.value })} />
                </label>
                <label className="block text-sm">
                  <span className="mb-1 block text-gray-300">Data ancoraggio ciclo (opzionale)</span>
                  <input type="datetime-local" className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formProgrammazione.data_ancora_cadenza?.slice(0, 16) || ''} onChange={(e) => setFormProgrammazione({ ...formProgrammazione, data_ancora_cadenza: e.target.value || null })} />
                </label>
                <details className="text-sm text-gray-400">
                  <summary className="cursor-pointer text-gray-300">Finestre manuali in evento LARP</summary>
                  <div className="mt-2 space-y-2">
                    <label className="block">
                      <span className="mb-1 block text-gray-300">Ore apertura prima evento</span>
                      <input type="number" min={1} className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formProgrammazione.ore_apertura_prima_evento ?? 336} onChange={(e) => setFormProgrammazione({ ...formProgrammazione, ore_apertura_prima_evento: e.target.value })} />
                    </label>
                    <label className="block">
                      <span className="mb-1 block text-gray-300">Ore chiusura prima evento</span>
                      <input type="number" min={1} className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2" value={formProgrammazione.ore_chiusura_prima_evento ?? 2} onChange={(e) => setFormProgrammazione({ ...formProgrammazione, ore_chiusura_prima_evento: e.target.value })} />
                    </label>
                  </div>
                </details>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={formProgrammazione.attiva !== false} onChange={(e) => setFormProgrammazione({ ...formProgrammazione, attiva: e.target.checked })} /> Programmazione attiva</label>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={formProgrammazione.auto_genera !== false} onChange={(e) => setFormProgrammazione({ ...formProgrammazione, auto_genera: e.target.checked })} /> Auto-genera sulla cadenza</label>
              </div>
            )}

            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => { setFormSport(null); setFormSquadra(null); setFormCalendario(null); setFormProgrammazione(null); }} className="rounded px-3 py-2 text-sm text-gray-300">Annulla</button>
              <button
                type="button"
                disabled={saving}
                onClick={
                  formSport ? handleSaveSport
                    : formSquadra ? handleSaveSquadra
                      : formProgrammazione ? handleSaveProgrammazione
                        : handleSaveCalendario
                }
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
