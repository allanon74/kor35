import { useCallback } from 'react';
import { useCharacter } from '../components/CharacterContext';
import { normalizeTimerRow, timerStateKey } from '../utils/activeTimers';

export const useTimers = () => {
    const { activeTimers, setActiveTimers } = useCharacter();

    const addTimer = useCallback((config) => {
        const normalized = normalizeTimerRow(config);
        if (!normalized) return;
        const key = timerStateKey(normalized);
        setActiveTimers((prev) => ({
            ...prev,
            [key]: {
                ...normalized,
                variant: normalized.variant || prev?.[key]?.variant,
            },
        }));
    }, [setActiveTimers]);

    const removeTimer = useCallback((key) => {
        setActiveTimers((prev) => {
            const newTimers = { ...prev };
            delete newTimers[key];
            return newTimers;
        });
    }, [setActiveTimers]);

    return {
        activeTimers,
        addTimer,
        removeTimer,
    };
};
