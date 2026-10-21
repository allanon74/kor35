import { describe, expect, it } from 'vitest';
import {
  etichettaStatoProposta,
  propostaDaRivedere,
  propostaModificabile,
  sezioneProposta,
} from './propostaTecnicaStato';

describe('propostaTecnicaStato', () => {
  it('il rifiuto in bozza esce dalla valutazione e resta modificabile', () => {
    const rimandata = { stato: 'BOZZA', note_staff: '<p>Manca il mattone.</p>', nome: 'Soffio' };
    expect(sezioneProposta(rimandata)).toBe('bozze');
    expect(propostaModificabile(rimandata.stato)).toBe(true);
    expect(propostaDaRivedere(rimandata)).toBe(true);
    expect(etichettaStatoProposta(rimandata)).toBe('Bozza da rivedere');
  });

  it('in valutazione non è modificabile e non è una bozza', () => {
    const inCoda = { stato: 'VALUTAZIONE', note_staff: '', nome: 'Soffio' };
    expect(sezioneProposta(inCoda)).toBe('valutazione');
    expect(propostaModificabile(inCoda.stato)).toBe(false);
    expect(etichettaStatoProposta(inCoda)).toBe('In valutazione');
  });

  it('una nota staff nello storico marca la bozza da rivedere anche senza il campo legacy', () => {
    const daLog = {
      stato: 'BOZZA',
      note_staff: '',
      note_log: [{ origine: 'STAFF', testo: '<p>Manca il mattone.</p>', creata_il: '2026-10-21T18:00:00Z' }],
    };
    expect(propostaDaRivedere(daLog)).toBe(true);
    expect(etichettaStatoProposta(daLog)).toBe('Bozza da rivedere');
  });

  it('un rifiuto legacy RIFIUTATA si tratta come bozza da rivedere', () => {
    const legacy = { stato: 'RIFIUTATA', note_staff: 'Rivedi.', nome: 'Soffio' };
    expect(sezioneProposta(legacy)).toBe('bozze');
    expect(propostaModificabile(legacy.stato)).toBe(true);
    expect(propostaDaRivedere(legacy)).toBe(true);
  });
});
