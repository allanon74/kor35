import { useCallback } from 'react';
import { useCharacter } from '../components/CharacterContext';

export const useTimers = () => {
    const { activeTimers, setActiveTimers } = useCharacter();

    const addTimer = useCallback((config) => {
        // Estraiamo i dati. Supportiamo sia 'label' che 'nome' per flessibilità
        const { 
            nome,
            label, 
            duration, 
            endsAt, 
            alert_suono, 
            notifica_push, 
            messaggio_in_app 
        } = config;

        const timerNome = nome || label || "Operazione";

        // Calcoliamo endTime (millisecondi) come richiesto dal tuo SingleTimer
        const finalExpiration = endsAt 
            ? new Date(endsAt).getTime() 
            : Date.now() + (parseInt(duration || 0) * 1000);

        // Aggiorniamo l'OGGETTO (non l'array) per coerenza con TimerOverlay
        setActiveTimers(prev => ({
            ...prev,
            [timerNome]: {
                nome: timerNome,
                endTime: finalExpiration, // Il tuo SingleTimer usa .endTime
                alert_suono,
                notifica_push,
                messaggio_in_app,
                notified: false
            }
        }));

        console.log(`⏱️ Hook: Timer "${timerNome}" impostato a ${new Date(finalExpiration).toLocaleTimeString()}`);
    }, [setActiveTimers]); // Corretta la dipendenza

    const removeTimer = useCallback((nome) => {
        setActiveTimers(prev => {
            const newTimers = { ...prev };
            delete newTimers[nome];
            return newTimers;
        });
    }, [setActiveTimers]);

    return {
        activeTimers,
        addTimer,
        removeTimer
    };
};