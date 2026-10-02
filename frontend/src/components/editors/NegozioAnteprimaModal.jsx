import React, { useCallback, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import StaffEditorModal from './StaffEditorModal';
import { RichTextViewer } from '../RichTextDisplay';
import NegozioVoceRow from '../negozio/NegozioVoceRow';
import NegozioVoceDetailModal from '../negozio/NegozioVoceDetailModal';
import { staffGetNegozioMercanteAnteprima } from '../../api';

/**
 * Anteprima staff della vetrina di un negozio mercante.
 *
 * Mostra nomi, descrizioni formattate e prezzi base come li vedrebbe un
 * giocatore, senza regole di apertura/visibilità né acquisti: serve a
 * controllare il catalogo prima dell'evento. Tocca una voce per la scheda piena.
 */
const NegozioAnteprimaModal = ({ negozio, onClose, onLogout }) => {
  const [listino, setListino] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [voceAperta, setVoceAperta] = useState(null);

  const load = useCallback(async () => {
    if (!negozio?.id) return;
    setLoading(true);
    try {
      setListino(await staffGetNegozioMercanteAnteprima(negozio.id, onLogout));
      setError('');
    } catch (e) {
      setError(e.message || 'Anteprima non disponibile.');
      setListino(null);
    } finally {
      setLoading(false);
    }
  }, [negozio?.id, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const testoImmersivo = (listino?.descrizione_immersiva || '').trim();
  const voci = Array.isArray(listino?.voci) ? listino.voci : [];
  const isPrestiti = !!listino?.negozio_prestiti;

  const prezzoLabel = (v) => {
    const n = Number(v.prezzo_crediti) || 0;
    if (isPrestiti) return n > 0 ? `Noleggio ${n} CR` : 'Prestito gratis';
    return `${n} CR`;
  };

  return (
    <StaffEditorModal
      title={`Anteprima: ${negozio?.nome || 'negozio'}`}
      onClose={onClose}
      showSave={false}
      wide
    >
      <p className="text-xs text-amber-200/90 bg-amber-950/40 border border-amber-800/60 rounded-lg px-3 py-2">
        Anteprima staff: prezzi base di catalogo. Regole di apertura/visibilità, prezzi duali e
        disponibilità dipendono dal personaggio e non sono applicate qui.
      </p>

      {loading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="animate-spin text-amber-500" size={30} />
        </div>
      ) : error ? (
        <p className="text-red-400 text-sm">{error}</p>
      ) : (
        <>
          {!listino?.aperto && (
            <p className="text-sm text-amber-300 bg-amber-950/40 border border-amber-800 rounded-lg p-3">
              {listino?.messaggio_accesso || 'Negozio non attivo.'}
            </p>
          )}
          {isPrestiti && (
            <p className="text-xs text-sky-300/90 bg-sky-950/40 border border-sky-800/60 rounded-lg px-3 py-2">
              Negozio di prestiti · max {listino?.limite_prestiti_per_personaggio || 1} oggetto per
              personaggio.
            </p>
          )}
          {testoImmersivo && (
            <div className="rounded-xl border border-amber-800/60 bg-amber-950/30 p-4 shadow-inner">
              <p className="text-[10px] font-black text-amber-500 uppercase tracking-widest mb-2">
                Il mercante
              </p>
              <div className="text-amber-50/95 text-sm leading-relaxed prose prose-invert prose-amber max-w-none">
                <RichTextViewer content={testoImmersivo} />
              </div>
            </div>
          )}
          <div className="grid gap-2">
            {voci.map((v) => (
              <NegozioVoceRow
                key={`${v.tipo}-${v.id}`}
                voce={v}
                prezzoLabel={prezzoLabel(v)}
                onOpen={() => setVoceAperta(v)}
              />
            ))}
            {voci.length === 0 && (
              <p className="text-gray-500 text-center py-6 text-sm">
                Catalogo vuoto: nessun articolo da mostrare ai giocatori.
              </p>
            )}
          </div>
        </>
      )}

      {voceAperta && (
        <NegozioVoceDetailModal
          voce={voceAperta}
          prezzoLabel={prezzoLabel(voceAperta)}
          onClose={() => setVoceAperta(null)}
          footerNote="Anteprima staff: nessun acquisto possibile da qui."
        />
      )}
    </StaffEditorModal>
  );
};

export default NegozioAnteprimaModal;
