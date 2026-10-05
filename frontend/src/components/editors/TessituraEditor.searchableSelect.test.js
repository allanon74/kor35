/**
 * Regressione: import di ./SearchableSelect + const locale omonimo
 * faceva fallire `vite build` e bloccava il deploy.
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, 'TessituraEditor.jsx'), 'utf8');

describe('TessituraEditor SearchableSelect', () => {
  it('non importa e ridefinisce SearchableSelect nello stesso file', () => {
    const hasImport = /import\s+SearchableSelect\s+from\s+['"]\.\/SearchableSelect['"]/.test(src);
    const hasLocal = /(?:^|\n)const\s+SearchableSelect\s*=/.test(src);
    expect(hasImport && hasLocal).toBe(false);
    expect(hasLocal).toBe(true);
  });
});
