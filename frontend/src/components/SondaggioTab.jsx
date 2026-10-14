import React, { useCallback, useEffect, useState } from 'react';
import { ClipboardCheck, Loader2 } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { sondaggiGetElenco, sondaggiInviaRisposta } from '../api';
import { PlayerTabHeader, PlayerTabShell } from './personaggi/layout/PlayerTabShell';
import SondaggioCompilazione from './sondaggio/SondaggioCompilazione';

function messaggioErrore(errore) {
  return errore?.data?.error || errore?.message || 'Invio non riuscito.';
}

export default function SondaggioTab({ onLogout }) {
  const { selectedCharacterId } = useCharacter();
  const [elenco, setElenco] = useState([]);
  const [sceltoId, setSceltoId] = useState('');
  const [caricamento, setCaricamento] = useState(true);
  const [invio, setInvio] = useState(false);
  const [errore, setErrore] = useState('');

  const carica = useCallback(async () => {
    if (!selectedCharacterId) return;
    setCaricamento(true);
    setErrore('');
    try {
      const data = await sondaggiGetElenco(selectedCharacterId, onLogout);
      const righe = data?.sondaggi || [];
      setElenco(righe);
      setSceltoId((corrente) => (
        righe.some((riga) => riga.id === corrente) ? corrente : (righe[0]?.id || '')
      ));
    } catch (e) {
      setErrore(messaggioErrore(e));
      setElenco([]);
    } finally {
      setCaricamento(false);
    }
  }, [selectedCharacterId, onLogout]);

  useEffect(() => {
    carica();
  }, [carica]);

  const scelto = elenco.find((riga) => riga.id === sceltoId) || null;

  const invia = async (risposte) => {
    if (!scelto || !selectedCharacterId) return;
    setInvio(true);
    setErrore('');
    try {
      const aggiornato = await sondaggiInviaRisposta(scelto.id, selectedCharacterId, risposte, onLogout);
      setElenco((corrente) => corrente.map((riga) => (riga.id === aggiornato.id ? aggiornato : riga)));
    } catch (e) {
      setErrore(messaggioErrore(e));
    } finally {
      setInvio(false);
    }
  };

  return (
    <PlayerTabShell width="narrow">
      <PlayerTabHeader
        icon={<ClipboardCheck size={22} />}
        title="Sondaggio"
        subtitle="Le risposte restano nell'app, anche senza rete."
      />
      {caricamento ? (
        <div className="flex justify-center py-10" role="status">
          <Loader2 className="animate-spin text-indigo-400" />
        </div>
      ) : null}
      {!caricamento && errore && !scelto ? (
        <p role="alert" className="rounded-lg border border-rose-800 bg-rose-950/40 px-3 py-2 text-sm text-rose-100 break-words">
          {errore}
        </p>
      ) : null}
      {!caricamento && !errore && elenco.length === 0 ? (
        <p className="text-sm text-gray-400">Nessun sondaggio aperto.</p>
      ) : null}
      {elenco.length > 1 ? (
        <div className="mb-4 flex flex-col gap-2">
          {elenco.map((riga) => (
            <button
              key={riga.id}
              type="button"
              onClick={() => { setSceltoId(riga.id); setErrore(''); }}
              className={`min-h-11 rounded-xl border px-3 text-left text-sm font-semibold break-words ${
                riga.id === sceltoId
                  ? 'border-indigo-500 bg-indigo-950/50 text-white'
                  : 'border-gray-700 bg-gray-950 text-gray-300'
              }`}
            >
              {riga.titolo}
              {riga.gia_risposto ? ' · inviato' : ''}
            </button>
          ))}
        </div>
      ) : null}
      {scelto ? (
        <div className="space-y-4">
          <div>
            <h3 className="text-lg font-bold text-white break-words">{scelto.titolo}</h3>
            {scelto.descrizione ? (
              <p className="mt-1 text-sm text-gray-400 whitespace-pre-wrap break-words">{scelto.descrizione}</p>
            ) : null}
          </div>
          <SondaggioCompilazione
            key={scelto.id}
            sondaggio={scelto}
            invio={invio}
            errore={errore}
            onInvia={invia}
          />
        </div>
      ) : null}
    </PlayerTabShell>
  );
}
