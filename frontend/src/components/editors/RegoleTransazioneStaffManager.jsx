import React, { useCallback, useEffect, useState } from 'react';
import { ArrowLeftRight, Loader2, Save, Wallet } from 'lucide-react';
import { RegoleVisibilitaEditor } from './RequisitiAccessoEditor';
import {
  staffPatchRegolaTransazione,
  staffGetRegoleTransazioni,
  staffGetKorps,
  staffGetCarriere,
  staffGetCariche,
  staffGetAbilitaListAll,
  fetchEconomiaConfig,
  patchEconomiaConfig,
} from '../../api';

const CATALOGO_OBBLIGATORIO = new Set(['infusioni', 'tessiture', 'cerimoniali']);
const TECNICHE = new Set(['infusioni', 'tessiture', 'cerimoniali']);
const SOLO_DEPOSITO = new Set(['negozio']); // non scambi P2P

const FLAG_TECNICHE = [
  {
    key: 'solo_posseduti',
    label: 'Escludi catalogo Accademia (tab Nuove)',
    hint: 'Blocca scambi di beni ancora acquistabili dall\'Accademia ufficiale.',
  },
  {
    key: 'trasferimento_copia',
    label: 'Trasferimento a copia (tecniche)',
    hint: 'Il destinatario riceve una copia; il mittente conserva l\'originale.',
  },
  {
    key: 'rispetta_non_insegnabile',
    label: 'Rispetta flag non acquistabile',
    hint: 'Blocca tecniche marcate non acquistabile / escluse catalogo.',
  },
];

