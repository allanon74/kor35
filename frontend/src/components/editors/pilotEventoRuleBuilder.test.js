import { describe, expect, it } from 'vitest';
import { DEFAULT_RULE_EXPR, emptyRuleBuilder } from './pilotEventoRuleBuilder';

describe('emptyRuleBuilder', () => {
  it('include ST, SP e CA così la chiusura della modale non rompe la pagina', () => {
    const builder = emptyRuleBuilder();
    for (const key of ['st', 'sp', 'ca']) {
      expect(builder[key]).toBeTruthy();
      expect(builder[key].expression).toBe(DEFAULT_RULE_EXPR);
      expect(builder[key].conditions).toEqual([]);
    }
  });
});
