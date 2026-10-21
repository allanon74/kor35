import React, { useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import SearchableSelect from './SearchableSelect';
import {
  staffPersonaggioAggiornaConsumabile,
  staffPersonaggioAggiungiConsumabile,
  staffPersonaggioCatalogoTessiture,
  staffPersonaggioRimuoviConsumabile,
} from '../../api';

const inputClass = 'w-full min-h-11 bg-gray-900 border border-gray-700 rounded px-2 py-2 text-sm text-white';

function etichettaTessitura(row) {
  const pezzi = [row.nome];
  if (row.livello) pezzi.push(`liv. ${row.livello}`);
  if (row.aura) pezzi.push(row.aura);
  return pezzi.join(' · ');
}

/**
 * Tab staff personaggio: consumabili del giocatore.
 * Si possono aggiungere a mano, generarne N da una tessitura, modificarli o toglierli.
 */
export default function StaffConsumabiliPersonaggioTab({ detail, onLogout, onUpdated, onError }) {
  const [catalogo, setCatalogo] = useState([]);
  const [catalogoLoading, setCatalogoLoading] = useState(false);
  const [motivo, setMotivo] = useState('Intervento staff consumabili');
  const [tessituraId, setTessituraId] = useState(null);
  const [quantita, setQuantita] = useState(1);
  const [utilizziTessitura, setUtilizziTessitura] = useState(1);
  const [scadenzaTessitura, setScadenzaTessitura] = useState('');
  const [manuale, setManuale] = useState({
    nome: '',
    descrizione: '',
    formula: '',
    utilizzi_rimanenti: 1,
    data_scadenza: '',
  });
  const [drafts, setDrafts] = useState({});
  const [busy, setBusy] = useState(false);

  const consumabili = detail?.consumabili || [];
  const firma = useMemo(
    () => consumabili.map((c) => `${c.id}:${c.utilizzi_rimanenti}:${c.data_scadenza}:${c.nome}`).join('|'),
    [consumabili],
  );

  useEffect(() => {
    const next = {};
    consumabili.forEach((c) => {
      next[c.id] = {
        utilizzi_rimanenti: c.utilizzi_rimanenti,
        data_scadenza: c.data_scadenza || '',
        nome: c.nome || '',
      };
    });
    setDrafts(next);
  }, [firma]);

  useEffect(() => {
    if (!detail?.id) return undefined;
    let cancel = false;
    setCatalogoLoading(true);
    staffPersonaggioCatalogoTessiture(detail.id, onLogout)
      .then((rows) => {
        if (!cancel) setCatalogo(Array.isArray(rows) ? rows : []);
      })
      .catch(() => {
        if (!cancel) setCatalogo([]);
      })
      .finally(() => {
        if (!cancel) setCatalogoLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [detail?.id, onLogout]);

  const opzioni = useMemo(
    () => catalogo.map((row) => ({ id: row.id, nome: etichettaTessitura(row) })),
    [catalogo],
  );

  const applica = async (azione) => {
    if (!detail?.id || busy) return;
    setBusy(true);
    try {
      const updated = await azione();
      onUpdated?.(updated, updated?.messaggio);
    } catch (err) {
      onError?.(err?.message || 'Operazione sui consumabili fallita');
    } finally {
      setBusy(false);
    }
  };

  const creaDaTessitura = () => {
    if (!tessituraId) {
      onError?.('Scegli una tessitura.');
      return;
    }
    const n = Math.max(1, Number(quantita) || 1);
    applica(() => staffPersonaggioAggiungiConsumabile(detail.id, {
      tessitura_id: tessituraId,
      quantita: n,
      utilizzi_rimanenti: Math.max(1, Number(utilizziTessitura) || 1),
      data_scadenza: scadenzaTessitura || undefined,
      motivo,
    }, onLogout));
  };

  const creaManuale = () => {
    if (!manuale.nome.trim()) {
      onError?.('Il nome del consumabile è obbligatorio.');
      return;
    }
    applica(async () => {
      const updated = await staffPersonaggioAggiungiConsumabile(detail.id, {
        nome: manuale.nome.trim(),
        descrizione: manuale.descrizione,
        formula: manuale.formula,
        quantita: 1,
        utilizzi_rimanenti: Math.max(1, Number(manuale.utilizzi_rimanenti) || 1),
        data_scadenza: manuale.data_scadenza || undefined,
        motivo,
      }, onLogout);
      setManuale({
        nome: '',
        descrizione: '',
        formula: '',
        utilizzi_rimanenti: 1,
        data_scadenza: '',
      });
      return updated;
    });
  };

  return (
    <div className="space-y-4" data-testid="staff-consumabili-personaggio">
      <p className="text-xs text-gray-400 break-words">
        Consumabili di questo personaggio. Da una tessitura puoi crearne il numero che ti serve:
        ogni copia è un consumabile distinto, con gli utilizzi indicati.
      </p>

      <label className="block text-xs text-gray-500">
        Motivo (diario del personaggio)
        <input
          className={`${inputClass} mt-1`}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
      </label>

      <section className="bg-gray-800/80 border border-teal-900/50 rounded-lg p-3 space-y-2">
        <h4 className="text-sm font-bold text-teal-200">Da tessitura</h4>
        {catalogoLoading ? (
          <p className="text-xs text-gray-500 flex items-center gap-2">
            <Loader2 className="animate-spin" size={14} /> Catalogo tessiture…
          </p>
        ) : (
          <SearchableSelect
            options={opzioni}
            value={tessituraId}
            onChange={setTessituraId}
            placeholder="Seleziona tessitura…"
          />
        )}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <label className="text-xs text-gray-500">
            Numero
            <input
              type="number"
              min={1}
              max={40}
              className={`${inputClass} mt-1`}
              value={quantita}
              onChange={(e) => setQuantita(e.target.value)}
              aria-label="Numero di consumabili"
            />
          </label>
          <label className="text-xs text-gray-500">
            Utilizzi ciascuno
            <input
              type="number"
              min={1}
              max={999}
              className={`${inputClass} mt-1`}
              value={utilizziTessitura}
              onChange={(e) => setUtilizziTessitura(e.target.value)}
              aria-label="Utilizzi di ciascun consumabile"
            />
          </label>
          <label className="text-xs text-gray-500">
            Scadenza
            <input
              type="date"
              className={`${inputClass} mt-1`}
              value={scadenzaTessitura}
              onChange={(e) => setScadenzaTessitura(e.target.value)}
              aria-label="Scadenza consumabili da tessitura"
            />
          </label>
        </div>
        <button
          type="button"
          data-testid="crea-consumabili-tessitura"
          disabled={busy || !tessituraId}
          onClick={creaDaTessitura}
          className="min-h-11 w-full sm:w-auto px-4 py-2 bg-teal-700 rounded font-bold text-sm disabled:opacity-40"
        >
          Crea consumabili
        </button>
      </section>

      <section className="bg-gray-800/80 border border-indigo-900/50 rounded-lg p-3 space-y-2">
        <h4 className="text-sm font-bold text-indigo-200">Aggiungi a mano</h4>
        <input
          className={inputClass}
          placeholder="Nome"
          aria-label="Nome consumabile"
          value={manuale.nome}
          onChange={(e) => setManuale((f) => ({ ...f, nome: e.target.value }))}
        />
        <textarea
          className={`${inputClass} min-h-20`}
          placeholder="Descrizione"
          aria-label="Descrizione consumabile"
          value={manuale.descrizione}
          onChange={(e) => setManuale((f) => ({ ...f, descrizione: e.target.value }))}
        />
        <textarea
          className={`${inputClass} min-h-16`}
          placeholder="Formula (opzionale)"
          aria-label="Formula consumabile"
          value={manuale.formula}
          onChange={(e) => setManuale((f) => ({ ...f, formula: e.target.value }))}
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <label className="text-xs text-gray-500">
            Utilizzi
            <input
              type="number"
              min={1}
              className={`${inputClass} mt-1`}
              value={manuale.utilizzi_rimanenti}
              onChange={(e) => setManuale((f) => ({ ...f, utilizzi_rimanenti: e.target.value }))}
              aria-label="Utilizzi consumabile manuale"
            />
          </label>
          <label className="text-xs text-gray-500">
            Scadenza
            <input
              type="date"
              className={`${inputClass} mt-1`}
              value={manuale.data_scadenza}
              onChange={(e) => setManuale((f) => ({ ...f, data_scadenza: e.target.value }))}
              aria-label="Scadenza consumabile manuale"
            />
          </label>
        </div>
        <button
          type="button"
          disabled={busy || !manuale.nome.trim()}
          onClick={creaManuale}
          className="min-h-11 w-full sm:w-auto px-4 py-2 bg-indigo-700 rounded font-bold text-sm disabled:opacity-40"
        >
          Aggiungi consumabile
        </button>
      </section>

      <section className="space-y-2">
        <h4 className="text-sm font-bold text-gray-300">
          In possesso ({consumabili.length})
        </h4>
        {consumabili.length === 0 ? (
          <p className="text-sm text-gray-500 italic">Nessun consumabile.</p>
        ) : (
          <ul className="space-y-2">
            {consumabili.map((c) => {
              const draft = drafts[c.id] || {
                utilizzi_rimanenti: c.utilizzi_rimanenti,
                data_scadenza: c.data_scadenza || '',
                nome: c.nome,
              };
              return (
                <li key={c.id} className="bg-gray-800 border border-gray-700 rounded-lg p-3 space-y-2">
                  <div className="min-w-0">
                    <p className="font-bold text-gray-100 break-words">{c.nome}</p>
                    <p className="text-xs text-gray-500 break-words">
                      {c.tessitura_nome ? `Da ${c.tessitura_nome}` : 'Aggiunto a mano'}
                      {c.scaduto ? ' · scaduto' : ''}
                    </p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <label className="text-xs text-gray-500">
                      Utilizzi
                      <input
                        type="number"
                        min={1}
                        className={`${inputClass} mt-1`}
                        aria-label={`Utilizzi ${c.nome}`}
                        value={draft.utilizzi_rimanenti}
                        onChange={(e) => setDrafts((prev) => ({
                          ...prev,
                          [c.id]: { ...draft, utilizzi_rimanenti: e.target.value },
                        }))}
                      />
                    </label>
                    <label className="text-xs text-gray-500">
                      Scadenza
                      <input
                        type="date"
                        className={`${inputClass} mt-1`}
                        aria-label={`Scadenza ${c.nome}`}
                        value={draft.data_scadenza || ''}
                        onChange={(e) => setDrafts((prev) => ({
                          ...prev,
                          [c.id]: { ...draft, data_scadenza: e.target.value },
                        }))}
                      />
                    </label>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy}
                      className="min-h-11 px-3 bg-teal-800 rounded text-xs font-bold disabled:opacity-40"
                      onClick={() => applica(() => staffPersonaggioAggiornaConsumabile(detail.id, {
                        consumabile_id: c.id,
                        utilizzi_rimanenti: Math.max(1, Number(draft.utilizzi_rimanenti) || 1),
                        data_scadenza: draft.data_scadenza || undefined,
                        motivo,
                      }, onLogout))}
                    >
                      Salva
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      className="min-h-11 px-3 bg-red-900/70 border border-red-800 rounded text-xs font-bold disabled:opacity-40"
                      onClick={() => {
                        if (!window.confirm(`Rimuovere «${c.nome}» da questo personaggio?`)) return;
                        applica(() => staffPersonaggioRimuoviConsumabile(detail.id, c.id, motivo, onLogout));
                      }}
                    >
                      Rimuovi
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
