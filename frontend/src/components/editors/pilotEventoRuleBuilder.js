export const DEFAULT_RULE_EXPR = '(1)';

/** Stato iniziale del composer ST/SP/CA. Il reset della modale deve includere tutte e tre. */
export function emptyRuleBuilder() {
  const branch = () => ({ conditions: [], expression: DEFAULT_RULE_EXPR });
  return { st: branch(), sp: branch(), ca: branch() };
}
