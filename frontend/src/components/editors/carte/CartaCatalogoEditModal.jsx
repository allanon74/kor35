import React, { useMemo } from 'react';
import CardFrame from '../../../carte/CardFrame';
import { buildTemaEnergieFromPunteggi } from '../../../carte/carteEnergyAuraMap';
import { CardRulesPreview } from '../../../carte/cardTextBlocks';
import { CARTA_ENERGIA_LABEL, CARTA_RARITA_LABEL, CARTA_TIPO_LABEL } from '../../../carte/carteConstants';
import {
  LabeledField,
  StaffFieldGrid,
  StaffModal,
  StaffSection,
  staffInputClass,
} from '../../../staff/StaffCrudUi';
import BonusEquipEditor from '../BonusEquipEditor';
import CartaEffectScriptsEditor from '../CartaEffectScriptsEditor';
import StatModInline from '../inlines/StatModInline';

function CartaImmagineUpload({
  label,
  previewUrl,
  file,
  onFileChange,
  onRemoveExisting,
  removeExisting,
}) {
  return (
    <LabeledField
      label={label}
      hint="Arte mostrata sulla carta in app. Dopo il deploy: make sync-media sui nodi replica."
    >
      {previewUrl ? (
        <div className="relative mb-2 flex justify-center">
          <img src={previewUrl} alt="" className="max-h-32 rounded border border-gray-600 object-contain" />
        </div>
      ) : (
        <p className="mb-2 text-center text-[10px] text-gray-500">Nessuna immagine</p>
      )}
      <label className="flex cursor-pointer items-center justify-center rounded border border-dashed border-violet-700 bg-violet-950/20 px-2 py-2 text-xs text-violet-200">
        {file ? file.name : 'Scegli file (JPG, PNG, WebP)'}
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          className="hidden"
          onChange={(e) => onFileChange(e.target.files?.[0] || null)}
        />
      </label>
      {previewUrl && !file && onRemoveExisting && (
        <label className="mt-2 flex items-center gap-2 text-xs text-gray-400">
          <input type="checkbox" checked={!!removeExisting} onChange={(e) => onRemoveExisting(e.target.checked)} />
          Rimuovi immagine salvata
        </label>
      )}
    </LabeledField>
  );
}

