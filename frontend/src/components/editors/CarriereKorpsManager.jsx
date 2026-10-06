import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { X, Users, Briefcase, Shield } from 'lucide-react';
import MasterGenericList from './MasterGenericList';
import SearchableSelect from './SearchableSelect';
import StaffEditorModal from './StaffEditorModal';
import {
  staffGetTipiCarriera,
  staffGetCarriere,
  staffCreateCarriera,
  staffUpdateCarriera,
  staffDeleteCarriera,
  staffGetCariche,
  staffCreateCarica,
  staffUpdateCarica,
  staffDeleteCarica,
  staffGetCarriereMemberships,
  staffCreateCarriereMembership,
  staffUpdateCarriereMembership,
  staffDeleteCarriereMembership,
  staffGetCarrieraTiersSelezionabili,
  getPersonaggiEditList,
  staffGetAbilitaListAll,
} from '../../api';
import { ItalianDateTimeInput } from '../ItalianDateTimeInputs';
import { localDateTimeToApiIso } from '../../utils/italianDateTime';
import {
  LabeledField,
  StaffFieldGrid,
  StaffSection,
  staffInputClass,
} from '../../staff/StaffCrudUi';
import { StaffToolHeader, StaffToolShell } from '../../staff/StaffToolShell';

const TABS = [
  { id: 'org', label: 'Carriere / KORP', icon: Briefcase },
  { id: 'cariche', label: 'Cariche', icon: Shield },
  { id: 'membership', label: 'Appartenenze', icon: Users },
];

const WIKI_TIER_OPTS = [
  { id: 'T1', nome: 'T1' },
  { id: 'T2', nome: 'T2' },
  { id: 'T3', nome: 'T3' },
  { id: 'T4', nome: 'T4' },
];

const inputCls = staffInputClass('min-h-11');

function tipoFromForm(tipi, form) {
  const id = form?.tipo_carriera || form?.tipo_carriera_id;
  return (tipi || []).find((t) => String(t.id) === String(id)) || null;
}

function formatTierOptionLabel(tier) {
  if (!tier) return '';
  const tipo = tier.tipo ? String(tier.tipo).toUpperCase() : '';
  return tipo ? `${tipo} · ${tier.nome}` : tier.nome;
}

function groupTiersByTipo(rows) {
  const map = new Map();
  (rows || []).forEach((t) => {
    const key = t.tipo || 'Altro';
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(t);
  });
  return [...map.entries()].sort(([a], [b]) => String(a).localeCompare(String(b)));
}

function ChipRemoveButton({ onClick, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-md text-red-400 hover:bg-red-950/40 hover:text-red-300"
      aria-label={label}
      title={label}
    >
      <X size={16} />
    </button>
  );
}

function SelectedChip({ children, onRemove, removeLabel }) {
  return (
    <span className="inline-flex max-w-full items-center gap-1 rounded-lg border border-gray-600 bg-gray-800 py-0.5 pl-2 pr-0.5 text-sm text-gray-100">
      <span className="min-w-0 break-words">{children}</span>
      <ChipRemoveButton onClick={onRemove} label={removeLabel} />
    </span>
  );
}

function ChipMultiSelect({
  options,
  pendingValue,
  onAdd,
  emptyText,
  placeholder,
  children,
}) {
  return (
    <div>
      <SearchableSelect
        options={options}
        value={pendingValue}
        onChange={(v) => onAdd(v)}
        placeholder={placeholder}
        minOptionsForSearch={0}
      />
      <div className="mt-2 max-h-52 overflow-y-auto rounded-lg border border-gray-700 bg-gray-950/40 p-2">
        {children || <p className="text-xs text-gray-500">{emptyText}</p>}
      </div>
    </div>
  );
}

