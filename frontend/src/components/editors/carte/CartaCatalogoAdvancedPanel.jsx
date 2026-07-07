import React from 'react';
import { buildPlayableSpecFromForm } from '../../../carte/cartePlatformSpecUtils';
import { LabeledField, StaffSection, staffInputClass } from '../../../staff/StaffCrudUi';
import JsonSpecField from './JsonSpecField';

export default function CartaCatalogoAdvancedPanel({
  form,
  setForm,
  studioTemplates = [],
  espansioni = [],
  effectScripts = [],
  onMessage,
}) {
  const handleRegeneratePlayable = () => {
    const spec = buildPlayableSpecFromForm(
      { ...form, effect_scripts: effectScripts },
      espansioni,
    );
    setForm((p) => ({ ...p, arena_playable_spec: spec }));
    onMessage?.('Playable spec rigenerato dai campi gameplay.');
  };

  return (
    <div className="space-y-4">
      <p className="rounded border border-violet-800/50 bg-violet-950/20 px-2 py-1 text-xs text-violet-200">
        Campi per Card Studio e Card Arena. Opzionali: l&apos;editor catalogo funziona anche senza compilarli.
        Vedi <code className="text-violet-300">docs/card-platform/</code>.
      </p>

      <StaffSection
        title="Card Studio (stampa)"
        hint="Template e metadati layout per export futuro."
      >
        <LabeledField
          label="Template Studio"
          hint="Stylesheet di rendering (tab Platform → template)."
        >
          <select
            className={staffInputClass()}
            value={form.studio_template || ''}
            onChange={(e) => setForm((p) => ({
              ...p,
              studio_template: e.target.value || null,
            }))}
          >
            <option value="">— Default / nessuno —</option>
            {studioTemplates.filter((t) => t.attivo !== false).map((t) => (
              <option key={t.id} value={t.id}>{t.nome} ({t.slug})</option>
            ))}
          </select>
        </LabeledField>
        <JsonSpecField
          label="studio_carta_spec (JSON)"
          hint="Layer stampa, bleed, artista (studio_card_spec_v1)."
          value={form.studio_carta_spec}
          onChange={(studio_carta_spec) => setForm((p) => ({ ...p, studio_carta_spec }))}
        />
        <JsonSpecField
          label="mse_campi (JSON)"
          hint="Campi raw MSE per round-trip import/export."
          value={form.mse_campi}
          onChange={(mse_campi) => setForm((p) => ({ ...p, mse_campi }))}
        />
      </StaffSection>

      <StaffSection
        title="Card Arena (gioco)"
        hint="Snapshot normalizzato per il motore duello standalone."
      >
        <div className="mb-2 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded bg-violet-800 px-2 py-1 text-xs text-white hover:bg-violet-700"
            onClick={handleRegeneratePlayable}
          >
            Rigenera playable da gameplay
          </button>
        </div>
        <JsonSpecField
          label="arena_playable_spec (JSON)"
          hint="playable_card_spec_v1 — usato da Card Arena."
          value={form.arena_playable_spec}
          onChange={(arena_playable_spec) => setForm((p) => ({ ...p, arena_playable_spec }))}
          minRows={14}
        />
      </StaffSection>
    </div>
  );
}
