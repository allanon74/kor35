import { useState, useEffect } from 'react';

/**
 * Hook per debouncing di valori
 * @param {any} value - Il valore da debounce
 * @param {number} delay - Il delay in millisecondi
 * @returns {any} Il valore debounced
 */
export const useDebounce = (value, delay = 300) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

/**
 * Hook per debouncing di callback
 * @param {Function} callback - La funzione da debounce
 * @param {number} delay - Il delay in millisecondi
 * @returns {Function} La funzione debounced
 */
export const useDebouncedCallback = (callback, delay = 300) => {
  const [timeoutId, setTimeoutId] = useState(null);

  const debouncedCallback = (...args) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    const newTimeoutId = setTimeout(() => {
      callback(...args);
    }, delay);

    setTimeoutId(newTimeoutId);
  };

  useEffect(() => {
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [timeoutId]);

  return debouncedCallback;
};
