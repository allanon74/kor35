import { describe, expect, it } from 'vitest';
import {
  ALARM_FADE_MS,
  ALARM_SPEECH_LEAD_MS,
  ALARM_TAIL_HOLD_MS,
  mixAlarmWithSpeech,
} from './alarmMix';

function controllableSample() {
  let ended = false;
  let resolveEnded = () => {};
  const endedPromise = new Promise((resolve) => {
    resolveEnded = resolve;
  });
  const calls = [];
  return {
    calls,
    finish() {
      if (ended) return;
      ended = true;
      resolveEnded();
    },
    handle: {
      ended: endedPromise,
      isEnded: () => ended,
      stop: () => {
        calls.push('stop');
      },
      fadeOut: async (ms) => {
        calls.push(['fade', ms]);
      },
    },
  };
}

describe('mixAlarmWithSpeech', () => {
  it('fa partire il campione e sovrappone il parlato dopo 1,5 s', async () => {
    const sample = controllableSample();
    const order = [];
    await mixAlarmWithSpeech({
      startSample: () => {
        order.push('sample');
        return sample.handle;
      },
      speak: async () => {
        order.push('speak');
      },
      delay: async (ms) => {
        order.push(ms);
      },
    });
    expect(order).toEqual(['sample', ALARM_SPEECH_LEAD_MS, 'speak', ALARM_TAIL_HOLD_MS]);
    expect(sample.calls).toEqual([['fade', ALARM_FADE_MS], 'stop']);
  });

  it('se il campione finisce prima resta solo la voce, senza dissolvenza', async () => {
    const sample = controllableSample();
    const order = [];
    await mixAlarmWithSpeech({
      startSample: () => sample.handle,
      speak: async () => {
        sample.finish();
        order.push('speak');
      },
      delay: async (ms) => {
        order.push(ms);
      },
    });
    expect(order).toEqual([ALARM_SPEECH_LEAD_MS, 'speak']);
    expect(sample.calls).toEqual(['stop']);
  });

  it('se il campione finisce nei 2 s dopo la frase non sfuma', async () => {
    const sample = controllableSample();
    await mixAlarmWithSpeech({
      startSample: () => sample.handle,
      speak: async () => {},
      delay: async (ms) => {
        if (ms === ALARM_TAIL_HOLD_MS) sample.finish();
      },
    });
    expect(sample.calls).toEqual(['stop']);
  });

  it('se la frase finisce prima tiene il suono 2 s e poi lo sfuma in 2 s', async () => {
    const sample = controllableSample();
    const delays = [];
    await mixAlarmWithSpeech({
      startSample: () => sample.handle,
      speak: async () => {},
      delay: async (ms) => {
        delays.push(ms);
      },
    });
    expect(delays).toEqual([ALARM_SPEECH_LEAD_MS, ALARM_TAIL_HOLD_MS]);
    expect(sample.calls).toEqual([['fade', ALARM_FADE_MS], 'stop']);
    expect(ALARM_FADE_MS).toBe(2000);
    expect(ALARM_TAIL_HOLD_MS).toBe(2000);
  });

  it('un annuncio nuovo interrompe prima della voce e non sfuma', async () => {
    const sample = controllableSample();
    let cancel = false;
    const order = [];
    await mixAlarmWithSpeech({
      startSample: () => sample.handle,
      speak: async () => {
        order.push('speak');
      },
      delay: async () => {
        cancel = true;
      },
      cancelled: () => cancel,
    });
    expect(order).toEqual([]);
    expect(sample.calls).toEqual(['stop']);
  });

  it('un annuncio nuovo durante la coda ferma il suono senza dissolvenza', async () => {
    const sample = controllableSample();
    let cancel = false;
    await mixAlarmWithSpeech({
      startSample: () => sample.handle,
      speak: async () => {},
      delay: async (ms) => {
        if (ms === ALARM_TAIL_HOLD_MS) cancel = true;
      },
      cancelled: () => cancel,
    });
    expect(sample.calls).toEqual(['stop']);
  });
});
