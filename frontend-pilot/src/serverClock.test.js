import assert from 'node:assert/strict';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import {
  anchoredRemainingSeconds,
  clockOffsetMs,
  remainingSecondsUntil,
} from './serverClock.js';
import { useAnchoredSeconds } from './useServerClock.js';

function Probe({ base, sampleKey, now }) {
  const n = useAnchoredSeconds(base, sampleKey, now);
  return React.createElement('span', null, n == null ? 'null' : String(n));
}

test('lo scarto kiosk/mirror non entra nel countdown ancorato al server', () => {
  // DEFCON 0: 5 tick × 22s = 110s. Il display fotografato mostrava ~354131s.
  const durationSec = 110;
  const displayedSkewSec = 354131;
  const serverNow = Date.parse('2026-10-08T09:10:00.000Z');
  const clientNow = serverNow - (displayedSkewSec - durationSec) * 1000;
  const deadline = new Date(serverNow + durationSec * 1000).toISOString();

  const naive = Math.max(0, Math.ceil((Date.parse(deadline) - clientNow) / 1000));
  assert.equal(naive, displayedSkewSec);

  assert.equal(anchoredRemainingSeconds(durationSec, clientNow, clientNow), durationSec);
  assert.equal(anchoredRemainingSeconds(durationSec, clientNow, clientNow + 4000), 106);
  assert.equal(anchoredRemainingSeconds(durationSec, clientNow, clientNow + (durationSec + 5) * 1000), 0);
});

test('l’offset sull’ora del nodo riallinea anche deadline_at', () => {
  const serverIso = '2026-10-08T09:10:00.000Z';
  const serverNow = Date.parse(serverIso);
  const clientNow = serverNow - 354021 * 1000;
  const offset = clockOffsetMs(serverIso, clientNow);
  const gameNow = clientNow + offset;
  const deadline = new Date(serverNow + 110 * 1000).toISOString();
  assert.equal(remainingSecondsUntil(deadline, gameNow), 110);
  assert.equal(remainingSecondsUntil(deadline, gameNow + 2500), 108);
});

test('il countdown ancorato mostra la durata reale, non lo scarto del kiosk', () => {
  const durationSec = 110;
  const displayedSkewSec = 354131;
  const serverNow = Date.parse('2026-10-08T09:10:00.000Z');
  const clientNow = serverNow - (displayedSkewSec - durationSec) * 1000;
  const html = renderToStaticMarkup(
    React.createElement(Probe, { base: durationSec, sampleKey: 'poll-1', now: clientNow }),
  );
  assert.equal(html, '<span>110</span>');
});

test('senza timestamp server l’offset resta zero e i valori invalidi non diventano numeri', () => {
  assert.equal(clockOffsetMs('', Date.now()), 0);
  assert.equal(clockOffsetMs('non-una-data', 1_000), 0);
  assert.equal(anchoredRemainingSeconds(null, 0, 0), null);
  assert.equal(remainingSecondsUntil(null, Date.now()), null);
});