const RegoleTransazioneStaffManager = ({ onLogout }) => {
  const [regole, setRegole] = useState([]);
  const [draft, setDraft] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [savingEco, setSavingEco] = useState(false);
  const [message, setMessage] = useState('');
  const [lookup, setLookup] = useState({ abilita: [], korps: [], carriere: [], cariche: [] });
  const [frazione, setFrazione] = useState('1.00');
  const [fattore, setFattore] = useState('0.90');
  const [campagnaId, setCampagnaId] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetRegoleTransazioni(onLogout);
      const list = Array.isArray(data) ? data : data?.results || [];
      setRegole(list);
      const map = {};
      list.forEach((r) => { map[r.id] = { ...r }; });
      setDraft(map);
      const cid = list[0]?.campagna;
      if (cid) {
        setCampagnaId(String(cid));
        try {
          const eco = await fetchEconomiaConfig(cid, onLogout);
          const cfg = eco?.config || {};
          setFrazione(String(cfg.frazione_trasferimento_stipendio ?? '1.00'));
          setFattore(String(cfg.fattore_valore_deposito ?? '0.90'));
        } catch {
          /* modulo/config opzionale */
        }
      }
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
        vendibile_giocatori: SOLO_DEPOSITO.has(row.codice) ? false : !!row.vendibile_giocatori,
        requisiti_gruppo: row.requisiti_gruppo || { operator: 'AND', requisiti: [] },
        solo_posseduti: !!row.solo_posseduti,
        trasferimento_copia: !!row.trasferimento_copia,
        rispetta_non_insegnabile: !!row.rispetta_non_insegnabile,
        pagabile_con_deposito: !!row.pagabile_con_deposito,
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

  const saveEconomia = async () => {
    if (!campagnaId) return;
    setSavingEco(true);
    setMessage('');
    try {
      await patchEconomiaConfig(
        campagnaId,
        {
          frazione_trasferimento_stipendio: frazione,
          fattore_valore_deposito: fattore,
        },
        onLogout,
      );
      setMessage('Parametri economia (deposito) salvati.');
    } catch (e) {
      setMessage(e.message || 'Errore salvataggio economia');
    } finally {
      setSavingEco(false);
    }
  };

  const esempioPrezzo = (() => {
    const f = Number(fattore) || 0.9;
    if (f <= 0) return '—';
    return (100 / f).toFixed(2);
  })();

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
      <div className="p-4 border-b border-gray-800 space-y-3">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <ArrowLeftRight size={22} className="text-amber-400" />
            Regole scambi e spese
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Per categoria: scambi tra giocatori e cosa si può acquistare anche con i
            {' '}
            <span className="text-emerald-400">crediti di deposito</span>
            {' '}
            (investimento), se il modulo campagna è attivo.
          </p>
        </div>
        {message && <p className="text-sm text-amber-300">{message}</p>}

        {campagnaId && (
          <div className="bg-gray-850 border border-emerald-900/50 rounded-lg p-3 space-y-3">
            <div className="flex items-center gap-2 text-emerald-300 font-semibold text-sm">
              <Wallet size={16} />
              Parametri conto deposito
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Frazione stipendio trasferibile (deposito → corrente)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
                  value={frazione}
                  onChange={(e) => setFrazione(e.target.value)}
                />
                <p className="text-[11px] text-gray-500 mt-1">
                  Tetto = frazione × stipendio evento (es. 1.50 = fino al 150%).
                </p>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Fattore valore deposito (0.01–1.00)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max="1"
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
                  value={fattore}
                  onChange={(e) => setFattore(e.target.value)}
                />
                <p className="text-[11px] text-gray-500 mt-1">
                  Bene da 100 CR in corrente costa {esempioPrezzo} CR dal deposito.
                </p>
              </div>
            </div>
            <button
              type="button"
              disabled={savingEco}
              onClick={saveEconomia}
              className="flex items-center gap-2 px-3 py-1.5 bg-emerald-800 hover:bg-emerald-700 rounded text-sm font-bold disabled:opacity-50"
            >
              {savingEco ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Salva parametri deposito
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {regole.map((r) => {
          const row = draft[r.id] || r;
          const requisiti = row.requisiti_gruppo && typeof row.requisiti_gruppo === 'object'
            ? row.requisiti_gruppo
            : { operator: 'AND', requisiti: [] };
          const isNegozio = SOLO_DEPOSITO.has(row.codice);
          const isTecnica = TECNICHE.has(row.codice);
          const hideP2p = isNegozio;

          return (
            <div key={r.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="font-bold text-lg">{row.nome}</h3>
                  <span className="text-xs text-gray-500 font-mono">{row.codice}</span>
                  {isNegozio && (
                    <p className="text-xs text-gray-400 mt-1">
                      Solo acquisti presso mercanti / negozi NPC (non scambi tra giocatori).
                    </p>
                  )}
                </div>
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                {!hideP2p && (
                  <label className="flex flex-col gap-0.5 text-sm text-gray-300 bg-gray-900/40 rounded px-3 py-2 border border-gray-700/80">
                    <span className="flex items-center gap-2 font-medium">
                      <input
                        type="checkbox"
                        checked={!!row.vendibile_giocatori}
                        onChange={(e) => updateDraft(r.id, { vendibile_giocatori: e.target.checked })}
                      />
                      Scambiabile tra giocatori
                    </span>
                    <span className="text-xs text-gray-500 ml-6">
                      Se disattivo, la categoria non compare nelle proposte di scambio.
                    </span>
                  </label>
                )}
                <label className="flex flex-col gap-0.5 text-sm text-gray-300 bg-emerald-950/30 rounded px-3 py-2 border border-emerald-900/50">
                  <span className="flex items-center gap-2 font-medium text-emerald-200">
                    <input
                      type="checkbox"
                      checked={!!row.pagabile_con_deposito}
                      onChange={(e) => updateDraft(r.id, { pagabile_con_deposito: e.target.checked })}
                    />
                    Pagabile con crediti di deposito
                  </span>
                  <span className="text-xs text-gray-500 ml-6">
                    Acquisti NPC / listino anche con crediti di investimento (prezzo maggiorato dal fattore).
                  </span>
                </label>
              </div>

              {CATALOGO_OBBLIGATORIO.has(row.codice) && (
                <p className="text-xs text-amber-400/90 bg-amber-950/30 border border-amber-900/50 rounded px-2 py-1">
                  Protezione copyright: le tecniche nel catalogo Accademia (tab Nuove) non sono mai scambiabili tra giocatori.
                </p>
              )}

              {isTecnica && FLAG_TECNICHE.map(({ key, label, hint }) => {
                const catalogoLocked = key === 'solo_posseduti' && CATALOGO_OBBLIGATORIO.has(row.codice);
                const checked = catalogoLocked ? true : !!row[key];
                return (
                  <label key={key} className="flex flex-col gap-0.5 text-sm text-gray-300">
                    <span className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={catalogoLocked}
                        onChange={(e) => updateDraft(r.id, { [key]: e.target.checked })}
                      />
                      {label}
                      {catalogoLocked && (
                        <span className="text-[10px] uppercase text-amber-500 font-semibold">Sempre attivo</span>
                      )}
                    </span>
                    {hint && <span className="text-xs text-gray-500 ml-6">{hint}</span>}
                  </label>
                );
              })}

              {!hideP2p && (
                <div>
                  <p className="text-xs text-gray-500 mb-2 uppercase font-semibold">Requisiti mittente (vuoto = sempre)</p>
                  <RegoleVisibilitaEditor
                    value={requisiti}
                    onChange={(requisiti_gruppo) => updateDraft(r.id, { requisiti_gruppo })}
                    lookup={lookup}
                  />
                </div>
              )}

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
