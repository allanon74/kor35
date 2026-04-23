const TOAST_EVENT_NAME = 'kor35:toast';

export const emitToast = ({ type = 'info', title = '', message = '', durationMs = 3000 } = {}) => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent(TOAST_EVENT_NAME, {
      detail: { type, title, message, durationMs },
    })
  );
};

export const onToast = (handler) => {
  if (typeof window === 'undefined') return () => {};
  const wrapped = (event) => handler?.(event?.detail || {});
  window.addEventListener(TOAST_EVENT_NAME, wrapped);
  return () => window.removeEventListener(TOAST_EVENT_NAME, wrapped);
};

