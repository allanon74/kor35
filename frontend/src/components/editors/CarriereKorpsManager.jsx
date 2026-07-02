import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { X, Users, Briefcase, Shield } from 'lucide-react';
import MasterGenericList from './MasterGenericList';
import EditorSaveActions from './EditorSaveActions';
import SearchableSelect from './SearchableSelect';
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
import {
  ItalianDateTimeInput,
} from '../ItalianDateTimeInputs';
import { localDateTimeToApiIso } from '../../utils/italianDateTime';

const TABS = [
  { id: 'org', label: 'Carriere / KORP', icon: Briefcase },
  { id: 'cariche', label: 'Cariche', icon: Shield },
  { id: 'membership', label: 'Appartenenze', icon: Users },
];

function CarrieraModal({ isOpen, onClose, onSave, value, tipi, tiersSelezionabili, abilitaOptions, statusMessage, statusType }) {
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

  const tiersById = useMemo(
    () => new Map((tiersSelezionabili || []).map((t) => [String(t.id), t])),
    [tiersSelezionabili],
  );
  const abilitaById = useMemo(
    () => new Map((abilitaOptions || []).map((a) => [String(a.id), a])),
    [abilitaOptions],
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

  const selectedTierRows = (form.tiers_sblocco_ids || [])
    .map((id) => tiersById.get(String(id)))
    .filter(Boolean);
  const selectedAbilitaRows = (form.abilita_default_ids || [])
    .map((id) => abilitaById.get(String(id)))
    .filter(Boolean);

  const tierOptionsDisponibili = (tiersSelezionabili || []).filter(
    (t) => !(form.tiers_sblocco_ids || []).map(String).includes(String(t.id)),
  );
  const abilitaOptionsDisponibili = (abilitaOptions || []).filter(
    (a) => !(form.abilita_default_ids || []).map(String).includes(String(a.id)),
  );

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-gray-900 border border-gray-700 rounded-xl">
        <div className="p-4 border-b border-gray-700 flex justify-between items-center">
          <h3 className="text-lg font-bold text-white">{form?.id ? 'Modifica' : 'Nuova'} carriera</h3>
          <button type="button" onClick={onClose}><X className="text-gray-400" size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            placeholder="Nome"
            value={form.nome || ''}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
          />
          <textarea
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white min-h-[90px]"
            placeholder="Descrizione"
            value={form.descrizione || ''}
            onChange={(e) => setForm({ ...form, descrizione: e.target.value })}
          />
          <label className="block text-xs text-gray-400 mb-1">Tipo carriera</label>
          <SearchableSelect
            options={tipi}
            value={form.tipo_carriera || form.tipo_carriera_id || null}
            onChange={(v) => setForm({ ...form, tipo_carriera: v, tipo_carriera_id: v })}
            placeholder="Tipo (KORP, Professione, …)"
          />
          <p className="text-xs text-gray-500">
            Le professioni restano tier T3 in wiki. Qui associ i <strong>tier di abilità</strong> sbloccabili
            per i membri; per inserire le singole abilità in un tier usa{' '}
            <strong>Database regole → Tabelle</strong>.
          </p>
          <input
            type="number"
            step="0.01"
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            placeholder="Bonus crediti evento (carriera/KORP)"
            value={form.bonus_crediti_evento ?? 0}
            onChange={(e) => setForm({ ...form, bonus_crediti_evento: e.target.value })}
          />
          <div>
            <div className="text-xs text-gray-400 mb-2">Tier abilità sbloccabili per i membri</div>
            <SearchableSelect
              options={tierOptionsDisponibili}
              value={tierToAdd}
              onChange={(v) => {
                setTierToAdd(v);
                addTier(v);
              }}
              placeholder="Cerca tier da aggiungere…"
              minOptionsForSearch={0}
            />
            <div className="mt-2 max-h-40 overflow-y-auto border border-gray-700 rounded p-2 flex flex-wrap gap-2">
              {selectedTierRows.length === 0 ? (
                <p className="text-xs text-gray-500">Nessun tier selezionato</p>
              ) : (
                selectedTierRows.map((t) => (
                  <span
                    key={t.id}
                    className="inline-flex items-center gap-2 px-2 py-1 rounded bg-gray-800 border border-gray-700 text-sm text-gray-200"
                  >
                    <span className="text-gray-500 text-xs">{t.tipo}</span>
                    <span>{t.nome}</span>
                    <button
                      type="button"
                      onClick={() => removeTier(t.id)}
                      className="text-red-400 hover:text-red-300"
                      title="Rimuovi tier"
                    >
                      <X size={14} />
                    </button>
                  </span>
                ))
              )}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-2">
              Abilità assegnate automaticamente ai membri attivi
            </div>
            <p className="text-xs text-gray-500 mb-2">
              Es. perk sconto forgiatura (CFG MOL 0.5 con limite aura ATE/AIN). All&apos;ingresso in KORP/carriera
              vengono aggiunte senza costo; alla chiusura membership vengono rimosse.
            </p>
            <SearchableSelect
              options={abilitaOptionsDisponibili}
              value={abilitaToAdd}
              onChange={(v) => {
                setAbilitaToAdd(v);
                addAbilitaDefault(v);
              }}
              placeholder="Cerca abilità da aggiungere…"
              minOptionsForSearch={0}
            />
            <div className="mt-2 max-h-40 overflow-y-auto border border-gray-700 rounded p-2 flex flex-wrap gap-2">
              {selectedAbilitaRows.length === 0 ? (
                <p className="text-xs text-gray-500">Nessuna abilità selezionata</p>
              ) : (
                selectedAbilitaRows.map((a) => (
                  <span
                    key={a.id}
                    className="inline-flex items-center gap-2 px-2 py-1 rounded bg-gray-800 border border-gray-700 text-sm text-gray-200"
                  >
                    <span>{a.nome}</span>
                    <button
                      type="button"
                      onClick={() => removeAbilitaDefault(a.id)}
                      className="text-red-400 hover:text-red-300"
                      title="Rimuovi abilità"
                    >
                      <X size={14} />
                    </button>
                  </span>
                ))
              )}
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700">
          <EditorSaveActions
            onSave={() => onSave(form, 'save_close')}
            onSaveAndContinue={() => onSave(form, 'save_continue')}
            onCancel={onClose}
            statusMessage={statusMessage}
            statusType={statusType}
          />
        </div>
      </div>
    </div>
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

function CaricaModal({ isOpen, onClose, onSave, value, carriereOptions, statusMessage, statusType }) {
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
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-gray-900 border border-gray-700 rounded-xl max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-gray-700 flex justify-between">
          <h3 className="text-lg font-bold text-white">{form?.id ? 'Modifica' : 'Nuova'} carica</h3>
          <button type="button" onClick={onClose}><X className="text-gray-400" size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <div>
            <div className="text-xs text-gray-400 mb-2">Dipartimenti (carriere / KORP)</div>
            <SearchableSelect
              options={carriereDisponibili}
              value={carrieraToAdd}
              onChange={(v) => {
                setCarrieraToAdd(v);
                addCarriera(v);
              }}
              placeholder="Aggiungi dipartimento…"
              minOptionsForSearch={0}
            />
            <div className="mt-2 max-h-36 overflow-y-auto border border-gray-700 rounded p-2 flex flex-wrap gap-2">
              {selectedCarriereRows.length === 0 ? (
                <p className="text-xs text-gray-500">Nessun dipartimento — seleziona almeno uno.</p>
              ) : (
                selectedCarriereRows.map((c) => (
                  <span
                    key={c.id}
                    className="inline-flex items-center gap-2 px-2 py-1 rounded bg-gray-800 border border-gray-700 text-sm text-gray-200"
                  >
                    <span>{c.nome}</span>
                    <button type="button" className="text-red-400 hover:text-red-300" onClick={() => removeCarriera(c.id)}>
                      <X size={14} />
                    </button>
                  </span>
                ))
              )}
            </div>
          </div>
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            placeholder="Nome carica"
            value={form.nome || ''}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
          />
          <input
            type="number"
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            placeholder="Bonus stipendio evento"
            value={form.bonus_stipendio_evento ?? 0}
            onChange={(e) => setForm({ ...form, bonus_stipendio_evento: e.target.value })}
          />
          <input
            type="number"
            step="0.01"
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            placeholder="Bonus crediti evento (carica)"
            value={form.bonus_crediti_evento ?? 0}
            onChange={(e) => setForm({ ...form, bonus_crediti_evento: e.target.value })}
          />
          <input
            type="number"
            min={0}
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            placeholder="Bonus peso influencer InstaFame"
            value={form.bonus_peso_influencer ?? 0}
            onChange={(e) => setForm({ ...form, bonus_peso_influencer: e.target.value })}
          />
          <input
            type="number"
            className="w-32 bg-gray-800 border border-gray-700 rounded p-2 text-white"
            value={form.ordine ?? 0}
            onChange={(e) => setForm({ ...form, ordine: parseInt(e.target.value || '0', 10) })}
          />
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" checked={!!form.attiva} onChange={(e) => setForm({ ...form, attiva: e.target.checked })} />
            Attiva
          </label>
        </div>
        <div className="p-4 border-t border-gray-700">
          <EditorSaveActions
            onSave={() => onSave(form, 'save_close')}
            onCancel={onClose}
            statusMessage={statusMessage}
            statusType={statusType}
          />
        </div>
      </div>
    </div>
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
  statusMessage,
  statusType,
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
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-gray-900 border border-gray-700 rounded-xl max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-gray-700 flex justify-between">
          <h3 className="text-lg font-bold text-white">{form?.id ? 'Modifica' : 'Nuova'} appartenenza</h3>
          <button type="button" onClick={onClose}><X className="text-gray-400" size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <label className="block text-xs text-gray-400 mb-1">Personaggio</label>
          <SearchableSelect
            options={personaggiOptions}
            value={form.personaggio || null}
            onChange={(v) => setForm({ ...form, personaggio: v })}
            placeholder="Cerca personaggio (nome o giocatore)…"
          />
          <label className="block text-xs text-gray-400 mb-1">Tipo</label>
          <SearchableSelect
            options={tipi}
            value={tipoId || null}
            onChange={(v) => setForm({ ...form, tipo_carriera: v, carriera: null, carica: null })}
            placeholder="KORP o Professione…"
          />
          <label className="block text-xs text-gray-400 mb-1">Carica (opzionale)</label>
          <SearchableSelect
            options={caricheOptions}
            value={form.carica || form.carica_id || null}
            onChange={(v) => setForm({ ...form, carica: v, carriera: null, carriera_id: null })}
            placeholder="Carica militare…"
          />
          {selectedCarica && carriereDaCarica.length > 0 ? (
            <p className="text-xs text-gray-500">
              Dipartimenti di questa carica:{' '}
              <span className="text-gray-300">{carriereDaCarica.map((c) => c.nome).join(', ')}</span>
            </p>
          ) : null}
          {!form.id && selectedCarica && carriereDaCarica.length > 1 ? (
            <label className="flex items-start gap-2 p-3 rounded-lg border border-indigo-700/50 bg-indigo-950/30 text-sm text-indigo-100">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={espandiTutteCarriere}
                onChange={(e) => setEspandiTutteCarriere(e.target.checked)}
              />
              <span>
                Crea un&apos;appartenenza per <strong>ogni</strong> dipartimento della carica ({carriereDaCarica.length}).
                Lascia deselezionato per scegliere un solo dipartimento sotto.
              </span>
            </label>
          ) : null}
          <label className="block text-xs text-gray-400 mb-1">Carriera / KORP {espansioneAttiva ? '(opzionale — espansione automatica)' : ''}</label>
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
            placeholder={espansioneAttiva ? 'Opzionale se espandi tutti i dipartimenti' : 'Cerca professione o KORP…'}
            disabled={espansioneAttiva || (!tipoId && carriereFiltrate.length === 0)}
          />
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              checked={form.visibile_social !== false}
              onChange={(e) => setForm({ ...form, visibile_social: e.target.checked })}
            />
            Carica visibile sul profilo social InstaFame
          </label>
          {isKorp && !form.id && (
            <label className="flex items-start gap-2 p-3 rounded-lg border border-amber-600/50 bg-amber-950/30 text-sm text-amber-100">
              <input
                type="checkbox"
                className="mt-1"
                checked={chiudiKorpPrecedenti}
                onChange={(e) => setChiudiKorpPrecedenti(e.target.checked)}
              />
              <span>
                <strong>Molto consigliato:</strong> chiudi la KORP attiva precedente di questo personaggio
                impostando <code className="text-amber-200">data_a</code> adesso.
              </span>
            </label>
          )}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-500">Data da</label>
              <ItalianDateTimeInput
                className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white text-sm"
                value={form.data_da || ''}
                onChange={(v) => setForm({ ...form, data_da: localDateTimeToApiIso(v) })}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">Data a (vuoto = attiva)</label>
              <ItalianDateTimeInput
                className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white text-sm"
                value={form.data_a || ''}
                onChange={(v) => setForm({ ...form, data_a: localDateTimeToApiIso(v) })}
              />
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700">
          <EditorSaveActions
            onSave={() =>
              onSave(
                { ...form, chiudi_korp_precedenti: chiudiKorpPrecedenti, espandi_tutte_carriere: espandiTutteCarriere },
                'save_close',
              )
            }
            onCancel={onClose}
            statusMessage={statusMessage}
            statusType={statusType}
          />
        </div>
      </div>
    </div>
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
  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState('success');
  const [modalCarriera, setModalCarriera] = useState(null);
  const [modalCarica, setModalCarica] = useState(null);
  const [modalMembership, setModalMembership] = useState(null);
  const [filtroTipo, setFiltroTipo] = useState('');
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

  const carriereFiltered = useMemo(() => {
    if (!filtroTipo) return carriere;
    return carriere.filter((c) => c.tipo_carriera_codice === filtroTipo);
  }, [carriere, filtroTipo]);

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
      { header: 'Nome', render: (x) => <span className="font-bold">{x.nome}</span> },
      { header: 'Tipo', render: (x) => x.tipo_carriera_nome || x.tipo_carriera_codice || '—' },
      { header: 'Tier wiki', render: (x) => x.tipo || '—', align: 'center', width: 90 },
      { header: 'Bonus CR', render: (x) => Number(x.bonus_crediti_evento || 0).toFixed(2), align: 'center', width: 100 },
      {
        header: 'Tier sblocco',
        render: (x) => (x.tiers_sblocco_dettaglio?.length ?? 0),
        align: 'center',
        width: 100,
      },
      {
        header: 'Perk auto',
        render: (x) => (x.abilita_default_dettaglio?.length ?? 0),
        align: 'center',
        width: 90,
      },
    ],
    [],
  );

  const caricaColumns = useMemo(
    () => [
      { header: 'Carica', render: (x) => <span className="font-bold">{x.nome}</span> },
      {
        header: 'Dipartimenti',
        render: (x) => (x.carriere_nomi?.length ? x.carriere_nomi.join(', ') : '—'),
      },
      { header: 'Bonus CR', render: (x) => Number(x.bonus_crediti_evento || 0).toFixed(2), align: 'center', width: 100 },
      { header: 'Ordine', render: (x) => x.ordine ?? 0, align: 'center', width: 80 },
      {
        header: 'Attiva',
        render: (x) => (x.attiva === false ? 'No' : 'Sì'),
        align: 'center',
        width: 80,
      },
    ],
    [],
  );

  const membershipColumns = useMemo(
    () => [
      { header: 'PG', render: (x) => x.personaggio_nome || `#${x.personaggio}` },
      { header: 'Carriera', render: (x) => x.carriera_nome || '—' },
      { header: 'Tipo', render: (x) => x.tipo_carriera_codice || '—', width: 110 },
      { header: 'Carica', render: (x) => x.carica_nome || '—' },
      {
        header: 'Social',
        render: (x) => (x.visibile_social === false ? 'Nascosta' : 'Visibile'),
        align: 'center',
        width: 90,
      },
      {
        header: 'Stato',
        render: (x) => (x.data_a ? 'Chiusa' : 'Attiva'),
        align: 'center',
        width: 90,
      },
    ],
    [],
  );

  const saveCarriera = async (form, mode) => {
    try {
      const payload = {
        nome: form.nome,
        descrizione: form.descrizione || '',
        tipo: form.tipo || 'T3',
        tipo_carriera: form.tipo_carriera || form.tipo_carriera_id,
        bonus_crediti_evento: form.bonus_crediti_evento ?? 0,
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
    }
  };

  const saveCarica = async (form, mode) => {
    try {
      if (!form.carriere_ids?.length) {
        setStatusMessage('Seleziona almeno un dipartimento per la carica.');
        setStatusType('error');
        return;
      }
      const payload = {
        carriere_ids: form.carriere_ids,
        nome: form.nome,
        bonus_stipendio_evento: form.bonus_stipendio_evento ?? 0,
        bonus_crediti_evento: form.bonus_crediti_evento ?? 0,
        bonus_peso_influencer: form.bonus_peso_influencer ?? 0,
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
    }
  };

  if (loading && !carriere.length) {
    return <div className="p-8 text-center text-gray-400">Caricamento carriere e KORP…</div>;
  }

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      <div className="p-4 border-b border-gray-800 flex flex-wrap gap-2 items-center">
        <h2 className="text-xl font-bold mr-4">Carriere, KORP e cariche</h2>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm ${
              tab === id ? 'bg-violet-600' : 'bg-gray-800 hover:bg-gray-700'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
        {tab === 'org' && (
          <select
            className="ml-auto bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
            value={filtroTipo}
            onChange={(e) => setFiltroTipo(e.target.value)}
          >
            <option value="">Tutti i tipi</option>
            {tipi.map((t) => (
              <option key={t.codice} value={t.codice}>{t.nome}</option>
            ))}
          </select>
        )}
      </div>

      {statusMessage && (
        <div className={`mx-4 mt-2 px-3 py-2 rounded text-sm ${statusType === 'error' ? 'bg-red-900/50 text-red-200' : 'bg-green-900/40 text-green-200'}`}>
          {statusMessage}
        </div>
      )}

      <div className="flex-1 min-h-0 p-4 h-full">
        {tab === 'org' && (
          <div className="h-full">
          <MasterGenericList
            title="Carriere e KORP"
            items={carriereFiltered}
            columns={carrieraColumns}
            loading={loading}
            persistKey="staff-carriere-korps-org"
            addLabel="Nuova carriera"
            emptyMessage="Nessuna carriera trovata."
            onAdd={() =>
              setModalCarriera({
                tipo: 'T3',
                tipo_carriera: tipi.find((t) => t.codice === 'professione')?.id,
                tiers_sblocco_ids: [],
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
          <div className="h-full">
          <MasterGenericList
            title="Cariche"
            items={cariche}
            columns={caricaColumns}
            loading={loading}
            persistKey="staff-carriere-korps-cariche"
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
          <div className="h-full">
          <MasterGenericList
            title="Appartenenze PG"
            items={memberships}
            columns={membershipColumns}
            loading={loading}
            persistKey="staff-carriere-korps-membership"
            addLabel="Nuova appartenenza"
            emptyMessage="Nessuna appartenenza registrata."
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
        statusMessage={statusMessage}
        statusType={statusType}
      />
      <CaricaModal
        isOpen={!!modalCarica}
        onClose={() => setModalCarica(null)}
        onSave={saveCarica}
        value={modalCarica}
        carriereOptions={carriereSelectOptions}
        statusMessage={statusMessage}
        statusType={statusType}
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
        statusMessage={statusMessage}
        statusType={statusType}
      />
    </div>
  );
}
