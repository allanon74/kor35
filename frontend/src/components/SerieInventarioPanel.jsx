import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Package, Send, Layers } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import {
  getSerieInventario,
  trasferisciPezzoSerie,
  searchPersonaggi,
  resolveMediaUrl,
} from '../api';
import { emitToast } from '../utils/toastBus';

/**
 * Inventario serie del personaggio: pezzi da QR/pool, trasferibili ad altri PG.
 * Visibilità filtrata lato server in base agli eventi collegati alla serie.
 */
const SerieInventarioPanel = ({ onLogout }) => {
  const { selectedCharacterId } = useCharacter();
  const [loading, setLoading] = useState(false);
  const [serieGroups, setSerieGroups] = useState([]);
  const [openSerieId, setOpenSerieId] = useState(null);
  const [transferFor, setTransferFor] = useState(null);
  const [searchQ, setSearchQ] = useState('');
  const [searchHits, setSearchHits] = useState([]);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    if (!selectedCharacterId) {
      setSerieGroups([]);
      return;
    }
    setLoading(true);
    try {
      const data = await getSerieInventario(selectedCharacterId, onLogout);
      setSerieGroups(Array.isArray(data?.serie) ? data.serie : []);
    } catch (e) {
      emitToast({
        type: 'error',
        title: 'Inventario serie',
        message: e.message || 'Caricamento fallito.',
      });
    } finally {
      setLoading(false);
    }
  }, [selectedCharacterId, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!transferFor || !searchQ.trim() || searchQ.trim().length < 2) {
      setSearchHits([]);
      return undefined;
    }
    const t = setTimeout(async () => {
      try {
        const hits = await searchPersonaggi(searchQ.trim(), selectedCharacterId);
        setSearchHits(Array.isArray(hits) ? hits : hits?.results || []);
      } catch {
        setSearchHits([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [searchQ, transferFor, selectedCharacterId]);

  const handleTransfer = async (destId) => {
    if (!transferFor || !selectedCharacterId) return;
    setBusyId(transferFor.id);
    try {
      await trasferisciPezzoSerie(transferFor.id, selectedCharacterId, destId, onLogout);
      emitToast({
        type: 'success',
        title: 'Trasferimento',
        message: `«${transferFor.etichetta}» inviato.`,
      });
      setTransferFor(null);
      setSearchQ('');
      await load();
    } catch (e) {
      emitToast({
        type: 'error',
        title: 'Trasferimento fallito',
        message: e.message || 'Operazione non riuscita.',
      });
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-bold text-violet-300 mb-1 flex items-center gap-2 uppercase tracking-wider pl-1">
        <Layers size={16} /> Inventario serie
      </h3>
      <p className="text-xs text-gray-500 pl-1">
        Pezzi unici da QR/pool. Trasferimento diretto tra personaggi (alternativa a messaggi/transazioni:
        qui si aggiorna la proprietà del pezzo nell&apos;inventario serie).
      </p>
      {loading ? (
        <div className="flex justify-center py-6 text-gray-500">
          <Loader2 className="animate-spin" />
        </div>
      ) : serieGroups.length === 0 ? (
        <p className="text-sm text-gray-600 italic p-4 text-center border border-dashed border-gray-700 rounded-lg bg-gray-800/30">
          Nessun pezzo di serie attivo.
        </p>
      ) : (
        <ul className="space-y-2">
          {serieGroups.map((g) => {
            const open = openSerieId === g.serie_id;
            return (
              <li key={g.serie_id} className="rounded-xl border border-violet-900/40 bg-violet-950/20 overflow-hidden">
                <button
                  type="button"
                  className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left hover:bg-violet-950/40"
                  onClick={() => setOpenSerieId(open ? null : g.serie_id)}
                >
                  <span className="font-semibold text-violet-100">{g.serie_nome}</span>
                  <span className="text-xs text-gray-400">
                    {g.pezzi?.length || 0} pezz{(g.pezzi?.length || 0) === 1 ? 'o' : 'i'}
                    {g.totale ? ` / ${g.totale}` : ''}
                  </span>
                </button>
                {open && (
                  <ul className="border-t border-violet-900/30 divide-y divide-violet-900/20">
                    {(g.pezzi || []).map((p) => {
                      const img = resolveMediaUrl(p.immagine_url);
                      return (
                        <li key={p.id} className="flex gap-3 p-3 items-start">
                          <div className="w-16 h-16 shrink-0 rounded bg-black/40 border border-violet-800/40 flex items-center justify-center overflow-hidden">
                            {img ? (
                              <img src={img} alt={p.etichetta} className="w-full h-full object-contain" />
                            ) : (
                              <Package className="text-violet-500/70" size={22} />
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="font-bold text-violet-200">{p.etichetta}</div>
                            <div className="text-xs text-gray-400">
                              Pezzo {p.indice} di {p.totale}
                            </div>
                            <button
                              type="button"
                              disabled={busyId === p.id}
                              className="mt-2 inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded bg-violet-800 hover:bg-violet-700 text-violet-50 disabled:opacity-50"
                              onClick={() => {
                                setTransferFor(p);
                                setSearchQ('');
                                setSearchHits([]);
                              }}
                            >
                              <Send size={12} /> Trasferisci
                            </button>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {transferFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md bg-gray-900 border border-violet-800/50 rounded-xl p-4 space-y-3 shadow-xl">
            <h4 className="font-bold text-violet-200">Trasferisci «{transferFor.etichetta}»</h4>
            <p className="text-xs text-gray-400">
              Cerca il personaggio destinatario. Il pezzo sparisce dal tuo inventario serie e
              compare nel suo.
            </p>
            <input
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm"
              placeholder="Nome personaggio…"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              autoFocus
            />
            <ul className="max-h-48 overflow-y-auto space-y-1">
              {searchHits.map((hit) => (
                <li key={hit.id}>
                  <button
                    type="button"
                    disabled={busyId === transferFor.id || hit.id === selectedCharacterId}
                    className="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-violet-900/40 disabled:opacity-40"
                    onClick={() => handleTransfer(hit.id)}
                  >
                    {hit.nome || hit.label || `#${hit.id}`}
                  </button>
                </li>
              ))}
              {searchQ.trim().length >= 2 && searchHits.length === 0 && (
                <li className="text-xs text-gray-500 px-2">Nessun risultato</li>
              )}
            </ul>
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                className="px-3 py-1.5 text-sm rounded bg-gray-700"
                onClick={() => setTransferFor(null)}
              >
                Annulla
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default SerieInventarioPanel;
