import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpen, Newspaper, PenLine, RefreshCw } from 'lucide-react';
import ArticoloComposer from './ArticoloComposer';
import ArticoloRubricaCard from './ArticoloRubricaCard';
import ArticoloRubricaReader from './ArticoloRubricaReader';
import { getArticoli, getRubriche } from '../../api/rubriche';

/**
 * Sezione «Rubriche» di InstaFame: elenco testate, articoli e lettore giornalistico.
 * La scrittura è riservata ai personaggi autorizzati dallo staff sulla singola rubrica.
 */
export default function RubricheSection({ personaggio, onLogout, articoloIniziale = null }) {
  const personaggioId = personaggio?.id || null;

  const [rubriche, setRubriche] = useState([]);
  const [articoli, setArticoli] = useState([]);
  const [rubricaSelezionata, setRubricaSelezionata] = useState(null);
  const [articoloAperto, setArticoloAperto] = useState(articoloIniziale);
  const [articoloInModifica, setArticoloInModifica] = useState(null);
  const [composerAperto, setComposerAperto] = useState(false);
  const [caricamento, setCaricamento] = useState(true);
  const [errore, setErrore] = useState('');

  const caricaRubriche = useCallback(async () => {
    setCaricamento(true);
    setErrore('');
    try {
      const righe = await getRubriche(personaggioId, onLogout);
      const elenco = Array.isArray(righe) ? righe : righe?.results || [];
      setRubriche(elenco);
    } catch (e) {
      setErrore(e?.message || 'Impossibile caricare le rubriche.');
    } finally {
      setCaricamento(false);
    }
  }, [personaggioId, onLogout]);

  const caricaArticoli = useCallback(
    async (rubricaId) => {
      try {
        const risposta = await getArticoli(personaggioId, onLogout, { rubricaId, pageSize: 30 });
        setArticoli(Array.isArray(risposta?.results) ? risposta.results : risposta || []);
      } catch (e) {
        setErrore(e?.message || 'Impossibile caricare gli articoli.');
        setArticoli([]);
      }
    },
    [personaggioId, onLogout]
  );

  useEffect(() => {
    caricaRubriche();
  }, [caricaRubriche]);

  useEffect(() => {
    if (articoloIniziale) setArticoloAperto(articoloIniziale);
  }, [articoloIniziale]);

  useEffect(() => {
    if (rubricaSelezionata?.id) caricaArticoli(rubricaSelezionata.id);
  }, [rubricaSelezionata, caricaArticoli]);

  const rubricheScrivibili = useMemo(() => rubriche.filter((r) => r.can_write), [rubriche]);

  const apriRubrica = (rubrica) => {
    setRubricaSelezionata(rubrica);
    setArticoloAperto(null);
    setComposerAperto(false);
  };

  const dopoSalvataggio = async (salvato) => {
    if (salvato?.id) {
      setArticoloInModifica(salvato);
      setComposerAperto(true);
    } else {
      setComposerAperto(false);
      setArticoloInModifica(null);
    }
    if (rubricaSelezionata?.id) await caricaArticoli(rubricaSelezionata.id);
    await caricaRubriche();
  };

  if (articoloAperto) {
    return (
      <ArticoloRubricaReader
        articoloId={articoloAperto}
        personaggioId={personaggioId}
        onLogout={onLogout}
        onChiudi={() => setArticoloAperto(null)}
        onModifica={(articolo) => {
          setArticoloInModifica(articolo);
          setComposerAperto(true);
          setArticoloAperto(null);
        }}
      />
    );
  }

  return (
    <section className="space-y-4 lg:max-w-5xl lg:mx-auto lg:w-full">
      <div className="rounded-2xl border border-amber-300/30 bg-[#1b1420]/90 px-3 py-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-amber-200 font-bold">
          <Newspaper size={18} /> Rubriche
        </div>
        <div className="flex items-center gap-2">
          {rubricheScrivibili.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setArticoloInModifica(null);
                setComposerAperto((s) => !s);
              }}
              className="inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-indigo-700/90 hover:bg-indigo-600 border border-indigo-400/30 font-bold"
            >
              <PenLine size={13} /> {composerAperto ? 'Chiudi' : 'Scrivi articolo'}
            </button>
          )}
          <button
            type="button"
            onClick={caricaRubriche}
            className="inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-gray-800 border border-gray-700 hover:bg-gray-700"
          >
            <RefreshCw size={13} /> Aggiorna
          </button>
        </div>
      </div>

      {errore && (
        <p className="text-xs text-red-200 bg-red-950/40 border border-red-500/40 rounded-lg px-3 py-2">{errore}</p>
      )}

      {composerAperto && (
        <ArticoloComposer
          rubriche={rubriche}
          articolo={articoloInModifica}
          rubricaPreselezionata={rubricaSelezionata?.id || ''}
          personaggioAttivo={personaggio}
          onSalvato={dopoSalvataggio}
          onAnnulla={() => {
            setComposerAperto(false);
            setArticoloInModifica(null);
          }}
          onLogout={onLogout}
        />
      )}

      {caricamento && <div className="rounded-2xl border border-gray-700 bg-gray-900/70 h-32 animate-pulse" />}

      {!caricamento && rubriche.length === 0 && (
        <p className="text-sm text-gray-400">Nessuna rubrica pubblicata al momento.</p>
      )}

      {!rubricaSelezionata && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {rubriche.map((rubrica) => (
            <button
              key={rubrica.id}
              type="button"
              onClick={() => apriRubrica(rubrica)}
              className="text-left rounded-2xl border border-amber-200/25 bg-[#17111c]/90 p-3 hover:border-amber-200/60 transition"
              style={{ borderLeft: `4px solid ${rubrica.colore_accento || '#b91c1c'}` }}
            >
              <div className="flex items-center gap-3">
                {rubrica.logo_url ? (
                  <img
                    src={rubrica.logo_url}
                    alt={rubrica.nome}
                    className="w-12 h-12 rounded-xl object-cover border border-white/10"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-black/40 border border-white/10 flex items-center justify-center text-amber-200/70">
                    <BookOpen size={20} />
                  </div>
                )}
                <div className="min-w-0">
                  <h3 className="font-serif font-bold text-amber-50 truncate">{rubrica.nome}</h3>
                  {rubrica.sottotitolo && (
                    <p className="text-xs text-amber-100/70 italic truncate">{rubrica.sottotitolo}</p>
                  )}
                  <p className="text-[11px] text-gray-400">
                    {rubrica.articoli_count} articoli
                    {rubrica.can_write ? ' · puoi scrivere' : ''}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {rubricaSelezionata && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => setRubricaSelezionata(null)}
              className="text-xs text-amber-100/80 hover:text-white"
            >
              ← Tutte le rubriche
            </button>
            <h2
              className="font-serif text-lg font-bold"
              style={{ color: rubricaSelezionata.colore_accento || '#f5d0a9' }}
            >
              {rubricaSelezionata.nome}
            </h2>
          </div>

          {rubricaSelezionata.descrizione && (
            <p className="text-sm text-gray-300">{rubricaSelezionata.descrizione}</p>
          )}

          {articoli.length === 0 && <p className="text-sm text-gray-400">Nessun articolo in questa rubrica.</p>}

          <div className="space-y-3">
            {articoli.map((articolo) => (
              <ArticoloRubricaCard
                key={articolo.id}
                articolo={articolo}
                onOpen={(a) => setArticoloAperto(a.id)}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
