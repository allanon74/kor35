import { describe, expect, it } from 'vitest';
import { resolveStaffAlarmSampleUrl } from './pilotAlarmPreview';

describe('resolveStaffAlarmSampleUrl', () => {
  it('preferisce l\'URL remoto del campione staff', () => {
    expect(resolveStaffAlarmSampleUrl('giallo', '/media/pilotaggio/allarmi/giallo.mp3?v=1')).toBe(
      '/media/pilotaggio/allarmi/giallo.mp3?v=1',
    );
  });

  it('per i cinque colori storici usa il file statico se non c\'è remoto', () => {
    expect(resolveStaffAlarmSampleUrl('rosso')).toBe('/pilot/sounds/allarmi/rosso.mp3');
    expect(resolveStaffAlarmSampleUrl('crociera', '  ')).toBe('/pilot/sounds/allarmi/crociera.mp3');
  });

  it('ambra/viola/bianco senza remoto non hanno fallback statico', () => {
    expect(resolveStaffAlarmSampleUrl('ambra')).toBe('');
    expect(resolveStaffAlarmSampleUrl('viola')).toBe('');
    expect(resolveStaffAlarmSampleUrl('bianco')).toBe('');
  });
});
