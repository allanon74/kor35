import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, Package, Send, Layers, Trash2, Search, FileText, BookOpen, X } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import {
  getSerieInventario,
  trasferisciPezzoSerie,
  eliminaPezzoSerie,
  trasferisciDocumentoArchivio,
  eliminaDocumentoArchivio,
  searchPersonaggi,
  resolveMediaUrl,
} from '../api';
import { emitToast } from '../utils/toastBus';
import RichHtml from './RichHtml';

/**
 * Scheda «Serie e testi»: pezzi serie + manifesti/testi salvati.
 * Filtro ricerca, lettura, trasferimento ed eliminazione.
 */
const SerieInventarioPanel = ({ onLogout }) => {
  const { selectedCharacterId } = useCharacter();
  const [loading, setLoading] = useState(false);
  const [serieGroups, setSerieGroups] = useState([]);
  const [documenti, setDocumenti] = useState([]);
  const [filterQ, setFilterQ] = useState('');
  const [openSerieId, setOpenSerieId] = useState(null);
  const [reading, setReading] = useState(null);
  const [transferFor, setTransferFor] = useState(null);
  const [searchQ, setSearchQ] = useState('');
  const [searchHits, setSearchHits] = useState([]);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    if (!selectedCharacterId) {
      setSerieGroups([]);
      setDocumenti([]);
      return;
    }
    setLoading(true);
    try {
      const data = await getSerieInventario(selectedCharacterId, onLogout);
      setSerieGroups(Array.isArray(data?.serie) ? data.serie : []);
      setDocumenti(Array.isArray(data?.documenti) ? data.documenti : []);
    } catch (e) {
      emitToast({
        type: 'error',
        title: 'Serie e testi',
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

  const qNorm = filterQ.trim().toLowerCase();

  const filteredSerie = useMemo(() => {
    if (!qNorm) return serieGroups;
    return serieGroups
      .map((g) => {
        const nomeOk = (g.serie_nome || '').toLowerCase().includes(qNorm);
        const pezzi = (g.pezzi || []).filter(
          (p) =>
            nomeOk
            || (p.etichetta || '').toLowerCase().includes(qNorm)
            || String(p.indice || '').includes(qNorm),
        );
        if (!nomeOk && !pezzi.length) return null;
        return { ...g, pezzi: nomeOk ? g.pezzi : pezzi };
      })
      .filter(Boolean);
  }, [serieGroups, qNorm]);

  const filteredDocs = useMemo(() => {
    if (!qNorm) return documenti;
    return documenti.filter(
      (d) =>
        (d.titolo || '').toLowerCase().includes(qNorm)
        || (d.tipo || '').toLowerCase().includes(qNorm)
        || (d.testo || '').toLowerCase().includes(qNorm),
    );
  }, [documenti, qNorm]);

  const handleTransfer = async (destId) => {
    if (!transferFor || !selectedCharacterId) return;
    setBusyId(transferFor.id);
    try {
      if (transferFor.kind === 'documento') {
        await trasferisciDocumentoArchivio(
          transferFor.id,
          selectedCharacterId,
          destId,
          onLogout,
        );
      } else {
        await trasferisciPezzoSerie(transferFor.id, selectedCharacterId, destId, onLogout);
      }
      emitToast({
        type: 'success',
        title: 'Trasferimento',
        message: `«${transferFor.etichetta || transferFor.titolo}» inviato.`,
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

  const handleDelete = async (item) => {
    if (!selectedCharacterId || !item?.id) return;
    const label = item.etichetta || item.titolo || 'elemento';
    if (!window.confirm(`Eliminare «${label}» dal tuo archivio?`)) return;
    setBusyId(item.id);
    try {
      if (item.kind === 'documento') {
        await eliminaDocumentoArchivio(item.id, selectedCharacterId, onLogout);
      } else {
        await eliminaPezzoSerie(item.id, selectedCharacterId, onLogout);
      }
      emitToast({ type: 'success', title: 'Eliminato', message: `«${label}» rimosso.` });
      if (reading?.id === item.id) setReading(null);
      await load();
    } catch (e) {
      emitToast({
        type: 'error',
        title: 'Eliminazione fallita',
        message: e.message || 'Operazione non riuscita.',
      });
    } finally {
      setBusyId(null);
    }
  };

  const openPezzo = (p, serieNome) => {
    setReading({
      kind: 'serie',
      id: p.id,
      etichetta: p.etichetta,
      titolo: p.etichetta,
      serie_nome: serieNome,
      indice: p.indice,
      totale: p.totale,
      immagine_url: p.immagine_url,
    });
  };

  const openDocumento = (d) => {
    setReading({ ...d, kind: 'documento' });
  };

  const empty = !loading && !filteredSerie.length && !filteredDocs.length;

  return (
    <section className="space-y-3">
      <p className="text-xs text-gray-500 pl-1">
        Pezzi di serie, manifesti e testi salvati. Aprili in lettura (senza minigiochi),
        trasferiscili o eliminali.
      </p>
      <div className="relative">
        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          className="w-full bg-gray-800 border border-gray-600 rounded-lg pl-8 pr-3 py-2 text-sm"
          placeholder="Cerca serie, pezzi, titoli…"
          value={filterQ}
          onChange={(e) => setFilterQ(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-6 text-gray-500">
          <Loader2 className="animate-spin" />
        </div>
      ) : empty ? (
        <p className="text-sm text-gray-600 italic p-4 text-center border border-dashed border-gray-700 rounded-lg bg-gray-800/30">
          Nessun elemento in Serie e testi.
        </p>
      ) : (
        <div className="space-y-4">
          {filteredDocs.length > 0 && (
            <div>
              <h4 className="text-xs uppercase tracking-wider text-amber-400/90 font-bold mb-2 flex items-center gap-1.5">
                <FileText size={14} /> Manifesti e testi
              </h4>
              <ul className="space-y-2">
                {filteredDocs.map((d) => (
                  <li
                    key={d.id}
                    className="rounded-xl border border-amber-900/40 bg-amber-950/20 p-3 flex gap-3 items-start"
                  >
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-left"
                      onClick={() => openDocumento(d)}
                    >
                      <div className="font-bold text-amber-100 flex items-center gap-2">
                        {d.tipo === 'manifesto' ? <BookOpen size={14} /> : <FileText size={14} />}
                        {d.titolo}
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5 capitalize">{d.tipo}</div>
                    </button>
                    <div className="flex flex-col gap-1 shrink-0">
                      <button
                        type="button"
                        disabled={busyId === d.id}
                        className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-violet-800 hover:bg-violet-700 disabled:opacity-50"
                        onClick={() => {
                          setTransferFor({ ...d, etichetta: d.titolo, kind: 'documento' });
                          setSearchQ('');
                          setSearchHits([]);
                        }}
                      >
                        <Send size={12} /> Trasferisci
                      </button>
                      <button
                        type="button"
                        disabled={busyId === d.id}
                        className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-900/70 hover:bg-red-800 disabled:opacity-50"
                        onClick={() => handleDelete({ ...d, kind: 'documento' })}
                      >
                        <Trash2 size={12} /> Elimina
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {filteredSerie.length > 0 && (
            <div>
              <h4 className="text-xs uppercase tracking-wider text-violet-400/90 font-bold mb-2 flex items-center gap-1.5">
                <Layers size={14} /> Serie
              </h4>
              <ul className="space-y-2">
                {filteredSerie.map((g) => {
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
                                <button
                                  type="button"
                                  className="flex gap-3 min-w-0 flex-1 text-left"
                                  onClick={() => openPezzo(p, g.serie_nome)}
                                >
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
                                  </div>
                                </button>
                                <div className="flex flex-col gap-1 shrink-0">
                                  <button
                                    type="button"
                                    disabled={busyId === p.id}
                                    className="inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded bg-violet-800 hover:bg-violet-700 text-violet-50 disabled:opacity-50"
                                    onClick={() => {
                                      setTransferFor({ ...p, kind: 'serie' });
                                      setSearchQ('');
                                      setSearchHits([]);
                                    }}
                                  >
                                    <Send size={12} /> Trasferisci
                                  </button>
                                  <button
                                    type="button"
                                    disabled={busyId === p.id}
                                    className="inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded bg-red-900/70 hover:bg-red-800 disabled:opacity-50"
                                    onClick={() => handleDelete({ ...p, kind: 'serie' })}
                                  >
                                    <Trash2 size={12} /> Elimina
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
            </div>
          )}
        </div>
      )}

      {reading && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/75 p-0 sm:p-4">
          <div className="w-full sm:max-w-lg max-h-[90vh] overflow-y-auto bg-gray-900 border border-gray-700 rounded-t-2xl sm:rounded-xl p-4 space-y-3 shadow-xl">
            <div className="flex items-start justify-between gap-2">
              <h4 className="font-bold text-lg text-white pr-2">
                {reading.titolo || reading.etichetta}
              </h4>
              <button
                type="button"
                className="p-1.5 rounded bg-gray-800 hover:bg-gray-700 shrink-0"
                onClick={() => setReading(null)}
              >
                <X size={18} />
              </button>
            </div>
            {reading.kind === 'serie' && (
              <>
                {reading.serie_nome && (
                  <p className="text-xs text-violet-300">{reading.serie_nome}</p>
                )}
                {reading.immagine_url ? (
                  <img
                    src={resolveMediaUrl(reading.immagine_url)}
                    alt={reading.etichetta}
                    className="w-full max-h-[50vh] object-contain rounded-lg bg-black border border-violet-900/40"
                  />
                ) : (
                  <div className="flex justify-center py-10 text-violet-500">
                    <Package size={48} />
                  </div>
                )}
                <p className="text-sm text-gray-400">
                  Pezzo {reading.indice} di {reading.totale}
                </p>
              </>
            )}
            {reading.kind === 'documento' && (
              <>
                {reading.immagine_url && (
                  <img
                    src={resolveMediaUrl(reading.immagine_url)}
                    alt={reading.titolo}
                    className="w-full max-h-[40vh] object-contain rounded-lg bg-black border border-amber-900/40"
                  />
                )}
                {reading.audio_url && (
                  <audio controls className="w-full" src={resolveMediaUrl(reading.audio_url)}>
                    <track kind="captions" />
                  </audio>
                )}
                {reading.video_url && (
                  <video controls className="w-full rounded-lg" src={resolveMediaUrl(reading.video_url)}>
                    <track kind="captions" />
                  </video>
                )}
                {reading.testo ? (
                  <div className="rounded-lg bg-amber-50 text-gray-900 p-3 prose prose-sm max-w-none">
                    <RichHtml content={reading.testo} />
                  </div>
                ) : null}
                {reading.mostra_testo_condizionato && reading.testo_condizionato ? (
                  <div className="rounded-lg bg-amber-100/90 text-gray-900 p-3 prose prose-sm max-w-none border-t border-amber-300">
                    <RichHtml content={reading.testo_condizionato} />
                  </div>
                ) : null}
              </>
            )}
          </div>
        </div>
      )}

      {transferFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md bg-gray-900 border border-violet-800/50 rounded-xl p-4 space-y-3 shadow-xl">
            <h4 className="font-bold text-violet-200">
              Trasferisci «{transferFor.etichetta || transferFor.titolo}»
            </h4>
            <p className="text-xs text-gray-400">
              Cerca il personaggio destinatario. L&apos;elemento sparisce dal tuo archivio e
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
