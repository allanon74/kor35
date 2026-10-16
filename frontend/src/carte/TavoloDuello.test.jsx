import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import TavoloDuello from './TavoloDuello';

vi.mock('../components/CharacterContext', () => ({
  useCharacter: () => ({ punteggiList: [] }),
}));

const duello = {
  id: 'd1',
  stato: 'COR',
  modalita_partita: 'LIVE',
  mio_ruolo: 'sfidante',
  turno_personaggio_id: 1,
  influenza_sfidante: 18,
  influenza_sfidato: 12,
  sfidante: { id: 1, nome: 'Io' },
  sfidato: { id: 2, nome: 'Avversario' },
  carte: {
    a: { nome: 'Lama', tipo: 'PG', energia: 'MAR', costo_gioco: 1, attacco: 2, salute: 3, rarita: 'COM' },
    b: { nome: 'Scudo', tipo: 'OGG', energia: 'MAR', costo_gioco: 1 },
    c: { nome: 'Radura', tipo: 'LUO', energia: 'SIL', costo_gioco: 0 },
  },
  stato_gioco: {
    mani: { 1: ['b'] },
    terra_condivisa: { carta_posseduta_id: 'c' },
    campo: {
      1: {
        eroi: ['a', null],
        eroi_is_leader: [true, false],
        salute_eroi: [3, null],
        oggetti: {},
        energia: 2,
        mana_massimo: 3,
        fase_turno: 'APE',
        fase_turno_label: 'Apertura',
        mazzo_count: 10,
        scarto_count: 1,
        mano_count: 1,
      },
      2: {
        eroi: [null, null],
        energia: 1,
        mana_massimo: 3,
        mazzo_count: 12,
        scarto_count: 0,
        mano_count: 4,
      },
    },
  },
};

describe('TavoloDuello', () => {
  it('mostra le due metà del campo, la terra e la mano', () => {
    const html = renderToStaticMarkup(
      <TavoloDuello duello={duello} charId={1} onAzione={() => {}} />,
    );
    expect(html).toContain('Avversario');
    expect(html).toContain('Lama');
    expect(html).toContain('Radura');
    expect(html).toContain('Scudo');
    expect(html).toContain('Tuo turno');
    expect(html).toContain('mano 4');
  });
});
