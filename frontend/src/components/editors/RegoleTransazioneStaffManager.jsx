import React, { useCallback, useEffect, useState } from 'react';
import { ArrowLeftRight, Loader2, Save } from 'lucide-react';
import { RegoleVisibilitaEditor } from './RequisitiAccessoEditor';
import {
  staffGetRegoleTransazioni,
  staffPatchRegolaTransazione,
  staffGetKorps,
  staffGetCarriere,
  staffGetCariche,
  staffGetAbilitaListAll,
} from '../../api';

const FLAG_FIELDS = [
  { key: 'solo_posseduti', label: 'Solo beni già posseduti' },
  { key: 'trasferimento_copia', label: 'Trasferimento a copia (tecniche)' },
  { key: 'rispetta_non_insegnabile', label: 'Rispetta flag non insegnabile/acquistabile' },
];

const RegoleTransazioneStaffManager = ({ onLogout }) => {
  const [regole, setRegole] = useState([]);
  const [draft, setDraft] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [message, setMessage] = useState('');
  const [lookup, setLookup] = useState({ abilita: [], korps: [], carriere: [], cariche: [] });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetRegoleTransazioni(onLogout);
      const list = Array.isArray(data) ? data : data?.results || [];
      setRegole(list);
      const map = {};
      list.forEach((r) => { map[r.id] = { ...r }; });
      setDraft(map);
    } catch (e) {
      setMessage(e.message || 'Errore caricamento regole');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
    Promise.all([
      staffGetKorps(onLogout),
      staffGetCarriere(onLogout),
      staffGetCariche(onLogout),
      staffGetAbilitaListAll(onLogout),
    ]).then(([korps, carriere, cariche, abilita]) => {
      setLookup({
        korps: Array.isArray(korps) ? korps : korps?.results || [],
        carriere: Array.isArray(carriere) ? carriere : carriere?.results || [],
        cariche: Array.isArray(cariche) ? cariche : cariche?.results || [],
        abilita: Array.isArray(abilita) ? abilita : abilita?.results || [],
      });
    });
  }, [load, onLogout]);

  const updateDraft = (id, patch) => {
    setDraft((d) => ({ ...d, [id]: { ...d[id], ...patch } }));
  };

  const saveRegola = async (id) => {
    const row = draft[id];
    if (!row) return;
    setSavingId(id);
    setMessage('');
    try {
      const payload = {
        vendibile_giocatori: !!row.vendibile_giocatori,
        requisiti_gruppo: row.requisiti_gruppo || { operator: 'AND', requisiti: [] },
        solo_posseduti: !!row.solo_posseduti,
        trasferimento_copia: !!row.trasferimento_copia,
        rispetta_non_insegnabile: !!row.rispetta_non_insegnabile,
      };
      const updated = await staffPatchRegolaTransazione(id, payload, onLogout);
      setRegole((list) => list.map((r) => (r.id === id ? updated : r)));
      setDraft((d) => ({ ...d, [id]: updated }));
      setMessage(`Regola «${updated.nome}» salvata.`);
    } catch (e) {
      setMessage(e.message || 'Errore salvataggio');
    } finally {
      setSavingId(null);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        <Loader2 className="animate-spin mr-2" size={20} />
        Caricamento regole transazioni…
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white overflow-hidden">
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <ArrowLeftRight size={22} className="text-amber-400" />
          Regole scambi tra giocatori
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Per categoria di bene: abilita o blocca gli scambi e imposta i requisiti del mittente.
        </p>
        {message && <p className="text-sm text-amber-300 mt-2">{message}</p>}
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {regole.map((r) => {
          const row = draft[r.id] || r;
          const requisiti = row.requisiti_gruppo && typeof row.requisiti_gruppo === 'object'
            ? row.requisiti_gruppo
            : { operator: 'AND', requisiti: [] };
          return (
            <div key={r.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="font-bold text-lg">{row.nome}</h3>
                  <span className="text-xs text-gray-500 font-mono">{row.codice}</span>
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={!!row.vendibile_giocatori}
                    onChange={(e) => updateDraft(r.id, { vendibile_giocatori: e.target.checked })}
                  />
                  Scambiabile tra giocatori
                </label>
              </div>
              {FLAG_FIELDS.map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={!!row[key]}
                    onChange={(e) => updateDraft(r.id, { [key]: e.target.checked })}
                  />
                  {label}
                </label>
              ))}
              <div>
                <p className="text-xs text-gray-500 mb-2 uppercase font-semibold">Requisiti mittente (vuoto = sempre)</p>
                <RegoleVisibilitaEditor
                  value={requisiti}
                  onChange={(requisiti_gruppo) => updateDraft(r.id, { requisiti_gruppo })}
                  lookup={lookup}
                />
              </div>
              <button
                type="button"
                disabled={savingId === r.id}
                onClick={() => saveRegola(r.id)}
                className="flex items-center gap-2 px-4 py-2 bg-amber-700 rounded font-bold text-sm disabled:opacity-50"
              >
                {savingId === r.id ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                Salva categoria
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RegoleTransazioneStaffManager;
