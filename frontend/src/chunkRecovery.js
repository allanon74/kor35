const CHUNK_RECOVERY_KEY = 'kor35_chunk_recovery_attempted';

function isChunkLoadError(reason) {
  if (!reason) return false;
  const message = String(reason?.message || reason || '').toLowerCase();
  return (
    message.includes('failed to fetch dynamically imported module') ||
    message.includes('importing a module script failed') ||
    message.includes('failed to load module script')
  );
}

async function resetServiceWorkerAndCaches() {
  if ('serviceWorker' in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));
  }

  if ('caches' in window) {
    const keys = await caches.keys();
    await Promise.all(keys.map((key) => caches.delete(key)));
  }
}

function reloadOnce() {
  const alreadyAttempted = sessionStorage.getItem(CHUNK_RECOVERY_KEY) === '1';
  if (alreadyAttempted) return;

  sessionStorage.setItem(CHUNK_RECOVERY_KEY, '1');
  window.location.reload();
}

export function installChunkRecovery() {
  window.addEventListener('unhandledrejection', async (event) => {
    if (!isChunkLoadError(event.reason)) return;
    try {
      await resetServiceWorkerAndCaches();
    } catch (_error) {
      // Best effort cleanup: proceed with reload even if cleanup fails.
    }
    reloadOnce();
  });

  window.addEventListener(
    'error',
    async (event) => {
      const targetSrc = event?.target?.src || '';
      const targetType = event?.target?.tagName || '';
      const targetLooksLikeModuleScript =
        targetType === 'SCRIPT' && String(targetSrc).includes('/assets/');
      const messageLooksLikeChunkError = isChunkLoadError(event?.message);

      if (!targetLooksLikeModuleScript && !messageLooksLikeChunkError) return;
      try {
        await resetServiceWorkerAndCaches();
      } catch (_error) {
        // Best effort cleanup: proceed with reload even if cleanup fails.
      }
      reloadOnce();
    },
    true
  );
}
