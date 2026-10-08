import { describe, expect, it } from 'vitest';
import {
  noteRiepilogoTask,
  righeRiepilogoTask,
  totaliRiepilogoTask,
} from './riepilogoTaskEvento';

const riga = (over = {}) => ({
  korp_id: 1,
  korp_nome: 'APEX',
  crediti_korp: 20,
  prestigio_korp: 6,
  crediti_non_korp: 5,
  prestigio_non_korp: 1,
  n_task_korp: 1,
  n_task_non_korp: 2,
  ...over,
});

describe('righeRiepilogoTask', () => {
  it('usa i totali di riga inviati dal backend', () => {
    const evento = {
      missioni_riepilogo: [riga({ crediti_totale: 25, prestigio_totale: 7, n_task_totale: 3 })],
    };
    expect(righeRiepilogoTask(evento)[0]).toMatchObject({
      crediti_totale: 25,
      prestigio_totale: 7,
      n_task_totale: 3,
    });
  });

  it('ricalcola i totali di riga se il backend non li invia', () => {
    const riepilogo = righeRiepilogoTask({ missioni_riepilogo: [riga()] })[0];
    expect(riepilogo.crediti_totale).toBe(25);
    expect(riepilogo.prestigio_totale).toBe(7);
    expect(riepilogo.n_task_totale).toBe(3);
  });

  it('tollera un evento senza riepilogo', () => {
    expect(righeRiepilogoTask(null)).toEqual([]);
    expect(righeRiepilogoTask({})).toEqual([]);
  });
});

describe('totaliRiepilogoTask', () => {
  it('preferisce i totali del backend', () => {
    const totali = { n_task_collegate: 8, n_task_attive: 5, crediti_base: 85, crediti_max: 85 };
    expect(totaliRiepilogoTask({ missioni_riepilogo_totali: totali }, [])).toBe(totali);
  });

  it('ricava massimo e conteggio dalle righe se mancano i totali', () => {
    const righe = [
      { crediti_totale: 25, prestigio_totale: 7, n_task_totale: 3 },
      { crediti_totale: 40, prestigio_totale: 4, n_task_totale: 4 },
    ];
    const totali = totaliRiepilogoTask({}, righe);
    expect(totali.crediti_max).toBe(40);
    expect(totali.prestigio_max).toBe(7);
    expect(totali.n_task_collegate).toBe(4);
    // Il totale base non è derivabile dalle righe KORP.
    expect(totali.crediti_base).toBeNull();
  });
});

describe('noteRiepilogoTask', () => {
  it('non avvisa quando i totali sono completi', () => {
    expect(noteRiepilogoTask({
      n_task_attive: 3,
      n_task_spente_catalogo: 0,
      n_task_spente_evento: 0,
      crediti_max: 85,
      prestigio_max: 20,
    })).toEqual([]);
  });

  it('accorda singolare e plurale delle task spente', () => {
    const singolare = noteRiepilogoTask({
      n_task_attive: 1,
      n_task_spente_catalogo: 1,
      n_task_spente_evento: 1,
      crediti_max: 10,
    });
    expect(singolare[0]).toContain('1 task collegata è spenta nel catalogo');
    expect(singolare[1]).toBe('1 task è disattivata per questo evento dal pannello Tasks evento.');

    const plurale = noteRiepilogoTask({
      n_task_attive: 1,
      n_task_spente_catalogo: 2,
      n_task_spente_evento: 3,
      crediti_max: 10,
    });
    expect(plurale[0]).toContain('2 task collegate sono spente nel catalogo');
    expect(plurale[1]).toContain('3 task sono disattivate per questo evento');
  });

  it('spiega i totali a zero quando le task attive non hanno premi', () => {
    const note = noteRiepilogoTask({ n_task_attive: 3, crediti_max: 0, prestigio_max: 0 });
    expect(note).toEqual([
      'Le task conteggiate non hanno premi configurati: i totali restano a zero.',
    ]);
  });

  it('non parla di premi a zero se non ci sono task conteggiate', () => {
    expect(noteRiepilogoTask({ n_task_attive: 0, crediti_max: 0, prestigio_max: 0 })).toEqual([]);
  });
});
