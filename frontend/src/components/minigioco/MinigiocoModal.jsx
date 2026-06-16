import React, { useState, useEffect, useCallback, useRef } from 'react';
import { X, Timer, Loader, Puzzle } from 'lucide-react';
import SlidingPuzzle from './SlidingPuzzle';
import MemoryGame from './MemoryGame';
import RotateTiles from './RotateTiles';
import { minigiocoComplete, minigiocoExpire } from '../../api';

const TIPO_LABELS = {
  sliding_puzzle: 'Ricomponi l\'immagine',
  memory: 'Memory',
  rotate_tiles: 'Ruota le tessere',
};

const isSolvedClient = (tipo, stato) => {
  if (!stato) return false;
  if (tipo === 'sliding_puzzle') {
    const size = stato.size || Math.round(Math.sqrt((stato.tiles || []).length));
    const expected = Array.from({ length: size * size }, (_, i) => i);
    return JSON.stringify(stato.tiles) === JSON.stringify(expected);
  }
  if (tipo === 'memory') {
    const cols = stato.cols || 3;
    const rows = stato.rows || 4;
    const total = cols * rows;
    const matched = new Set(stato.matched || []);
    return matched.size === total;
  }
  if (tipo === 'rotate_tiles') {
    const rots = stato.rotations || [];
    return rots.length > 0 && rots.every((r) => (Number(r) || 0) % 4 === 0);
  }
  return false;
};

