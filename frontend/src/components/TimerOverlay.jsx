import React, { useState, useEffect, useCallback } from 'react';

const SingleTimer = ({ timer, onExpire }) => {
  const [timeLeft, setTimeLeft] = useState(0);

  useEffect(() => {
    const tick = () => {
      const now = Date.now();
      const diff = timer.endTime - now;
      
      if (diff <= 0) {
        onExpire(timer);
      } else {
        setTimeLeft(Math.floor(diff / 1000));
      }
    };

    const interval = setInterval(tick, 1000);
    tick(); // Esecuzione immediata al montaggio
    return () => clearInterval(interval);
  }, [timer.endTime, timer, onExpire]);

  const format = (s) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

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
                body: `Il countdown per la tipologia "${timer.nome}" è terminato.`,
                icon: '/pwa-192x192.png'
            });
        } catch (e) { console.error("Errore invio notifica sistema:", e); }
    }

    // 3. Messaggio In-App (Alert popup)
    if (timer.messaggio_in_app) {
      // Usiamo un piccolo delay per non bloccare l'inizio della sequenza audio
      setTimeout(() => {
        alert(`ATTENZIONE: Il timer "${timer.nome}" è scaduto!`);
      }, 200);
    }

    // Rimuove il timer dallo stato globale in CharacterContext
    onRemove(timer.nome);
  };

  if (Object.keys(activeTimers).length === 0) return null;

  return (
    <div className="fixed top-20 right-4 z-9999 pointer-events-none flex flex-col items-end max-w-[250px]">
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