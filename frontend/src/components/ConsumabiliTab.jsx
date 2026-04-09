import React, { useState, useEffect, useMemo } from 'react';
import { useCharacter } from './CharacterContext';
import { Loader2, Info, Zap, Calendar, X, Timer, PackageCheck } from 'lucide-react';
import RichTextDisplay from './RichTextDisplay';
import { consumaConsumabile, completaCreazioneConsumabile } from '../api';

const ConsumabiliTab = ({ onLogout }) => {
  const { selectedCharacterData: char, selectedCharacterId, refreshCharacterData } = useCharacter();
  const [modalConsumabile, setModalConsumabile] = useState(null);
  const [modalAttivazione, setModalAttivazione] = useState(null);
  const [isConsumendo, setIsConsumendo] = useState(null);
  const [countdowns, setCountdowns] = useState({});
  const [isCompletingConsumable, setIsCompletingConsumable] = useState(null);

  const consumabili = char?.consumabili || [];
  const creazioniInCorso = useMemo(() => char?.creazioni_consumabili_in_corso || [], [char?.creazioni_consumabili_in_corso]);
  const creazioniPronte = useMemo(() => char?.creazioni_consumabili_pronte || [], [char?.creazioni_consumabili_pronte]);
  const creazioniInCorsoKey = useMemo(
    () => creazioniInCorso.map((c) => `${c.id}:${c.secondi_rimanenti}`).sort().join(','),
    [creazioniInCorso]
  );

  useEffect(() => {
    const byId = {};
    creazioniInCorso.forEach((c) => { byId[c.id] = c.secondi_rimanenti ?? 0; });
    setCountdowns((prev) => {
      const next = { ...byId };
      Object.keys(prev).forEach((id) => { if (next[id] === undefined && prev[id] > 0) next[id] = prev[id]; });
      return next;
    });
  }, [char?.id, creazioniInCorsoKey]);

  useEffect(() => {
    const idsInCorso = new Set(creazioniInCorso.map((c) => c.id));
    if (idsInCorso.size === 0) return;
    const t = setInterval(() => {
      setCountdowns((prev) => {
        const next = {};
        let anyZero = false;
        for (const id of idsInCorso) {
          const sec = prev[id] ?? 0;
          const s = Math.max(0, sec - 1);
          next[id] = s;
          if (s === 0) anyZero = true;
        }
        if (anyZero) refreshCharacterData();
        return Object.keys(next).length ? next : prev;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [creazioniInCorso, refreshCharacterData]);

  const handleCompletaCreazione = async (creazioneId, e) => {
    e?.stopPropagation();
    if (isCompletingConsumable || !selectedCharacterId) return;
    setIsCompletingConsumable(creazioneId);
    try {
      const data = await completaCreazioneConsumabile(selectedCharacterId, creazioneId, onLogout);
      if (data?.error) throw new Error(data.error);
      await refreshCharacterData();
    } catch (err) {
      alert(err?.message || 'Errore completamento creazione.');
      await refreshCharacterData();
    } finally {
      setIsCompletingConsumable(null);
    }
  };

  const fmtTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec < 10 ? '0' : ''}${sec}`;
  };

  const handleConsuma = async (item, e) => {
    e.stopPropagation();
    if (isConsumendo || !selectedCharacterId) return;
    if (!window.confirm(`Consumare un utilizzo di "${item.nome}"? Ne resteranno ${item.utilizzi_rimanenti - 1}.`)) return;
    setIsConsumendo(item.id);
    try {
      await consumaConsumabile(item.id, selectedCharacterId, onLogout);
      setModalAttivazione({
        nome: item.nome,
        descrizione: item.descrizione_formattata || item.descrizione,
        formula: item.formula_formattata || item.formula,
      });
      await refreshCharacterData();
    } catch (err) {
      alert(`Errore: ${err.message}`);
    } finally {
      setIsConsumendo(null);
    }
  };

  const formatDate = (d) => {
    if (!d) return '-';
    const dt = new Date(d);
    return dt.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  if (!char) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="animate-spin text-indigo-500" size={48} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Zap className="w-6 h-6 text-amber-400" />
        <h2 className="text-xl font-bold text-gray-200">Consumabili</h2>
        <span className="text-sm text-gray-500">
          (Occupano 1 slot COG se ne hai almeno uno)
        </span>
      </div>

      {/* Creazioni in corso: timer e pronte da aggiungere */}
      {(creazioniInCorso.length > 0 || creazioniPronte.length > 0) && (
        <div className="mb-6 p-4 bg-gray-800/80 rounded-lg border border-cyan-700/50">
          <h3 className="flex items-center gap-2 text-cyan-400 font-bold mb-3">
            <Timer size={20} />
            Creazioni in corso
          </h3>
          <ul className="space-y-2">
            {creazioniPronte.map((c) => (
              <li key={`pronta-${c.id}`} className="flex items-center justify-between py-2 px-3 rounded bg-green-900/30 border border-green-700/50">
                <span className="text-gray-200 font-medium">{c.tessitura_nome}</span>
                <button
                  type="button"
                  onClick={(e) => handleCompletaCreazione(c.id, e)}
                  disabled={isCompletingConsumable === c.id}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-bold disabled:opacity-50"
                >
                  {isCompletingConsumable === c.id ? <Loader2 className="animate-spin" size={16} /> : <PackageCheck size={16} />}
                  Aggiungi a inventario
                </button>
              </li>
            ))}
            {creazioniInCorso.map((c) => {
              const secondi = countdowns[c.id] ?? c.secondi_rimanenti ?? 0;
              return (
                <li key={`corso-${c.id}`} className="flex items-center justify-between py-2 px-3 rounded bg-amber-900/20 border border-amber-700/50">
                  <span className="text-gray-200 font-medium">{c.tessitura_nome}</span>
                  <span className="flex items-center gap-2 text-amber-400 font-mono text-sm">
                    <Timer size={16} />
                    {secondi > 0 ? fmtTime(secondi) : '...'}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {consumabili.length === 0 ? (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-8 text-center text-gray-500">
          <Zap className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>Nessun consumabile in possesso.</p>
          <p className="text-sm mt-1">I consumabili scadono alla fine del giorno indicato.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {consumabili.map((item) => (
            <li
              key={item.id}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
            >
              <div className="flex-1 cursor-pointer" onClick={() => setModalConsumabile(item)}>
                <div className="flex items-center gap-3 mb-1">
                  <span className="font-bold text-gray-200 text-lg">{item.nome}</span>
                  <span className="px-2 py-0.5 rounded-full bg-amber-900/50 text-amber-300 text-sm font-mono font-bold">
                    ×{item.utilizzi_rimanenti}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Calendar size={14} />
                    Scadenza: {formatDate(item.data_scadenza)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={(e) => handleConsuma(item, e)}
                  disabled={isConsumendo === item.id || item.utilizzi_rimanenti <= 0}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed text-white font-bold transition-colors"
                >
                  {isConsumendo === item.id ? (
                    <Loader2 className="animate-spin" size={18} />
                  ) : (
                    <Zap size={18} />
                  )}
                  Consuma
                </button>
                <button
                  onClick={() => setModalConsumabile(item)}
                  className="p-2 text-gray-400 hover:text-white hover:bg-gray-600 rounded-full transition-colors"
                >
                  <Info size={20} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Modale Dettaglio Consumabile */}
      {modalConsumabile && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setModalConsumabile(null)}
        >
          <div
            className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 bg-gray-800 rounded-xl border border-gray-700"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setModalConsumabile(null)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white"
            >
              <X size={24} />
            </button>
            <h3 className="text-xl font-bold text-amber-400 mb-2">{modalConsumabile.nome}</h3>
            <p className="text-sm text-gray-500 mb-4">
              Utilizzi: {modalConsumabile.utilizzi_rimanenti} · Scadenza: {formatDate(modalConsumabile.data_scadenza)}
            </p>
            <div className="prose prose-invert prose-sm max-w-none text-gray-300 mb-4">
              <RichTextDisplay content={modalConsumabile.descrizione_formattata || modalConsumabile.descrizione} />
            </div>
            {modalConsumabile.formula_formattata || modalConsumabile.formula ? (
              <div className="pt-4 border-t border-gray-700">
                <h4 className="text-sm font-bold text-gray-400 mb-2">Formula</h4>
                <div
                  className="text-gray-300"
                  dangerouslySetInnerHTML={{ __html: modalConsumabile.formula_formattata || modalConsumabile.formula || '' }}
                />
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Modale Attivazione (full screen dopo consumo) */}
      {modalAttivazione && (
        <div
          className="fixed inset-0 z-[60] flex flex-col items-center justify-center bg-black p-6"
          onClick={() => setModalAttivazione(null)}
        >
          <div
            className="w-full max-w-3xl max-h-full overflow-y-auto p-8"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-3xl font-bold text-amber-400 mb-6 text-center">{modalAttivazione.nome}</h2>
            <div className="text-lg text-gray-300 leading-relaxed mb-8">
              <RichTextDisplay content={modalAttivazione.descrizione} />
            </div>
            {modalAttivazione.formula ? (
              <div className="pt-6 border-t border-gray-700">
                <h4 className="text-sm font-bold text-gray-400 mb-3">Formula</h4>
                <div
                  className="text-gray-300 text-base"
                  dangerouslySetInnerHTML={{ __html: modalAttivazione.formula }}
                />
              </div>
            ) : null}
            <div className="mt-12 flex justify-center">
              <button
                onClick={() => setModalAttivazione(null)}
                className="px-8 py-3 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-lg"
              >
                Chiudi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConsumabiliTab;
