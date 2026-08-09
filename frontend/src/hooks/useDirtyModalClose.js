/**
 * Chiusura modal con conferma se il form è "sporco".
 * Usare come `onClose` di Headless UI Dialog / click su backdrop / X / Annulla.
 */
export function confirmCloseIfDirty(isDirty, onClose, message) {
  if (!isDirty) {
    onClose?.();
    return true;
  }
  const ok = window.confirm(
    message ||
      'Ci sono dati non inviati. Se chiudi perderai le modifiche.\n\nVuoi chiudere comunque?'
  );
  if (ok) {
    onClose?.();
    return true;
  }
  return false;
}

/**
 * Hook: ritorna una funzione requestClose da passare a Dialog/onClick.
 */
export function useDirtyModalClose(isDirty, onClose, message) {
  return () => confirmCloseIfDirty(isDirty, onClose, message);
}
