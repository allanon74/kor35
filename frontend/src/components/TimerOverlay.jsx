import React, { useState, useEffect, useCallback } from 'react';
import { useSharedNowTs } from '../hooks/useSharedNowTs';

const SingleTimer = ({ timer, onExpire }) => {
  const nowTs = useSharedNowTs();
  const timeLeft = Math.max(0, Math.floor((timer.endTime - nowTs) / 1000));
  const isDanger = timer.variant === 'danger';

  useEffect(() => {
    if (timeLeft <= 0) {
      onExpire(timer);
    }
  }, [timeLeft, timer, onExpire]);

  const format = (s) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (isDanger) {
    return (
      <div className="bg-red-950/95 text-white p-4 rounded-xl mb-2 border-2 border-red-500 shadow-[0_0_24px_rgba(239,68,68,0.45)] flex justify-between items-center min-w-[220px] backdrop-blur-sm ring-2 ring-red-400/40 animate-pulse">
        <div className="flex flex-col">
          <span className="text-[11px] text-red-300 uppercase font-black tracking-[0.2em] leading-none mb-1">
            Trappola
          </span>
          <span className="text-sm font-bold uppercase truncate max-w-[140px]">{timer.nome}</span>
        </div>
        <div className="flex flex-col items-end ml-4">
          <span className="font-mono text-2xl font-black text-red-300 drop-shadow-[0_0_12px_rgba(248,113,113,0.7)]">
            {format(timeLeft)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800/95 text-white p-3 rounded-xl mb-2 border-l-4 border-amber-500 shadow-2xl flex justify-between items-center min-w-40 backdrop-blur-sm ring-1 ring-white/10 animate-slide-in-right">
      <div className="flex flex-col">
        <span className="text-[10px] text-gray-400 uppercase font-black tracking-tighter leading-none mb-1">Timer Attivo</span>
        <span className="text-xs font-bold uppercase truncate max-w-[100px]">{timer.nome}</span>
      </div>
      <div className="flex flex-col items-end ml-4">
        <span className="font-mono text-lg font-bold text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.4)]">
          {format(timeLeft)}
        </span>
      </div>
    </div>
  );
};

export const TimerOverlay = ({ activeTimers, onRemove }) => {
  
  // Funzione ricorsiva per riprodurre il suono N volte
  const playSoundSequence = useCallback((remaining) => {
    if (remaining <= 0) return;
    
    const audio = new Audio('/sounds/alert.mp3');
    
    // Quando il suono finisce, chiama se stessa riducendo il contatore
    audio.onended = () => playSoundSequence(remaining - 1);
    
    audio.play().catch(err => {
      // I browser bloccano l'audio se l'utente non ha ancora interagito con la pagina
      console.warn("Riproduzione audio bloccata dal browser. Richiesta interazione utente.", err);
    });
  }, []);

  const handleExpire = (timer) => {
    // 1. Alert Sonoro (Ripetuto 3 volte)
    if (timer.alert_suono) {
      playSoundSequence(3);
    }

    // 2. Notifica di Sistema (Browser Push)
    // Utilizza l'API nativa del browser se i permessi sono concessi
    if (timer.notifica_push && "Notification" in window && Notification.permission === "granted") {
        try {
            new Notification(`Timer Scaduto: ${timer.nome}`, {
                body: timer.variant === 'danger'
                  ? `La trappola "${timer.nome}" è scaduta.`
                  : `Il countdown per la tipologia "${timer.nome}" è terminato.`,
                icon: '/pwa-192x192.png'
            });
        } catch (e) { console.error("Errore invio notifica sistema:", e); }
    }

    // 3. Messaggio In-App (Alert popup)
    if (timer.messaggio_in_app) {
      // Usiamo un piccolo delay per non bloccare l'inizio della sequenza audio
      setTimeout(() => {
        alert(
          timer.variant === 'danger'
            ? `ATTENZIONE: La trappola "${timer.nome}" è scaduta!`
            : `ATTENZIONE: Il timer "${timer.nome}" è scaduto!`
        );
      }, 200);
    }

    // Rimuove il timer dallo stato globale in CharacterContext
    onRemove(timer.nome);
  };

  if (Object.keys(activeTimers).length === 0) return null;

  return (
    <div className="fixed top-20 right-4 z-9999 pointer-events-none flex flex-col items-end max-w-[280px]">
      <div className="pointer-events-auto">
        {Object.values(activeTimers).map(t => (
          <SingleTimer 
            key={t.nome} 
            timer={t} 
            onExpire={handleExpire} 
          />
        ))}
      </div>
    </div>
  );
};

export default TimerOverlay;