const MinigiocoModal = ({
  payload,
  qrcodeId,
  personaggioId,
  onLogout,
  onUnlocked,
  onBlocked,
  onClose,
}) => {
  const dati = payload?.dati || {};
  const [session, setSession] = useState(dati);
  const [statoGioco, setStatoGioco] = useState(() => ({
    ...dati.stato_gioco,
    size: dati.stato_gioco?.size,
    cols: dati.stato_gioco?.cols,
    rows: dati.stato_gioco?.rows,
  }));
  const [secondsLeft, setSecondsLeft] = useState(dati.timer_secondi_rimanenti ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const expiredRef = useRef(false);

  useEffect(() => {
    setSession(dati);
    setStatoGioco({
      ...dati.stato_gioco,
      size: dati.stato_gioco?.size,
      cols: dati.stato_gioco?.cols,
      rows: dati.stato_gioco?.rows,
    });
    setSecondsLeft(dati.timer_secondi_rimanenti ?? null);
    expiredRef.current = false;
  }, [dati.session_id, payload]);

  const handleExpire = useCallback(async () => {
    if (expiredRef.current || !session?.session_id) return;
    expiredRef.current = true;
    setBusy(true);
    setError('');
    try {
      const res = await minigiocoExpire(session.session_id, personaggioId, onLogout);
      if (res.tipo_modello === 'minigioco_bloccato') {
        onBlocked?.(res);
        return;
      }
      if (res.tipo_modello === 'minigioco_superato') {
        onUnlocked?.(res.minigioco_session_id, qrcodeId, res.messaggio);
        return;
      }
      if (res.tipo_modello === 'minigioco_richiesto') {
        expiredRef.current = false;
        setSession(res.dati);
        setStatoGioco({ ...res.dati.stato_gioco });
        setSecondsLeft(res.dati.timer_secondi_rimanenti ?? null);
        setError(res.messaggio || 'Il minigioco riparte.');
        return;
      }
      setError(res.messaggio || res.error || 'Tempo scaduto.');
    } catch (e) {
      setError(e.message || 'Errore scadenza timer.');
      expiredRef.current = false;
    } finally {
      setBusy(false);
    }
  }, [session?.session_id, personaggioId, onLogout, onBlocked, onUnlocked, qrcodeId]);

  useEffect(() => {
    if (secondsLeft == null || secondsLeft <= 0) return undefined;
    const t = setInterval(() => {
      setSecondsLeft((s) => {
        if (s == null) return s;
        if (s <= 1) {
          clearInterval(t);
          handleExpire();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [session?.session_id, secondsLeft, handleExpire]);

  const tryComplete = useCallback(async () => {
    if (!session?.session_id || busy) return;
    const tipo = session.tipo;
    const fullState = {
      ...statoGioco,
      tiles: statoGioco.tiles,
      cards: statoGioco.cards ?? session.stato_gioco?.cards,
      matched: statoGioco.matched,
      rotations: statoGioco.rotations,
      cols: statoGioco.cols || session.stato_gioco?.cols,
      rows: statoGioco.rows || session.stato_gioco?.rows,
      size: statoGioco.size || session.stato_gioco?.size,
    };
    if (!isSolvedClient(tipo, fullState)) return;

    setBusy(true);
    setError('');
    try {
      const res = await minigiocoComplete(session.session_id, personaggioId, fullState, onLogout);
      onUnlocked?.(res.minigioco_session_id, qrcodeId, res.messaggio);
    } catch (e) {
      setError(e.message || 'Soluzione non accettata.');
    } finally {
      setBusy(false);
    }
  }, [session, statoGioco, busy, personaggioId, onLogout, onUnlocked, qrcodeId]);

  useEffect(() => {
    if (isSolvedClient(session?.tipo, statoGioco)) {
      tryComplete();
    }
  }, [statoGioco, session?.tipo, tryComplete]);

  const tipo = session?.tipo;
  const imageUrl = session?.immagine_url;

  const renderGame = () => {
    if (tipo === 'sliding_puzzle') {
      const size = statoGioco.size || session.stato_gioco?.size || 3;
      return (
        <SlidingPuzzle
          size={size}
          tiles={statoGioco.tiles || []}
          imageUrl={imageUrl}
          onChange={(patch) => setStatoGioco((s) => ({ ...s, ...patch }))}
        />
      );
    }
    if (tipo === 'memory') {
      const cols = statoGioco.cols || session.stato_gioco?.cols || 3;
      const rows = statoGioco.rows || session.stato_gioco?.rows || 4;
      return (
        <MemoryGame
          cols={cols}
          rows={rows}
          cards={statoGioco.cards || session.stato_gioco?.cards || []}
          matched={statoGioco.matched || []}
          imageUrl={imageUrl}
          onChange={(patch) => setStatoGioco((s) => ({ ...s, ...patch }))}
        />
      );
    }
    if (tipo === 'rotate_tiles') {
      const size = statoGioco.size || session.stato_gioco?.size || 3;
      return (
        <RotateTiles
          size={size}
          rotations={statoGioco.rotations || []}
          imageUrl={imageUrl}
          onChange={(patch) => setStatoGioco((s) => ({ ...s, ...patch }))}
        />
      );
    }
    return <p className="text-red-400">Tipo minigioco sconosciuto.</p>;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-3">
      <div className="flex flex-col w-full max-w-md max-h-[95vh] bg-gray-900 rounded-xl border border-indigo-500 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-gray-700 shrink-0">
          <div className="flex items-center gap-2 text-indigo-300">
            <Puzzle className="w-5 h-5" />
            <h2 className="font-bold">{TIPO_LABELS[tipo] || 'Minigioco'}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 text-gray-400 rounded-full hover:bg-gray-700"
            aria-label="Chiudi"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 overflow-y-auto flex-1 space-y-3">
          {(payload?.messaggio || session?.messaggio_pre) && (
            <p className="text-sm text-gray-300">{payload?.messaggio || session?.messaggio_pre}</p>
          )}

          <p className="text-xs text-center text-indigo-300/90">
            {TIPO_LABELS[tipo] || tipo}
            {session?.difficolta ? ` · livello ${session.difficolta}` : ''}
            {session?.difficolta_label ? ` (${session.difficolta_label})` : ''}
          </p>

          {secondsLeft != null && (
            <div
              className={`flex items-center justify-center gap-2 text-sm font-mono ${
                secondsLeft <= 10 ? 'text-red-400' : 'text-amber-300'
              }`}
            >
              <Timer className="w-4 h-4" />
              {secondsLeft}s
            </div>
          )}

          {renderGame()}

          {error && <p className="text-sm text-amber-400 text-center">{error}</p>}
          {busy && (
            <div className="flex justify-center text-indigo-300">
              <Loader className="w-6 h-6 animate-spin" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MinigiocoModal;
