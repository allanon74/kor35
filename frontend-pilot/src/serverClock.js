/**
 * Countdown della console pilota ancorato all'orologio del nodo.
 *
 * Il kiosk (Raspberry solo browser) e il mirror non condividono NTP, soprattutto
 * in bosco. `deadline_at - Date.now()` misura lo scarto degli orologi, non la
 * durata dell'evento: in plancia si vedono centinaia di migliaia di secondi
 * mentre il motore, sullo stesso nodo, scade dopo i tick DEFCON.
 *
 * Il backend manda `secondi_rimanenti` calcolato con `timezone.now()` del nodo.
 * Qui si sottrae solo il tempo passato sul device da quando è arrivato il payload.
 */

export function anchoredRemainingSeconds(baseSeconds, anchoredAtMs, nowMs) {
  if (baseSeconds == null || baseSeconds === '') return null;
  const base = Number(baseSeconds);
  if (!Number.isFinite(base) || !Number.isFinite(anchoredAtMs) || !Number.isFinite(nowMs)) {
    return null;
  }
  const elapsed = (nowMs - anchoredAtMs) / 1000;
  return Math.max(0, Math.ceil(base - elapsed));
}

export function clockOffsetMs(serverTimeIso, sampledClientMs) {
  if (!serverTimeIso || !Number.isFinite(sampledClientMs)) return 0;
  const serverMs = Date.parse(serverTimeIso);
  if (!Number.isFinite(serverMs)) return 0;
  return serverMs - sampledClientMs;
}

export function remainingSecondsUntil(deadlineIso, gameNowMs) {
  if (!deadlineIso || !Number.isFinite(gameNowMs)) return null;
  const deadlineMs = Date.parse(deadlineIso);
  if (!Number.isFinite(deadlineMs)) return null;
  return Math.max(0, Math.ceil((deadlineMs - gameNowMs) / 1000));
}