export default function CartaCatalogoEditModal({
  open,
  isEdit,
  form,
  setForm,
  onClose,
  onSave,
  espansioni,
  tags,
  keywords,
  statsOptions,
  auraOptions,
  elementOptions,
  punteggi,
  cartaPreviewUrl,
  cartaImmagineFile,
  onCartaImmagineChange,
  removeCartaImmagine,
  onRemoveCartaImmagine,
  onMessage,
  gameplayLocked = false,
}) {
  const temaEnergie = useMemo(() => buildTemaEnergieFromPunteggi(punteggi), [punteggi]);

  const previewCarta = useMemo(() => ({
    nome: form.nome || 'Anteprima',
    codice: form.codice,
    tipo: form.tipo,
    energia: form.energia,
    rarita: form.rarita,
    costo_gioco: form.costo_gioco ?? 0,
    attacco: form.attacco,
    salute: form.salute,
    iniziativa: form.iniziativa,
    testo_gioco: form.testo_gioco || '—',
    testo_lore: form.testo_lore,
    immagine_url: cartaPreviewUrl || null,
    tags: (form.tag_ids || [])
      .map((id) => tags.find((t) => t.id === id))
      .filter(Boolean)
      .map((t) => ({ codice: t.codice, nome: t.nome })),
  }), [form, tags, cartaPreviewUrl]);

  const tagGlossary = useMemo(
    () => tags.filter((t) => t.attiva !== false).map((t) => ({ codice: t.codice, nome: t.nome })),
    [tags],
  );

  return (
    <StaffModal
      open={open}
      wide
      title={isEdit ? `Modifica carta — ${form.nome || form.codice}` : 'Nuova carta'}
      onClose={onClose}
      onSave={onSave}
      saveLabel={isEdit ? 'Salva modifiche' : 'Crea carta'}
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px]">
        <div className="space-y-4">
          {isEdit && gameplayLocked && (
            <p className="rounded border border-amber-700/60 bg-amber-950/30 px-2 py-1 text-xs text-amber-200">
              Campagna in OPEN: campi gameplay bloccati (duello). Restano editabili solo reliquiario, lore e metadati.
            </p>
          )}
          <StaffSection
            title="Identità"
            hint="Codice univoco per campagna. Set cronaca e legame servono a progressi collezione e combo reliquiario."
          >
            <StaffFieldGrid>
              <LabeledField label="Codice" required hint="Es. ST-KAEL-001 — univoco in catalogo.">
                <input
                  className={staffInputClass('font-mono')}
                  value={form.codice || ''}
                  onChange={(e) => setForm((p) => ({ ...p, codice: e.target.value }))}
                />
              </LabeledField>
              <LabeledField label="Nome" required>
                <input
                  className={staffInputClass()}
                  value={form.nome || ''}
                  onChange={(e) => setForm((p) => ({ ...p, nome: e.target.value }))}
                />
              </LabeledField>
              <LabeledField
                label="Espansione"
                hint="Collezione ufficiale (Sette Elegie, …). Preferire rispetto al set cronaca legacy."
              >
                <select
                  className={staffInputClass()}
                  value={form.espansione || ''}
                  onChange={(e) => setForm((p) => ({ ...p, espansione: e.target.value || null }))}
                >
                  <option value="">— Nessuna —</option>
                  {espansioni.map((e) => (
                    <option key={e.id} value={e.id}>{e.nome}</option>
                  ))}
                </select>
              </LabeledField>
              <LabeledField
                label="Set cronaca (legacy)"
                hint="Slug cronaca narrativa (es. sette-elegie). Usato da progressi «Cronache» e combo SET. Deprecato: usare Espansione."
              >
                <input
                  className={staffInputClass()}
                  value={form.set_collezione || ''}
                  onChange={(e) => setForm((p) => ({ ...p, set_collezione: e.target.value }))}
                />
              </LabeledField>
              <LabeledField
                label="Campagna lore"
                hint="Sigla evento narrativo di origine (ST, SP, CA, …) — solo metadato lore."
              >
                <input
                  className={staffInputClass()}
                  value={form.campagna_origine || ''}
                  onChange={(e) => setForm((p) => ({ ...p, campagna_origine: e.target.value }))}
                />
              </LabeledField>
              <LabeledField
                label="Legame"
                hint="ID combo reliquiario: carte con lo stesso legame_id possono attivare combo (tab Combo)."
              >
                <input
                  className={staffInputClass()}
                  value={form.legame_id || ''}
                  onChange={(e) => setForm((p) => ({ ...p, legame_id: e.target.value }))}
                />
              </LabeledField>
            </StaffFieldGrid>
            <StaffFieldGrid cols={3}>
              <LabeledField label="Tipo">
                <select
                  className={staffInputClass()}
                  value={form.tipo}
                  disabled={isEdit && gameplayLocked}
                  onChange={(e) => setForm((p) => ({ ...p, tipo: e.target.value }))}
                >
                  {Object.entries(CARTA_TIPO_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </LabeledField>
              <LabeledField label="Energia">
                <select
                  className={staffInputClass()}
                  value={form.energia}
                  disabled={isEdit && gameplayLocked}
                  onChange={(e) => setForm((p) => ({ ...p, energia: e.target.value }))}
                >
                  {Object.entries(CARTA_ENERGIA_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </LabeledField>
              <LabeledField label="Rarità">
                <select
                  className={staffInputClass()}
                  value={form.rarita}
                  disabled={isEdit && gameplayLocked}
                  onChange={(e) => setForm((p) => ({ ...p, rarita: e.target.value }))}
                >
                  {Object.entries(CARTA_RARITA_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </LabeledField>
              <LabeledField label="Layout carta">
                <select
                  className={staffInputClass()}
                  value={form.layout_versione || 'STD'}
                  onChange={(e) => setForm((p) => ({ ...p, layout_versione: e.target.value }))}
                >
                  <option value="STD">Standard</option>
                  <option value="FULL">Full-size borderless</option>
                </select>
              </LabeledField>
            </StaffFieldGrid>
            <CartaImmagineUpload
              label="Immagine arte"
              previewUrl={cartaPreviewUrl}
              file={cartaImmagineFile}
              onFileChange={onCartaImmagineChange}
              removeExisting={removeCartaImmagine}
              onRemoveExisting={form.immagine_url ? onRemoveCartaImmagine : null}
            />
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={!!form.attiva}
                onChange={(e) => setForm((p) => ({ ...p, attiva: e.target.checked }))}
              />
              Carta attiva in catalogo
            </label>
          </StaffSection>

          <StaffSection
            title="Statistiche in gioco (duello)"
            hint="Numeri stampati sulla carta: costo mana, attacco, salute (robustezza), iniziativa. Valgono mentre la carta è in campo come PG/OGG."
          >
            <fieldset disabled={isEdit && gameplayLocked} className="space-y-3 disabled:opacity-60">
            <StaffFieldGrid cols={3}>
              {[
                { key: 'costo_gioco', label: 'Costo gioco', min: 0, max: 3 },
                { key: 'attacco', label: 'Attacco', min: 0, max: 99 },
                { key: 'salute', label: 'Salute (PV)', min: 0, max: 99 },
                { key: 'iniziativa', label: 'Iniziativa', min: 0, max: 5 },
                { key: 'ordine_set', label: 'Ordine nel set', min: 0, max: 999 },
              ].map(({ key, label, min, max }) => (
                <LabeledField key={key} label={label}>
                  <input
                    type="number"
                    min={min}
                    max={max}
                    className={staffInputClass()}
                    value={form[key] ?? ''}
                    onChange={(e) => {
                      const raw = e.target.value;
                      setForm((p) => ({
                        ...p,
                        [key]: raw === '' ? (key === 'ordine_set' ? 0 : null) : Number(raw),
                      }));
                    }}
                  />
                </LabeledField>
              ))}
            </StaffFieldGrid>
            <label className="flex items-center gap-2 text-xs text-gray-400">
              <input
                type="checkbox"
                checked={!!form.duplicabile}
                onChange={(e) => setForm((p) => ({ ...p, duplicabile: e.target.checked }))}
              />
              Duplicabile nel mazzo (max 2 copie)
            </label>
            </fieldset>
          </StaffSection>

          <StaffSection
            title="Legalità duello"
            hint="Controlla uso nei mazzi/scontri. Non impatta reliquiario."
          >
            <fieldset disabled={isEdit && gameplayLocked} className="space-y-2 disabled:opacity-60">
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={form.legale_duello !== false}
                  onChange={(e) => setForm((p) => ({ ...p, legale_duello: e.target.checked }))}
                />
                Carta legale nei duelli
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={!!form.bandita}
                  onChange={(e) => setForm((p) => ({ ...p, bandita: e.target.checked }))}
                />
                Carta bandita dai mazzi
              </label>
              <LabeledField label="Motivazione ban" hint="Obbligatoria se carta bandita.">
                <textarea
                  className={staffInputClass("min-h-[72px]")}
                  value={form.ban_reason || ""}
                  onChange={(e) => setForm((p) => ({ ...p, ban_reason: e.target.value }))}
                />
              </LabeledField>
            </fieldset>
          </StaffSection>

          {tags.length > 0 && (
            <StaffSection
              title="Tag meccanici"
              hint="Etichette per effetti (Cavaliere, …). Non compaiono nel testo: si assegnano qui."
            >
              <fieldset disabled={isEdit && gameplayLocked} className="disabled:opacity-60">
              <div className="flex flex-wrap gap-2">
                {tags.filter((t) => t.attiva !== false).map((t) => {
                  const checked = (form.tag_ids || []).includes(t.id);
                  return (
                    <label
                      key={t.id}
                      className={`flex cursor-pointer items-center gap-1 rounded border px-2 py-1 text-xs ${
                        checked ? 'border-amber-500 bg-amber-900/40' : 'border-gray-600'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          setForm((p) => {
                            const cur = p.tag_ids || [];
                            const next = checked
                              ? cur.filter((id) => id !== t.id)
                              : [...cur, t.id];
                            return { ...p, tag_ids: next };
                          });
                        }}
                      />
                      <span className="font-mono text-[10px] text-gray-400">{t.codice}</span>
                      {t.nome}
                    </label>
                  );
                })}
              </div>
              </fieldset>
            </StaffSection>
          )}

          <StaffSection
            title="Bonus equip"
            hint="Modificatori extra oltre alle statistiche in gioco: in duello (forza/robustezza su oggetto equipaggiato) e sul personaggio LARP quando la carta è nello slot reliquiario."
          >
            <BonusEquipEditor
              tipo={form.tipo}
              value={form.bonus_equip}
              onChange={(bonus_equip) => setForm((p) => ({ ...p, bonus_equip }))}
            />
          </StaffSection>

          <CartaEffectScriptsEditor
            entries={form.effect_scripts_entries || []}
            onChange={(effect_scripts_entries) => setForm((p) => ({ ...p, effect_scripts_entries }))}
            onMessage={onMessage}
            disabled={isEdit && gameplayLocked}
          />

          <StaffSection title="Testo gioco" hint="Flavour e keyword condivise evidenziate in anteprima sotto.">
            <fieldset disabled={isEdit && gameplayLocked} className="space-y-2 disabled:opacity-60">
            <textarea
              className={`${staffInputClass()} min-h-[120px] leading-relaxed`}
              value={form.testo_gioco || ''}
              onChange={(e) => setForm((p) => ({ ...p, testo_gioco: e.target.value }))}
            />
            <CardRulesPreview text={form.testo_gioco} keywords={keywords} />
            </fieldset>
          </StaffSection>

          <StaffSection
            title="Testo reliquiario"
            hint="Mostrato solo nello slot reliquiario (sostituisce il testo gioco lì)."
          >
            <textarea
              className={`${staffInputClass()} min-h-[80px]`}
              value={form.testo_reliquiario || ''}
              onChange={(e) => setForm((p) => ({ ...p, testo_reliquiario: e.target.value }))}
            />
            <CardRulesPreview text={form.testo_reliquiario} keywords={keywords} label="Anteprima" />
          </StaffSection>

          <StaffSection
            title="Statistiche personaggio (reliquiario)"
            hint="Modificano le statistiche LARP del personaggio (FOR, RES, …) quando la carta è equipaggiata nel reliquiario — diverso dai numeri Attacco/Salute sulla carta in duello."
          >
            <StatModInline
              items={form.statistiche_reliquiario || []}
              options={statsOptions}
              auraOptions={auraOptions}
              elementOptions={elementOptions}
              onAdd={() => setForm((p) => ({
                ...p,
                statistiche_reliquiario: [...(p.statistiche_reliquiario || []), {
                  statistica: null,
                  valore: 0,
                  tipo_modificatore: 'ADD',
                  usa_limitazione_aura: false,
                  usa_limitazione_elemento: false,
                  usa_condizione_text: false,
                  condizione_text: '',
                  limit_a_aure: [],
                  limit_a_elementi: [],
                }],
              }))}
              onChange={(i, field, val) => setForm((p) => {
                const next = [...(p.statistiche_reliquiario || [])];
                next[i] = { ...next[i], [field]: val };
                return { ...p, statistiche_reliquiario: next };
              })}
              onRemove={(i) => setForm((p) => ({
                ...p,
                statistiche_reliquiario: (p.statistiche_reliquiario || []).filter((_, idx) => idx !== i),
              }))}
            />
          </StaffSection>

          <StaffSection title="Testo lore">
            <textarea
              className={`${staffInputClass()} min-h-[100px] italic`}
              value={form.testo_lore || ''}
              onChange={(e) => setForm((p) => ({ ...p, testo_lore: e.target.value }))}
            />
          </StaffSection>
        </div>

        <aside className="lg:sticky lg:top-0 lg:self-start">
          <p className="mb-2 text-center text-xs font-bold uppercase tracking-wide text-violet-300">
            Anteprima visiva
          </p>
          <div className="flex justify-center">
            <CardFrame
              carta={previewCarta}
              size="md"
              temaEnergie={temaEnergie}
              keywords={keywords}
              tagsGlossary={tagGlossary}
              showRules
              showLoreText={!!form.testo_lore?.trim()}
              expandRules
            />
          </div>
        </aside>
      </div>
    </StaffModal>
  );
}
