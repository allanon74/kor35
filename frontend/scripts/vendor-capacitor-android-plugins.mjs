/**
 * Dopo `npx cap sync`, Capacitor scrive path verso ../node_modules.
 * Su Windows (copia in C:/dev/...) quel layout si rompe facilmente →
 * "No matching variant of project :capacitor-status-bar" / "No variants exist".
 *
 * Questa script:
 * 1. Copia i moduli Android dei plugin dentro android/capacitor-plugins/
 * 2. Riscrive capacitor.settings.gradle con path locali (self-contained)
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, '..');
const androidRoot = path.join(frontendRoot, 'android');
const nmRoot = path.join(frontendRoot, 'node_modules');
const vendorRoot = path.join(androidRoot, 'capacitor-plugins');

/** @type {{ gradleName: string, from: string, to: string }[]} */
const PLUGINS = [
  {
    gradleName: 'capacitor-android',
    from: path.join(nmRoot, '@capacitor/android/capacitor'),
    to: path.join(vendorRoot, 'capacitor-android'),
  },
  {
    gradleName: 'capacitor-app',
    from: path.join(nmRoot, '@capacitor/app/android'),
    to: path.join(vendorRoot, 'capacitor-app'),
  },
  {
    gradleName: 'capacitor-push-notifications',
    from: path.join(nmRoot, '@capacitor/push-notifications/android'),
    to: path.join(vendorRoot, 'capacitor-push-notifications'),
  },
  {
    gradleName: 'capacitor-status-bar',
    from: path.join(nmRoot, '@capacitor/status-bar/android'),
    to: path.join(vendorRoot, 'capacitor-status-bar'),
  },
];

function rmRf(dir) {
  fs.rmSync(dir, { recursive: true, force: true });
}

function copyDir(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.cpSync(src, dest, { recursive: true });
}

function main() {
  if (!fs.existsSync(androidRoot)) {
    console.error(`ERRORE: manca ${androidRoot}`);
    process.exit(1);
  }

  rmRf(vendorRoot);
  fs.mkdirSync(vendorRoot, { recursive: true });

  const lines = [
    '// Generato da scripts/vendor-capacitor-android-plugins.mjs (dopo cap sync).',
    '// NON punta a ../node_modules: il progetto Android è self-contained.',
    '',
  ];

  for (const plugin of PLUGINS) {
    if (!fs.existsSync(path.join(plugin.from, 'build.gradle'))) {
      console.error(`ERRORE: manca build.gradle in ${plugin.from}`);
      console.error('Esegui: cd frontend && npm ci && npx cap sync android');
      process.exit(1);
    }
    copyDir(plugin.from, plugin.to);
    const buildGradle = path.join(plugin.to, 'build.gradle');
    if (!fs.existsSync(buildGradle)) {
      console.error(`ERRORE: copia fallita per ${plugin.gradleName}`);
      process.exit(1);
    }
    lines.push(`include ':${plugin.gradleName}'`);
    lines.push(
      `project(':${plugin.gradleName}').projectDir = new File('./capacitor-plugins/${plugin.gradleName}')`,
    );
    lines.push('');
    console.log(`vendored :${plugin.gradleName} → capacitor-plugins/${plugin.gradleName}`);
  }

  fs.writeFileSync(path.join(androidRoot, 'capacitor.settings.gradle'), `${lines.join('\n')}\n`);

  fs.writeFileSync(
    path.join(androidRoot, 'APRI_IN_ANDROID_STUDIO.txt'),
    [
      'PATH BLOCCATO — unica cartella da aprire in Android Studio:',
      '',
      '  C:\\dev\\kor35-app\\android',
      '',
      'Dopo: make android-sync WIN=1',
      '',
      'NON aprire:',
      '  - C:\\dev\\kor35-android',
      '  - C:\\dev\\kor35-app          (parent)',
      '  - \\\\wsl.localhost\\...',
      '',
    ].join('\n'),
  );

  console.log('OK: capacitor.settings.gradle usa ./capacitor-plugins/ (no ../node_modules)');
}

main();