function CarrieraModal({
  isOpen,
  onClose,
  onSave,
  value,
  tipi,
  tiersSelezionabili,
  abilitaOptions,
  saving,
}) {
  const [form, setForm] = useState(value || {});
  const [tierToAdd, setTierToAdd] = useState(null);
  const [abilitaToAdd, setAbilitaToAdd] = useState(null);
  useEffect(() => {
    const base = value || {};
    const ids = base.tiers_sblocco_dettaglio
      ? base.tiers_sblocco_dettaglio.map((t) => t.id)
      : base.tiers_sblocco_ids || [];
    const abilitaIds = base.abilita_default_dettaglio
      ? base.abilita_default_dettaglio.map((a) => a.id)
      : base.abilita_default_ids || [];
    setForm({ ...base, tiers_sblocco_ids: ids, abilita_default_ids: abilitaIds });
    setTierToAdd(null);
    setAbilitaToAdd(null);
  }, [value]);

  const selectedTipo = useMemo(() => tipoFromForm(tipi, form), [tipi, form]);
  const isKorp = selectedTipo?.codice === 'korp';

  const tiersById = useMemo(
    () => new Map((tiersSelezionabili || []).map((t) => [String(t.id), t])),
    [tiersSelezionabili],
  );
  const abilitaById = useMemo(
    () => new Map((abilitaOptions || []).map((a) => [String(a.id), a])),
    [abilitaOptions],
  );

  const selectedTierRows = (form.tiers_sblocco_ids || [])
    .map((id) => tiersById.get(String(id)))
    .filter(Boolean);
  const selectedAbilitaRows = (form.abilita_default_ids || [])
    .map((id) => abilitaById.get(String(id)))
    .filter(Boolean);
  const tierGroups = groupTiersByTipo(selectedTierRows);

  const tierOptionsDisponibili = (tiersSelezionabili || [])
    .filter((t) => !(form.tiers_sblocco_ids || []).map(String).includes(String(t.id)))
    .map((t) => ({ ...t, nome: formatTierOptionLabel(t) }));
  const abilitaOptionsDisponibili = (abilitaOptions || []).filter(
    (a) => !(form.abilita_default_ids || []).map(String).includes(String(a.id)),
  );

  if (!isOpen) return null;

  const addTier = (tierId) => {
    if (!tierId) return;
    const sid = String(tierId);
    const current = new Set((form.tiers_sblocco_ids || []).map(String));
    if (!current.has(sid)) {
      setForm({ ...form, tiers_sblocco_ids: [...current, sid].map((x) => Number(x)) });
    }
    setTierToAdd(null);
  };

  const removeTier = (tierId) => {
    const sid = String(tierId);
    const current = (form.tiers_sblocco_ids || []).map(String).filter((x) => x !== sid);
    setForm({ ...form, tiers_sblocco_ids: current.map((x) => Number(x)) });
  };

  const addAbilitaDefault = (abilitaId) => {
    if (!abilitaId) return;
    const sid = String(abilitaId);
    const current = new Set((form.abilita_default_ids || []).map(String));
    if (!current.has(sid)) {
      setForm({ ...form, abilita_default_ids: [...current, sid].map((x) => Number(x)) });
    }
    setAbilitaToAdd(null);
  };

  const removeAbilitaDefault = (abilitaId) => {
    const sid = String(abilitaId);
    const current = (form.abilita_default_ids || []).map(String).filter((x) => x !== sid);
    setForm({ ...form, abilita_default_ids: current.map((x) => Number(x)) });
  };

  return (
    <StaffEditorModal
      title={form?.id ? 'Modifica carriera / KORP' : 'Nuova carriera / KORP'}
      onClose={onClose}
      onSave={() => onSave(form, 'save_close')}
      saveLabel="Salva"
      saving={saving}
      wide
      size="lg"
      footerExtra={
        <button
          type="button"
          disabled={saving}
          onClick={() => onSave(form, 'save_continue')}
          className="min-h-11 w-full rounded-lg bg-violet-900/70 px-4 py-2 text-sm font-semibold text-violet-100 hover:bg-violet-800 disabled:opacity-50 sm:w-auto"
        >
          Salva e continua
        </button>
      }
    >
      <div className="space-y-4" data-testid="carriera-edit-form">
        <StaffSection
          title="Identità"
          hint="Nome e tipo visibili in scheda PG, wiki e filtri staff. Il livello wiki non è il catalogo di abilità più sotto."
        >
          <StaffFieldGrid>
            <LabeledField label="Nome" required hint="Come compare in elenchi, requisiti e profilo.">
              <input
                className={inputCls}
                value={form.nome || ''}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
                placeholder="Es. Forze di Sicurezza, Medico…"
              />
            </LabeledField>
            <LabeledField
              label="Tipo"
              required
              hint="KORP = organizzazione (task, contratti, gradi). Professione = mestiere del PG. Altri tipi seguono lo stesso schema."
            >
              <SearchableSelect
                options={tipi}
                value={form.tipo_carriera || form.tipo_carriera_id || null}
                onChange={(v) => setForm({ ...form, tipo_carriera: v, tipo_carriera_id: v })}
                placeholder="KORP, Professione, …"
              />
            </LabeledField>
            <LabeledField
              label="Livello in wiki"
              hint="Voce catalogo (di solito T3). Non sblocca abilità: quelli sono i cataloghi T1–T4 nella sezione sotto."
            >
              <SearchableSelect
                options={WIKI_TIER_OPTS}
                value={form.tipo || 'T3'}
                onChange={(v) => setForm({ ...form, tipo: v || 'T3' })}
                placeholder="T3"
              />
            </LabeledField>
          </StaffFieldGrid>
          <LabeledField label="Descrizione" hint="Testo staff / wiki. Può restare vuoto.">
            <textarea
              className={staffInputClass('min-h-[96px]')}
              value={form.descrizione || ''}
              onChange={(e) => setForm({ ...form, descrizione: e.target.value })}
              placeholder="Ruolo nell’ambientazione…"
            />
          </LabeledField>
        </StaffSection>

        <StaffSection
          title="Soldi all’evento"
          hint="Somma fissa di crediti data all’inizio di ogni evento ai membri attivi. Si aggiunge al bonus della carica. 0 = nessun extra."
        >
          <StaffFieldGrid>
            <LabeledField
              label="Bonus crediti evento"
              hint="Crediti extra per appartenenza a questa carriera/KORP, indipendenti dalle task."
            >
              <input
                type="number"
                step="0.01"
                inputMode="decimal"
                className={inputCls}
                value={form.bonus_crediti_evento ?? 0}
                onChange={(e) => setForm({ ...form, bonus_crediti_evento: e.target.value })}
              />
            </LabeledField>
          </StaffFieldGrid>
        </StaffSection>

        {isKorp ? (
          <StaffSection
            title="Task della KORP"
            hint="Moltiplicatori sulle ricompense delle missioni di questa KORP, solo per i membri attivi. Prestigio non arriva da cariche o carriere: solo staff, eventi e task."
          >
            <StaffFieldGrid>
              <LabeledField
                label="Fattore crediti delle task"
                hint="1 = normale, 2 = crediti doppi, 0 = le task di questa KORP non danno crediti."
              >
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  inputMode="decimal"
                  className={inputCls}
                  value={form.fattore_task_crediti ?? 1}
                  onChange={(e) => setForm({ ...form, fattore_task_crediti: e.target.value })}
                />
              </LabeledField>
              <LabeledField
                label="Fattore prestigio delle task"
                hint="Indipendente dai crediti. 3 = prestigio triplo, 0 = nessun prestigio da queste task."
              >
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  inputMode="decimal"
                  className={inputCls}
                  value={form.fattore_task_prestigio ?? 1}
                  onChange={(e) => setForm({ ...form, fattore_task_prestigio: e.target.value })}
                />
              </LabeledField>
            </StaffFieldGrid>
          </StaffSection>
        ) : (
          <p className="rounded-lg border border-gray-800 bg-gray-950/40 px-3 py-2 text-[11px] leading-snug text-gray-500">
            Fattori task e contratti si impostano solo se il tipo è KORP. Con il tipo attuale restano i valori di default (fattore 1, niente sottoscrizione).
          </p>
        )}

        {isKorp ? (
          <StaffSection
            title="Contratti"
            hint="Quanti modelli può proporre un membro e se questa KORP è parte contraente."
          >
            <label className="flex min-h-11 items-start gap-2 text-sm text-gray-200">
              <input
                type="checkbox"
                className="mt-1"
                checked={!!form.sottoscrive_contratti}
                onChange={(e) => setForm({ ...form, sottoscrive_contratti: e.target.checked })}
              />
              <span>
                <span className="font-semibold">Sottoscrive contratti</span>
                <span className="mt-0.5 block text-[11px] text-gray-500">
                  I membri possono proporre i modelli di contratto di questa KORP.
                </span>
              </span>
            </label>
            {form.sottoscrive_contratti ? (
              <LabeledField
                label="Slot contratto di base"
                hint="Slot del proponente all’ingresso, prima del bonus della carica e della statistica SCT."
              >
                <input
                  type="number"
                  inputMode="numeric"
                  className={inputCls}
                  value={form.slot_contratto_base ?? 3}
                  onChange={(e) => setForm({ ...form, slot_contratto_base: e.target.value })}
                />
              </LabeledField>
            ) : null}
          </StaffSection>
        ) : null}

        <StaffSection
          title="Cataloghi di abilità sbloccabili"
          hint="Tabelle T1–T4 i cui acquisti sono riservati ai membri attivi. Non è una lista di abilità: per inserire le skill in un catalogo usa Database regole → Tabelle."
        >
          <ChipMultiSelect
            options={tierOptionsDisponibili}
            pendingValue={tierToAdd}
            onAdd={addTier}
            placeholder="Cerca un catalogo (es. T2 · Combattente)…"
            emptyText="Nessun catalogo: i membri non sbloccano acquisti riservati da questa carriera."
          >
            {selectedTierRows.length === 0 ? null : (
              <div className="space-y-3">
                {tierGroups.map(([tipo, rows]) => (
                  <div key={tipo}>
                    <div className="mb-1 text-[10px] font-bold uppercase tracking-wide text-violet-300">
                      Catalogo {tipo}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {rows.map((t) => (
                        <SelectedChip
                          key={t.id}
                          onRemove={() => removeTier(t.id)}
                          removeLabel={`Rimuovi ${t.nome}`}
                        >
                          {t.nome}
                        </SelectedChip>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ChipMultiSelect>
        </StaffSection>

        <StaffSection
          title="Abilità automatiche (perk)"
          hint="Assegnate senza costo all’ingresso e rimosse alla chiusura membership. Es. sconto forgiatura. Non sostituiscono i cataloghi sopra."
        >
          <ChipMultiSelect
            options={abilitaOptionsDisponibili}
            pendingValue={abilitaToAdd}
            onAdd={addAbilitaDefault}
            placeholder="Cerca un’abilità da assegnare in automatico…"
            emptyText="Nessuna perk automatica."
          >
            {selectedAbilitaRows.length === 0 ? null : (
              <div className="flex flex-wrap gap-2">
                {selectedAbilitaRows.map((a) => (
                  <SelectedChip
                    key={a.id}
                    onRemove={() => removeAbilitaDefault(a.id)}
                    removeLabel={`Rimuovi ${a.nome}`}
                  >
                    {a.nome}
                  </SelectedChip>
                ))}
              </div>
            )}
          </ChipMultiSelect>
        </StaffSection>
      </div>
    </StaffEditorModal>
  );
}

function caricaIncludesCarriera(carica, carrieraId) {
  if (!carrieraId) return true;
  const raw = carica?.carriere_ids ?? carica?.carriere ?? [];
  const ids = Array.isArray(raw) ? raw : raw ? [raw] : [];
  if (!ids.length && carica?.carriera) {
    return String(carica.carriera) === String(carrieraId);
  }
  return ids.map(String).includes(String(carrieraId));
}

function CaricaModal({ isOpen, onClose, onSave, value, carriereOptions, saving }) {
  const [form, setForm] = useState(value || {});
  const [carrieraToAdd, setCarrieraToAdd] = useState(null);
  useEffect(() => {
    const base = value || {};
    const ids = base.carriere_ids
      ? base.carriere_ids
      : Array.isArray(base.carriere)
        ? base.carriere
        : base.carriera || base.carriera_id
          ? [base.carriera || base.carriera_id]
          : [];
    setForm({ ...base, carriere_ids: ids.map((x) => Number(x)) });
    setCarrieraToAdd(null);
  }, [value]);

  const carriereById = useMemo(
    () => new Map((carriereOptions || []).map((c) => [String(c.id), c])),
    [carriereOptions],
  );

  if (!isOpen) return null;

  const selectedCarriereRows = (form.carriere_ids || [])
    .map((id) => carriereById.get(String(id)))
    .filter(Boolean);
  const carriereDisponibili = (carriereOptions || []).filter(
    (c) => !(form.carriere_ids || []).map(String).includes(String(c.id)),
  );

  const addCarriera = (id) => {
    if (!id) return;
    const sid = String(id);
    const current = new Set((form.carriere_ids || []).map(String));
    if (!current.has(sid)) {
      setForm({ ...form, carriere_ids: [...current, sid].map((x) => Number(x)) });
    }
    setCarrieraToAdd(null);
  };

  const removeCarriera = (id) => {
    const sid = String(id);
    setForm({
      ...form,
      carriere_ids: (form.carriere_ids || []).map(String).filter((x) => x !== sid).map((x) => Number(x)),
    });
  };

  return (
    <StaffEditorModal
      title={form?.id ? 'Modifica carica' : 'Nuova carica'}
      onClose={onClose}
      onSave={() => onSave(form, 'save_close')}
      saveLabel="Salva"
      saving={saving}
      wide
    >
      <div className="space-y-4" data-testid="carica-edit-form">
        <StaffSection
          title="Identità"
          hint="La carica è il grado (Capitano, Recluta…). Vale in uno o più dipartimenti."
        >
          <LabeledField label="Nome carica" required hint="Come compare su scheda PG e InstaFame.">
            <input
              className={inputCls}
              value={form.nome || ''}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              placeholder="Es. Tenente, Capo reparto…"
            />
          </LabeledField>
          <StaffFieldGrid>
            <LabeledField
              label="Ordine in elenco"
              hint="Numero più basso = più in alto nelle liste. Serve a ordinare i gradi, non è un rango di gioco."
            >
              <input
                type="number"
                inputMode="numeric"
                className={inputCls}
                value={form.ordine ?? 0}
                onChange={(e) => setForm({ ...form, ordine: parseInt(e.target.value || '0', 10) })}
              />
            </LabeledField>
            <label className="flex min-h-11 items-start gap-2 self-end pb-1 text-sm text-gray-200">
              <input
                type="checkbox"
                className="mt-1"
                checked={form.attiva !== false}
                onChange={(e) => setForm({ ...form, attiva: e.target.checked })}
              />
              <span>
                <span className="font-semibold">Carica attiva</span>
                <span className="mt-0.5 block text-[11px] text-gray-500">
                  Se spenta non viene proposta nelle nuove appartenenze.
                </span>
              </span>
            </label>
          </StaffFieldGrid>
        </StaffSection>

        <StaffSection
          title="Dipartimenti"
          hint="KORP o professioni in cui esiste questo grado. Obbligatorio almeno uno (la stessa carica può coprire più reparti)."
        >
          <ChipMultiSelect
            options={carriereDisponibili}
            pendingValue={carrieraToAdd}
            onAdd={addCarriera}
            placeholder="Aggiungi un dipartimento…"
            emptyText="Nessun dipartimento: seleziona almeno una carriera o KORP."
          >
            {selectedCarriereRows.length === 0 ? null : (
              <div className="flex flex-wrap gap-2">
                {selectedCarriereRows.map((c) => (
                  <SelectedChip
                    key={c.id}
                    onRemove={() => removeCarriera(c.id)}
                    removeLabel={`Rimuovi ${c.nome}`}
                  >
                    {c.nome}
                  </SelectedChip>
                ))}
              </div>
            )}
          </ChipMultiSelect>
        </StaffSection>

        <StaffSection
          title="Economia e contratti"
          hint="Valori sommati a quelli della carriera/KORP, per i PG che hanno questa carica attiva."
        >
          <StaffFieldGrid cols={3}>
            <LabeledField
              label="Bonus stipendio evento"
              hint="Soldi (stipendio) extra a inizio evento. 0 = nessun extra."
            >
              <input
                type="number"
                inputMode="decimal"
                className={inputCls}
                value={form.bonus_stipendio_evento ?? 0}
                onChange={(e) => setForm({ ...form, bonus_stipendio_evento: e.target.value })}
              />
            </LabeledField>
            <LabeledField
              label="Bonus crediti evento"
              hint="Crediti extra a inizio evento, in aggiunta a quelli della carriera/KORP."
            >
              <input
                type="number"
                step="0.01"
                inputMode="decimal"
                className={inputCls}
                value={form.bonus_crediti_evento ?? 0}
                onChange={(e) => setForm({ ...form, bonus_crediti_evento: e.target.value })}
              />
            </LabeledField>
            <LabeledField
              label="Bonus slot contratto"
              hint="Si somma agli slot di base della KORP. 0 sul grado d’ingresso; può essere negativo."
            >
              <input
                type="number"
                inputMode="numeric"
                className={inputCls}
                value={form.bonus_slot_contratto ?? 0}
                onChange={(e) => setForm({ ...form, bonus_slot_contratto: e.target.value })}
              />
            </LabeledField>
          </StaffFieldGrid>
        </StaffSection>
      </div>
    </StaffEditorModal>
  );
}

function MembershipModal({
  isOpen,
  onClose,
  onSave,
  value,
  carriereOptions,
  tipi,
  personaggiOptions,
  cariche,
  saving,
}) {
  const [form, setForm] = useState(value || {});
  const [chiudiKorpPrecedenti, setChiudiKorpPrecedenti] = useState(true);
  const [espandiTutteCarriere, setEspandiTutteCarriere] = useState(true);
  useEffect(() => {
    setForm(value || {});
    setChiudiKorpPrecedenti(true);
    setEspandiTutteCarriere(true);
  }, [value]);

  const tipoId = form.tipo_carriera || form.tipo_carriera_id;
  const carrieraId = form.carriera || form.carriera_id;

  const selectedTipo = useMemo(
    () => tipi.find((t) => String(t.id) === String(tipoId)),
    [tipi, tipoId],
  );
  const isKorp = selectedTipo?.codice === 'korp';

  const carriereFiltrate = useMemo(() => {
    if (!tipoId) return carriereOptions;
    return carriereOptions.filter((c) => String(c.tipo_carriera) === String(tipoId));
  }, [carriereOptions, tipoId]);

  const caricheOptions = useMemo(() => {
    if (!carrieraId) return cariche;
    return cariche.filter((c) => caricaIncludesCarriera(c, carrieraId));
  }, [carrieraId, cariche]);

  const selectedCarica = useMemo(
    () => cariche.find((c) => String(c.id) === String(form.carica || form.carica_id)),
    [cariche, form.carica, form.carica_id],
  );

  const carriereDaCarica = useMemo(() => {
    if (!selectedCarica) return [];
    const raw = selectedCarica.carriere_ids ?? selectedCarica.carriere ?? [];
    const ids = Array.isArray(raw) ? raw.map(String) : raw ? [String(raw)] : [];
    if (!ids.length && selectedCarica.carriera) ids.push(String(selectedCarica.carriera));
    return carriereOptions.filter((c) => ids.includes(String(c.id)));
  }, [selectedCarica, carriereOptions]);

  const espansioneAttiva = !form.id && !carrieraId && selectedCarica && carriereDaCarica.length > 1 && espandiTutteCarriere;

  if (!isOpen) return null;

  return (
    <StaffEditorModal
      title={form?.id ? 'Modifica appartenenza' : 'Nuova appartenenza'}
      onClose={onClose}
      onSave={() =>
        onSave(
          { ...form, chiudi_korp_precedenti: chiudiKorpPrecedenti, espandi_tutte_carriere: espandiTutteCarriere },
          'save_close',
        )
      }
      saveLabel="Salva"
      saving={saving}
      wide
    >
      <div className="space-y-4" data-testid="membership-edit-form">
        <StaffSection
          title="Chi e dove"
          hint="Un’appartenenza lega un personaggio a una carriera o KORP, con carica opzionale e periodo di validità."
        >
          <LabeledField label="Personaggio" required hint="Cerca per nome PG o giocatore.">
            <SearchableSelect
              options={personaggiOptions}
              value={form.personaggio || null}
              onChange={(v) => setForm({ ...form, personaggio: v })}
              placeholder="Cerca personaggio…"
            />
          </LabeledField>
          <StaffFieldGrid>
            <LabeledField
              label="Tipo"
              required
              hint="Filtra l’elenco carriere. KORP e professione sono indipendenti: un PG può avere entrambe."
            >
              <SearchableSelect
                options={tipi}
                value={tipoId || null}
                onChange={(v) => setForm({ ...form, tipo_carriera: v, carriera: null, carica: null })}
                placeholder="KORP o Professione…"
              />
            </LabeledField>
            <LabeledField
              label="Carica (opzionale)"
              hint="Grado in quel dipartimento. Puoi partire dalla carica: i dipartimenti collegati compaiono sotto."
            >
              <SearchableSelect
                options={caricheOptions}
                value={form.carica || form.carica_id || null}
                onChange={(v) => setForm({ ...form, carica: v, carriera: null, carriera_id: null })}
                placeholder="Nessuna carica…"
              />
            </LabeledField>
          </StaffFieldGrid>
          {selectedCarica && carriereDaCarica.length > 0 ? (
            <p className="text-xs text-gray-400">
              Dipartimenti di questa carica:{' '}
              <span className="text-gray-200">{carriereDaCarica.map((c) => c.nome).join(', ')}</span>
            </p>
          ) : null}
          {!form.id && selectedCarica && carriereDaCarica.length > 1 ? (
            <label className="flex min-h-11 items-start gap-2 rounded-lg border border-indigo-700/50 bg-indigo-950/30 p-3 text-sm text-indigo-100">
              <input
                type="checkbox"
                className="mt-1"
                checked={espandiTutteCarriere}
                onChange={(e) => setEspandiTutteCarriere(e.target.checked)}
              />
              <span>
                Crea un&apos;appartenenza per <strong>ogni</strong> dipartimento della carica ({carriereDaCarica.length}).
                Togli la spunta per sceglierne uno solo nel campo sotto.
              </span>
            </label>
          ) : null}
          <LabeledField
            label={espansioneAttiva ? 'Carriera / KORP (opzionale)' : 'Carriera / KORP'}
            required={!espansioneAttiva}
            hint={
              espansioneAttiva
                ? 'Lascia vuoto: verrà creata un’appartenenza per ogni dipartimento della carica.'
                : 'Organizzazione o mestiere a cui appartiene il PG.'
            }
          >
            <SearchableSelect
              options={carriereFiltrate}
              value={carrieraId || null}
              onChange={(v) => {
                const row = carriereOptions.find((c) => String(c.id) === String(v));
                setForm({
                  ...form,
                  carriera: v,
                  tipo_carriera: row?.tipo_carriera || form.tipo_carriera,
                });
              }}
              placeholder={espansioneAttiva ? 'Opzionale con espansione automatica' : 'Cerca professione o KORP…'}
              disabled={espansioneAttiva || (!tipoId && carriereFiltrate.length === 0)}
            />
          </LabeledField>
        </StaffSection>

        <StaffSection title="Visibilità e periodo">
          <label className="flex min-h-11 items-start gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className="mt-1"
              checked={form.visibile_social !== false}
              onChange={(e) => setForm({ ...form, visibile_social: e.target.checked })}
            />
            <span>
              <span className="font-semibold">Carica visibile su InstaFame</span>
              <span className="mt-0.5 block text-[11px] text-gray-500">
                Se spento, il grado non compare sul profilo social del PG.
              </span>
            </span>
          </label>
          {isKorp && !form.id && (
            <label className="flex min-h-11 items-start gap-2 rounded-lg border border-amber-600/50 bg-amber-950/30 p-3 text-sm text-amber-100">
              <input
                type="checkbox"
                className="mt-1"
                checked={chiudiKorpPrecedenti}
                onChange={(e) => setChiudiKorpPrecedenti(e.target.checked)}
              />
              <span>
                <strong>Chiudi la KORP precedente</strong> di questo personaggio (imposta la data di fine adesso).
                Consigliato: un PG ha di solito una sola KORP attiva.
              </span>
            </label>
          )}
          <StaffFieldGrid>
            <LabeledField label="Data inizio" hint="Da quando l’appartenenza è valida.">
              <ItalianDateTimeInput
                className="flex min-h-11 w-full items-center rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-white"
                value={form.data_da || ''}
                onChange={(v) => setForm({ ...form, data_da: localDateTimeToApiIso(v) })}
              />
            </LabeledField>
            <LabeledField label="Data fine" hint="Vuoto = ancora in corso. Compila per chiudere l’appartenenza.">
              <ItalianDateTimeInput
                className="flex min-h-11 w-full items-center rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-white"
                value={form.data_a || ''}
                onChange={(v) => setForm({ ...form, data_a: localDateTimeToApiIso(v) })}
              />
            </LabeledField>
          </StaffFieldGrid>
        </StaffSection>
      </div>
    </StaffEditorModal>
  );
}

export default function CarriereKorpsManager({ onLogout }) {
  const [tab, setTab] = useState('org');
  const [tipi, setTipi] = useState([]);
  const [carriere, setCarriere] = useState([]);
  const [cariche, setCariche] = useState([]);
  const [memberships, setMemberships] = useState([]);
  const [personaggi, setPersonaggi] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState('success');
  const [modalCarriera, setModalCarriera] = useState(null);
  const [modalCarica, setModalCarica] = useState(null);
  const [modalMembership, setModalMembership] = useState(null);
  const [tiersSelezionabili, setTiersSelezionabili] = useState([]);
  const [abilitaOptions, setAbilitaOptions] = useState([]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [t, c, ch, m, p, tiers, abilita] = await Promise.all([
        staffGetTipiCarriera(onLogout),
        staffGetCarriere(onLogout),
        staffGetCariche(onLogout),
        staffGetCarriereMemberships(onLogout),
        getPersonaggiEditList(onLogout),
        staffGetCarrieraTiersSelezionabili(onLogout),
        staffGetAbilitaListAll(onLogout),
      ]);
      setTipi(Array.isArray(t) ? t : []);
      setCarriere(Array.isArray(c) ? c : []);
      setCariche(Array.isArray(ch) ? ch : []);
      setMemberships(Array.isArray(m) ? m : []);
      setPersonaggi(Array.isArray(p) ? p : []);
      setTiersSelezionabili(Array.isArray(tiers) ? tiers : []);
      const abList = Array.isArray(abilita) ? abilita : abilita?.results || [];
      setAbilitaOptions(abList.map((a) => ({ id: a.id, nome: a.nome })));
    } catch (e) {
      setStatusMessage(e.message || 'Errore caricamento');
      setStatusType('error');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const carriereSelectOptions = useMemo(
    () =>
      carriere.map((c) => ({
        id: c.id,
        nome: `[${c.tipo_carriera_codice || c.tipo_carriera_nome || '?'}] ${c.nome}`,
        tipo_carriera: c.tipo_carriera || tipi.find((t) => t.codice === c.tipo_carriera_codice)?.id,
      })),
    [carriere, tipi],
  );

  const personaggiSelectOptions = useMemo(
    () =>
      personaggi.map((p) => ({
        id: p.id,
        nome: p.proprietario ? `${p.nome} (${p.proprietario})` : p.nome,
      })),
    [personaggi],
  );

  const carrieraColumns = useMemo(
    () => [
      { key: 'nome', header: 'Nome', getSortValue: (x) => x.nome || '', render: (x) => <span className="font-bold">{x.nome}</span> },
      {
        key: 'tipo',
        header: 'Tipo',
        getSortValue: (x) => x.tipo_carriera_nome || x.tipo_carriera_codice || '',
        render: (x) => x.tipo_carriera_nome || x.tipo_carriera_codice || '—',
      },
      {
        key: 'tier_wiki',
        header: 'Livello wiki',
        getSortValue: (x) => x.tipo || '',
        render: (x) => x.tipo || '—',
        align: 'center',
        width: 110,
      },
      {
        key: 'bonus_cr',
        header: 'Bonus crediti',
        getSortValue: (x) => Number(x.bonus_crediti_evento || 0),
        render: (x) => Number(x.bonus_crediti_evento || 0).toFixed(2),
        align: 'center',
        width: 120,
      },
      {
        key: 'tier_sblocco',
        header: 'Cataloghi',
        getSortValue: (x) => x.tiers_sblocco_dettaglio?.length ?? 0,
        render: (x) => x.tiers_sblocco_dettaglio?.length ?? 0,
        align: 'center',
        width: 100,
      },
      {
        key: 'perk_auto',
        header: 'Perk auto',
        getSortValue: (x) => x.abilita_default_dettaglio?.length ?? 0,
        render: (x) => x.abilita_default_dettaglio?.length ?? 0,
        align: 'center',
        width: 90,
      },
    ],
    [],
  );

  const caricaColumns = useMemo(
    () => [
      { key: 'nome', header: 'Carica', getSortValue: (x) => x.nome || '', render: (x) => <span className="font-bold">{x.nome}</span> },
      {
        key: 'dipartimenti',
        header: 'Dipartimenti',
        getSortValue: (x) => (x.carriere_nomi || []).join(', '),
        getFilterValue: (x) => (x.carriere_nomi || []).join(', '),
        render: (x) => (x.carriere_nomi?.length ? x.carriere_nomi.join(', ') : '—'),
      },
      {
        key: 'bonus_stipendio',
        header: 'Stipendio',
        getSortValue: (x) => Number(x.bonus_stipendio_evento || 0),
        render: (x) => Number(x.bonus_stipendio_evento || 0),
        align: 'center',
        width: 100,
      },
      {
        key: 'bonus_cr',
        header: 'Crediti',
        getSortValue: (x) => Number(x.bonus_crediti_evento || 0),
        render: (x) => Number(x.bonus_crediti_evento || 0).toFixed(2),
        align: 'center',
        width: 90,
      },
      { key: 'ordine', header: 'Ordine', getSortValue: (x) => x.ordine ?? 0, render: (x) => x.ordine ?? 0, align: 'center', width: 80 },
      {
        key: 'attiva',
        header: 'Attiva',
        getSortValue: (x) => (x.attiva === false ? 0 : 1),
        getFilterValue: (x) => (x.attiva === false ? 'No' : 'Sì'),
        render: (x) => (x.attiva === false ? 'No' : 'Sì'),
        align: 'center',
        width: 80,
      },
    ],
    [],
  );

  const membershipSearchText = useCallback(
    (item) =>
      [item.personaggio_nome, item.carriera_nome, item.carica_nome, item.tipo_carriera_codice]
        .filter(Boolean)
        .join(' '),
    [],
  );

  const membershipItemLabel = useCallback(
    (item) =>
      [item.personaggio_nome, item.carriera_nome, item.carica_nome]
        .filter(Boolean)
        .join(' · ') || `Appartenenza #${item.id}`,
    [],
  );

  const membershipColumns = useMemo(
    () => [
      {
        key: 'pg',
        header: 'PG',
        getSortValue: (x) => x.personaggio_nome || '',
        render: (x) => x.personaggio_nome || `#${x.personaggio}`,
      },
      { key: 'carriera', header: 'Carriera', getSortValue: (x) => x.carriera_nome || '', render: (x) => x.carriera_nome || '—' },
      { key: 'tipo', header: 'Tipo', getSortValue: (x) => x.tipo_carriera_codice || '', render: (x) => x.tipo_carriera_codice || '—', width: 110 },
      { key: 'carica', header: 'Carica', getSortValue: (x) => x.carica_nome || '', render: (x) => x.carica_nome || '—' },
      {
        key: 'social',
        header: 'Social',
        getSortValue: (x) => (x.visibile_social === false ? 0 : 1),
        getFilterValue: (x) => (x.visibile_social === false ? 'Nascosta' : 'Visibile'),
        render: (x) => (x.visibile_social === false ? 'Nascosta' : 'Visibile'),
        align: 'center',
        width: 90,
      },
      {
        key: 'stato',
        header: 'Stato',
        getSortValue: (x) => (x.data_a ? 0 : 1),
        getFilterValue: (x) => (x.data_a ? 'Chiusa' : 'Attiva'),
        render: (x) => (x.data_a ? 'Chiusa' : 'Attiva'),
        align: 'center',
        width: 90,
      },
    ],
    [],
  );

  const carrieraFilterConfig = useMemo(
    () => [
      {
        key: 'tipo_carriera_codice',
        label: 'Tipo',
        options: tipi.map((t) => ({ id: t.codice, label: t.nome })),
      },
    ],
    [tipi],
  );

  const caricaFilterConfig = useMemo(
    () => [
      {
        key: 'dipartimento',
        label: 'Dipartimento',
        ui: 'select',
        placeholder: 'Tutti i dipartimenti',
        options: carriere.map((c) => ({ id: c.id, label: c.nome })),
        match: (item, values) => {
          const raw = item.carriere_ids ?? item.carriere ?? [];
          const ids = Array.isArray(raw) ? raw.map(String) : raw ? [String(raw)] : [];
          if (!ids.length && item.carriera) ids.push(String(item.carriera));
          return values.some((v) => ids.includes(String(v)));
        },
      },
      {
        key: 'attiva',
        label: 'Stato',
        ui: 'chips',
        options: [
          { id: true, label: 'Attive' },
          { id: false, label: 'Disattive' },
        ],
        match: (item, values) => values.some((v) => (item.attiva !== false) === v),
      },
    ],
    [carriere],
  );

  const membershipFilterConfig = useMemo(
    () => [
      {
        key: 'tipo_carriera_codice',
        label: 'Tipo',
        options: tipi.map((t) => ({ id: t.codice, label: t.nome })),
      },
      {
        key: 'stato',
        label: 'Stato',
        options: [
          { id: 'attiva', label: 'Attive' },
          { id: 'chiusa', label: 'Chiuse' },
        ],
        match: (item, values) => values.some((v) => (item.data_a ? 'chiusa' : 'attiva') === v),
      },
      {
        key: 'visibile_social',
        label: 'Social',
        options: [
          { id: true, label: 'Visibile' },
          { id: false, label: 'Nascosta' },
        ],
        match: (item, values) => values.some((v) => (item.visibile_social !== false) === v),
      },
    ],
    [tipi],
  );

  const saveCarriera = async (form, mode) => {
    try {
      setSaving(true);
      const payload = {
        nome: form.nome,
        descrizione: form.descrizione || '',
        tipo: form.tipo || 'T3',
        tipo_carriera: form.tipo_carriera || form.tipo_carriera_id,
        bonus_crediti_evento: form.bonus_crediti_evento ?? 0,
        fattore_task_crediti: form.fattore_task_crediti ?? 1,
        fattore_task_prestigio: form.fattore_task_prestigio ?? 1,
        sottoscrive_contratti: !!form.sottoscrive_contratti,
        slot_contratto_base: form.slot_contratto_base ?? 3,
        tiers_sblocco_ids: form.tiers_sblocco_ids || [],
        abilita_default_ids: form.abilita_default_ids || [],
      };
      if (form.id) await staffUpdateCarriera(form.id, payload, onLogout);
      else await staffCreateCarriera(payload, onLogout);
      setStatusMessage('Salvato');
      setStatusType('success');
      await loadAll();
      if (mode === 'save_close') setModalCarriera(null);
      else if (mode === 'save_continue' && form.id) setModalCarriera({ ...form });
      else if (mode !== 'save_continue') setModalCarriera(null);
    } catch (e) {
      setStatusMessage(e.message);
      setStatusType('error');
    } finally {
      setSaving(false);
    }
  };

  const saveCarica = async (form, mode) => {
    try {
      if (!form.carriere_ids?.length) {
        setStatusMessage('Seleziona almeno un dipartimento per la carica.');
        setStatusType('error');
        return;
      }
      setSaving(true);
      const payload = {
        carriere_ids: form.carriere_ids,
        nome: form.nome,
        bonus_stipendio_evento: form.bonus_stipendio_evento ?? 0,
        bonus_crediti_evento: form.bonus_crediti_evento ?? 0,
        bonus_slot_contratto: form.bonus_slot_contratto ?? 0,
        ordine: form.ordine ?? 0,
        attiva: form.attiva !== false,
      };
      if (form.id) await staffUpdateCarica(form.id, payload, onLogout);
      else await staffCreateCarica(payload, onLogout);
      setStatusMessage('Carica salvata');
      setStatusType('success');
      await loadAll();
      if (mode === 'save_close') setModalCarica(null);
    } catch (e) {
      setStatusMessage(e.message);
      setStatusType('error');
    } finally {
      setSaving(false);
    }
  };

  const saveMembership = async (form, mode) => {
    try {
      const tipoId = form.tipo_carriera || form.tipo_carriera_id;
      const carrieraIdLocal = form.carriera || form.carriera_id;
      const caricaId = form.carica || form.carica_id;
      const espandi = !form.id && !carrieraIdLocal && caricaId && form.espandi_tutte_carriere !== false;

      if (!form.personaggio || !tipoId) {
        setStatusMessage('Compila personaggio e tipo.');
        setStatusType('error');
        return;
      }
      if (!espandi && !carrieraIdLocal) {
        setStatusMessage('Compila carriera/KORP oppure usa espansione da carica.');
        setStatusType('error');
        return;
      }
      setSaving(true);
      const payload = {
        personaggio: form.personaggio,
        carriera: carrieraIdLocal || undefined,
        tipo_carriera: tipoId,
        carica: caricaId || null,
        data_da: form.data_da || undefined,
        data_a: form.data_a || null,
        visibile_social: form.visibile_social !== false,
        espandi_tutte_carriere_carica: espandi,
      };
      if (form.id) {
        await staffUpdateCarriereMembership(form.id, payload, onLogout);
        setStatusMessage('Appartenenza salvata');
      } else {
        const res = await staffCreateCarriereMembership(
          { ...payload, chiudi_korp_precedenti: !!form.chiudi_korp_precedenti },
          onLogout,
        );
        const n = res?.count || (res?.created?.length) || 1;
        setStatusMessage(n > 1 ? `${n} appartenenze create` : 'Appartenenza salvata');
      }
      setStatusType('success');
      await loadAll();
      if (mode === 'save_close') setModalMembership(null);
    } catch (e) {
      setStatusMessage(e.message);
      setStatusType('error');
    } finally {
      setSaving(false);
    }
  };

  if (loading && !carriere.length) {
    return <div className="p-8 text-center text-gray-400">Caricamento carriere e KORP…</div>;
  }

  return (
    <StaffToolShell fill>
      <StaffToolHeader
        title="Carriere, KORP e cariche"
        description="Cataloghi: organizzazioni e mestieri, gradi, e chi appartiene a cosa. I numeri cambiano soldi, task e contratti dei PG."
        icon={<Users size={22} />}
      >
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`flex min-h-11 shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-sm ${
                tab === id ? 'bg-violet-600 text-white' : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </StaffToolHeader>

      {statusMessage && (
        <div
          className={`mx-3 mt-2 rounded px-3 py-2 text-sm sm:mx-4 ${
            statusType === 'error' ? 'bg-red-900/50 text-red-200' : 'bg-green-900/40 text-green-200'
          }`}
        >
          {statusMessage}
        </div>
      )}

      <div className="min-h-0 flex-1 p-3 sm:p-4">
        {tab === 'org' && (
          <div className="h-full min-h-0">
            <MasterGenericList
              title="Carriere e KORP"
              items={carriere}
              columns={carrieraColumns}
              loading={loading}
              persistKey="staff-carriere-korps-org"
              filterConfig={carrieraFilterConfig}
              addLabel="Nuova carriera"
              emptyMessage="Nessuna carriera trovata."
              onAdd={() =>
                setModalCarriera({
                  tipo: 'T3',
                  tipo_carriera: tipi.find((t) => t.codice === 'professione')?.id,
                  tiers_sblocco_ids: [],
                  abilita_default_ids: [],
                  bonus_crediti_evento: 0,
                  fattore_task_crediti: 1,
                  fattore_task_prestigio: 1,
                  slot_contratto_base: 3,
                })
              }
              onEdit={(item) =>
                setModalCarriera({
                  ...item,
                  tipo_carriera:
                    item.tipo_carriera || tipi.find((t) => t.codice === item.tipo_carriera_codice)?.id,
                })
              }
              onDelete={async (id) => {
                await staffDeleteCarriera(id, onLogout);
                await loadAll();
              }}
            />
          </div>
        )}
        {tab === 'cariche' && (
          <div className="h-full min-h-0">
            <MasterGenericList
              title="Cariche"
              items={cariche}
              columns={caricaColumns}
              loading={loading}
              persistKey="staff-carriere-korps-cariche"
              filterConfig={caricaFilterConfig}
              addLabel="Nuova carica"
              emptyMessage="Nessuna carica definita."
              onAdd={() => setModalCarica({ attiva: true, ordine: 0 })}
              onEdit={(item) =>
                setModalCarica({
                  ...item,
                  carriere_ids: item.carriere_ids || item.carriere || (item.carriera ? [item.carriera] : []),
                })
              }
              onDelete={async (id) => {
                await staffDeleteCarica(id, onLogout);
                await loadAll();
              }}
            />
          </div>
        )}
        {tab === 'membership' && (
          <div className="h-full min-h-0">
            <MasterGenericList
              title="Appartenenze PG"
              items={memberships}
              columns={membershipColumns}
              loading={loading}
              persistKey="staff-carriere-korps-membership"
              filterConfig={membershipFilterConfig}
              addLabel="Nuova appartenenza"
              emptyMessage="Nessuna appartenenza registrata."
              searchPlaceholder="Cerca personaggio, giocatore, KORP, carriera o carica…"
              getSearchText={membershipSearchText}
              getItemLabel={membershipItemLabel}
              onAdd={() => setModalMembership({})}
              onEdit={(item) =>
                setModalMembership({
                  ...item,
                  personaggio: item.personaggio,
                  carriera: item.carriera,
                  tipo_carriera: item.tipo_carriera,
                  carica: item.carica,
                })
              }
              onDelete={async (id) => {
                await staffDeleteCarriereMembership(id, onLogout);
                await loadAll();
              }}
            />
          </div>
        )}
      </div>

      <CarrieraModal
        isOpen={!!modalCarriera}
        onClose={() => setModalCarriera(null)}
        onSave={saveCarriera}
        value={modalCarriera}
        tipi={tipi}
        tiersSelezionabili={tiersSelezionabili}
        abilitaOptions={abilitaOptions}
        saving={saving}
      />
      <CaricaModal
        isOpen={!!modalCarica}
        onClose={() => setModalCarica(null)}
        onSave={saveCarica}
        value={modalCarica}
        carriereOptions={carriereSelectOptions}
        saving={saving}
      />
      <MembershipModal
        isOpen={!!modalMembership}
        onClose={() => setModalMembership(null)}
        onSave={saveMembership}
        value={modalMembership}
        carriereOptions={carriereSelectOptions}
        tipi={tipi}
        personaggiOptions={personaggiSelectOptions}
        cariche={cariche}
        saving={saving}
      />
    </StaffToolShell>
  );
}
