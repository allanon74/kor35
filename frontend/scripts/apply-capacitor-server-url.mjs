#!/usr/bin/env node
/**
 * Applica CAPACITOR_SERVER_URL a capacitor.config.json prima di `cap sync`.
 * Uso: CAPACITOR_SERVER_URL=http://10.42.0.1 node scripts/apply-capacitor-server-url.mjs
 * Stringa vuota → rimuove server.url (asset locali in dist/).
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const cfgPath = join(root, 'capacitor.config.json');
const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));

if (process.env.CAPACITOR_SERVER_URL === undefined) {
  console.log('CAPACITOR_SERVER_URL non impostata: lascio', cfg.server?.url || '(nessun server.url)');
  process.exit(0);
}

const url = String(process.env.CAPACITOR_SERVER_URL).trim();
if (!url) {
  delete cfg.server;
  console.log('Rimosso server.url (WebView su asset dist/)');
} else {
  cfg.server = {
    ...(cfg.server || {}),
    url,
    cleartext: true,
    allowNavigation: cfg.server?.allowNavigation || [
      'www.kor35.it',
      'kor35.it',
      'app.kor35.it',
      'www.k-o-r-35.it',
      'k-o-r-35.it',
      'kor35.ddns.net',
      'www.arcanadomine.it',
      'arcanadomine.it',
      '*.arcanadomine.it',
      '10.42.0.1',
      '192.168.1.200',
      '192.168.1.50',
    ],
  };
  console.log('server.url =', url);
}

writeFileSync(cfgPath, `${JSON.stringify(cfg, null, 2)}\n`);
