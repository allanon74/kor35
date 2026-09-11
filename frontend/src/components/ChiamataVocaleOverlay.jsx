import React, { useEffect, useMemo, useState } from 'react';
import { Mic, MicOff, Phone, PhoneOff, PhoneIncoming, PhoneOutgoing, Volume2 } from 'lucide-react';

function formatElapsed(startedAt) {
  if (!startedAt) return '00:00';
  const sec = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
  const m = String(Math.floor(sec / 60)).padStart(2, '0');
  const s = String(sec % 60).padStart(2, '0');
  return `${m}:${s}`;
}

const ChiamataVocaleOverlay = ({
  call,
  error,
  busy,
  muted,
  remoteReady,
  acceptCall,
  rejectCall,
  hangup,
  toggleMute,
  boostSpeaker,
}) => {
  const [tick, setTick] = useState(Date.now());

  useEffect(() => {
    if (!call || call.stato !== 'in_corso') return undefined;
    const id = window.setInterval(() => setTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [call]);

  const startedAt = useMemo(() => {
    if (!call || call.stato !== 'in_corso') return null;
    return Date.now();
  }, [call?.id, call?.stato]);

  if (!call && !error && !busy) return null;

  const isIncoming = call?.ruolo === 'callee' && call?.stato === 'ringing';
  const isOutgoing = call?.ruolo === 'caller' && call?.stato === 'ringing';
  const inCall = call?.stato === 'in_corso';
  const peerNome = call?.ruolo === 'caller'
    ? call?.chiamato?.nome || (call?.verso_staff ? 'Staff' : '…')
    : call?.chiamante?.nome || '…';

  return (
    <div className="fixed inset-x-0 bottom-20 sm:bottom-6 z-[200] flex justify-center pointer-events-none px-3">
      <div className="pointer-events-auto w-full max-w-sm rounded-2xl border border-emerald-400/30 bg-gray-950/95 shadow-2xl shadow-black/50 backdrop-blur-md ring-1 ring-white/10 overflow-hidden">
        <div className="flex items-stretch">
          <div className={`w-1.5 shrink-0 ${isIncoming ? 'bg-amber-400' : 'bg-emerald-500'}`} />
          <div className="flex-1 p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-emerald-600/30 p-2.5 text-emerald-300">
                {isIncoming ? <PhoneIncoming size={22} /> : isOutgoing ? <PhoneOutgoing size={22} /> : <Phone size={22} />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-white truncate">
                  {call ? peerNome : 'Chiamata vocale'}
                </p>
                <p className="text-xs text-gray-400">
                  {busy && !call && 'Avvio chiamata…'}
                  {isIncoming && 'Chiamata in arrivo'}
                  {isOutgoing && !busy && 'Chiamata in corso…'}
                  {isOutgoing && busy && 'Avvio…'}
                  {inCall && (remoteReady ? `In linea · ${formatElapsed(startedAt || tick)}` : 'Collegamento audio…')}
                  {!call && !busy && error ? 'Errore' : null}
                </p>
              </div>
            </div>
            {error ? <p className="mt-2 text-xs text-red-400">{error}</p> : null}
            {call ? (
              <p className="mt-2 text-[11px] text-gray-500 leading-snug">
                Usa il viva voce (o cuffie Bluetooth già collegate).
                La cornetta all&apos;orecchio non è disponibile: il browser non può usarla come un telefono.
              </p>
            ) : null}
            <div className="mt-3 flex items-center justify-end gap-2 flex-wrap">
              {isIncoming ? (
                <>
                  <button
                    type="button"
                    onClick={rejectCall}
                    className="inline-flex items-center gap-1.5 rounded-full bg-red-700 hover:bg-red-600 px-3 py-2 text-xs font-bold text-white"
                  >
                    <PhoneOff size={14} /> Rifiuta
                  </button>
                  <button
                    type="button"
                    onClick={acceptCall}
                    className="inline-flex items-center gap-1.5 rounded-full bg-emerald-600 hover:bg-emerald-500 px-3 py-2 text-xs font-bold text-white"
                  >
                    <Phone size={14} /> Rispondi
                  </button>
                </>
              ) : (
                <>
                  {inCall ? (
                    <>
                      <button
                        type="button"
                        onClick={boostSpeaker}
                        className="inline-flex items-center gap-1.5 rounded-full bg-gray-800 text-gray-200 hover:bg-gray-700 px-3 py-2 text-xs font-bold"
                      >
                        <Volume2 size={14} /> Altoparlante
                      </button>
                      <button
                        type="button"
                        onClick={toggleMute}
                        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-2 text-xs font-bold ${
                          muted ? 'bg-amber-700 text-white' : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
                        }`}
                      >
                        {muted ? <MicOff size={14} /> : <Mic size={14} />}
                        {muted ? 'Muto' : 'Microfono'}
                      </button>
                    </>
                  ) : null}
                  <button
                    type="button"
                    onClick={hangup}
                    className="inline-flex items-center gap-1.5 rounded-full bg-red-700 hover:bg-red-600 px-3 py-2 text-xs font-bold text-white"
                  >
                    <PhoneOff size={14} /> Chiudi
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChiamataVocaleOverlay;
