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
} from '../../api';

const TABS = [
  { id: 'org', label: 'Carriere / KORP', icon: Briefcase },
  { id: 'cariche', label: 'Cariche', icon: Shield },
  { id: 'membership', label: 'Appartenenze', icon: Users },
];

function CarrieraModal({ isOpen, onClose, onSave, value, tipi, tiersSelezionabili, statusMessage, statusType }) {
  const [form, setForm] = useState(value || {});
  useEffect(() => {
    const base = value || {};
    const ids = base.tiers_sblocco_dettaglio
      ? base.tiers_sblocco_dettaglio.map((t) => t.id)
      : base.tiers_sblocco_ids || [];
    setForm({ ...base, tiers_sblocco_ids: ids });
  }, [value]);
  if (!isOpen) return null;

  const toggleTier = (tierId) => {
    const sid = String(tierId);
    const current = new Set((form.tiers_sblocco_ids || []).map(String));
    if (current.has(sid)) current.delete(sid);
    else current.add(sid);
    setForm({ ...form, tiers_sblocco_ids: [...current].map((x) => Number(x)) });
  };
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
            <div className="max-h-40 overflow-y-auto border border-gray-700 rounded p-2 space-y-1">
              {tiersSelezionabili.length === 0 ? (
                <p className="text-xs text-gray-500">Nessun tier disponibile</p>
              ) : (
                tiersSelezionabili.map((t) => (
                  <label key={t.id} className="flex items-center gap-2 text-sm text-gray-200">
                    <input
                      type="checkbox"
                      checked={(form.tiers_sblocco_ids || []).map(String).includes(String(t.id))}
                      onChange={() => toggleTier(t.id)}
                    />
                    <span className="text-gray-500 text-xs">{t.tipo}</span>
                    {t.nome}
                  </label>
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

function CaricaModal({ isOpen, onClose, onSave, value, carriereOptions, statusMessage, statusType }) {
  const [form, setForm] = useState(value || {});
  useEffect(() => setForm(value || {}), [value]);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-gray-900 border border-gray-700 rounded-xl">
        <div className="p-4 border-b border-gray-700 flex justify-between">
          <h3 className="text-lg font-bold text-white">{form?.id ? 'Modifica' : 'Nuova'} carica</h3>
          <button type="button" onClick={onClose}><X className="text-gray-400" size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <label className="block text-xs text-gray-400 mb-1">Carriera / KORP</label>
          <SearchableSelect
            options={carriereOptions}
            value={form.carriera || form.carriera_id || null}
            onChange={(v) => setForm({ ...form, carriera: v, carriera_id: v })}
            placeholder="Cerca carriera o KORP…"
          />
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
          <EditorSaveActions onSave={() => onSave(form, 'save_close')} onCancel={onClose} statusMessage={statusMessage} statusType={statusType} />
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
  useEffect(() => {
    setForm(value || {});
    setChiudiKorpPrecedenti(true);
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
    if (!carrieraId) return [];
    return cariche.filter((c) => String(c.carriera) === String(carrieraId));
  }, [carrieraId, cariche]);

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
          <label className="block text-xs text-gray-400 mb-1">Carriera / KORP</label>
          <SearchableSelect
            options={carriereFiltrate}
            value={carrieraId || null}
            onChange={(v) => {
              const row = carriereOptions.find((c) => String(c.id) === String(v));
              setForm({
                ...form,
                carriera: v,
                tipo_carriera: row?.tipo_carriera || form.tipo_carriera,
                carica: null,
              });
            }}
            placeholder="Cerca professione o KORP…"
            disabled={!tipoId && carriereFiltrate.length === 0}
          />
          <label className="block text-xs text-gray-400 mb-1">Carica (opzionale)</label>
          <SearchableSelect
            options={caricheOptions}
            value={form.carica || form.carica_id || null}
            onChange={(v) => setForm({ ...form, carica: v })}
            placeholder="Carica nella carriera…"
            disabled={!carrieraId}
          />
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
              <input
                type="datetime-local"
                className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white text-sm"
                value={form.data_da ? form.data_da.slice(0, 16) : ''}
                onChange={(e) => setForm({ ...form, data_da: e.target.value ? new Date(e.target.value).toISOString() : null })}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">Data a (vuoto = attiva)</label>
              <input
                type="datetime-local"
                className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white text-sm"
                value={form.data_a ? form.data_a.slice(0, 16) : ''}
                onChange={(e) => setForm({ ...form, data_a: e.target.value ? new Date(e.target.value).toISOString() : null })}
              />
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700">
          <EditorSaveActions
            onSave={() => onSave({ ...form, chiudi_korp_precedenti: chiudiKorpPrecedenti }, 'save_close')}
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

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [t, c, ch, m, p, tiers] = await Promise.all([
        staffGetTipiCarriera(onLogout),
        staffGetCarriere(onLogout),
        staffGetCariche(onLogout),
        staffGetCarriereMemberships(onLogout),
        getPersonaggiEditList(onLogout),
        staffGetCarrieraTiersSelezionabili(onLogout),
      ]);
      setTipi(Array.isArray(t) ? t : []);
      setCarriere(Array.isArray(c) ? c : []);
      setCariche(Array.isArray(ch) ? ch : []);
      setMemberships(Array.isArray(m) ? m : []);
      setPersonaggi(Array.isArray(p) ? p : []);
      setTiersSelezionabili(Array.isArray(tiers) ? tiers : []);
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
    ],
    [],
  );

  const caricaColumns = useMemo(
    () => [
      { header: 'Carriera', render: (x) => x.carriera_nome || '—' },
      { header: 'Carica', render: (x) => <span className="font-bold">{x.nome}</span> },
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
      const payload = {
        carriera: form.carriera || form.carriera_id,
        nome: form.nome,
        bonus_stipendio_evento: form.bonus_stipendio_evento ?? 0,
        bonus_crediti_evento: form.bonus_crediti_evento ?? 0,
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
      if (!form.personaggio || !(form.carriera || form.carriera_id) || !(form.tipo_carriera || form.tipo_carriera_id)) {
        setStatusMessage('Compila personaggio, tipo e carriera/KORP.');
        setStatusType('error');
        return;
      }
      const payload = {
        personaggio: form.personaggio,
        carriera: form.carriera || form.carriera_id,
        tipo_carriera: form.tipo_carriera || form.tipo_carriera_id,
        carica: form.carica || form.carica_id || null,
        data_da: form.data_da || undefined,
        data_a: form.data_a || null,
      };
      if (form.id) {
        await staffUpdateCarriereMembership(form.id, payload, onLogout);
      } else {
        await staffCreateCarriereMembership(
          { ...payload, chiudi_korp_precedenti: !!form.chiudi_korp_precedenti },
          onLogout,
        );
      }
      setStatusMessage('Appartenenza salvata');
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
            onEdit={(item) => setModalCarica({ ...item, carriera: item.carriera })}
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
