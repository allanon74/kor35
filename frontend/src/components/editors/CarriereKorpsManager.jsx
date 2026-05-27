import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { X, Users, Briefcase, Shield } from 'lucide-react';
import MasterGenericList from './MasterGenericList';
import EditorSaveActions from './EditorSaveActions';
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
  getPersonaggiEditList,
} from '../../api';

const TABS = [
  { id: 'org', label: 'Carriere / KORP', icon: Briefcase },
  { id: 'cariche', label: 'Cariche', icon: Shield },
  { id: 'membership', label: 'Appartenenze', icon: Users },
];

function CarrieraModal({ isOpen, onClose, onSave, value, tipi, statusMessage, statusType }) {
  const [form, setForm] = useState(value || {});
  useEffect(() => setForm(value || {}), [value]);
  if (!isOpen) return null;
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
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            value={form.tipo_carriera_id || ''}
            onChange={(e) => setForm({ ...form, tipo_carriera_id: e.target.value })}
          >
            <option value="">Tipo carriera</option>
            {tipi.map((t) => (
              <option key={t.id} value={t.id}>{t.nome}</option>
            ))}
          </select>
          <p className="text-xs text-gray-500">
            Le professioni restano tier T3 (wiki invariata). Tipo «KORP» per le corps.
          </p>
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

function CaricaModal({ isOpen, onClose, onSave, value, carriere, statusMessage, statusType }) {
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
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            value={form.carriera_id || ''}
            onChange={(e) => setForm({ ...form, carriera_id: e.target.value })}
          >
            <option value="">Carriera / KORP</option>
            {carriere.map((c) => (
              <option key={c.id} value={c.id}>
                [{c.tipo_carriera_codice}] {c.nome}
              </option>
            ))}
          </select>
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
  isOpen, onClose, onSave, value, carriere, tipi, personaggi, statusMessage, statusType,
}) {
  const [form, setForm] = useState(value || {});
  const [chiudiKorpPrecedenti, setChiudiKorpPrecedenti] = useState(true);
  useEffect(() => {
    setForm(value || {});
    setChiudiKorpPrecedenti(true);
  }, [value]);

  const selectedTipo = useMemo(
    () => tipi.find((t) => String(t.id) === String(form.tipo_carriera_id)),
    [tipi, form.tipo_carriera_id],
  );
  const isKorp = selectedTipo?.codice === 'korp';

  const carriereFiltrate = useMemo(() => {
    if (!form.tipo_carriera_id) return carriere;
    return carriere.filter((c) => String(c.tipo_carriera_id) === String(form.tipo_carriera_id));
  }, [carriere, form.tipo_carriera_id]);

  const caricheOptions = useMemo(() => {
    if (!form.carriera_id) return [];
    return (form._cariche || []).filter((c) => String(c.carriera_id) === String(form.carriera_id));
  }, [form.carriera_id, form._cariche]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-gray-900 border border-gray-700 rounded-xl max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-gray-700 flex justify-between">
          <h3 className="text-lg font-bold text-white">{form?.id ? 'Modifica' : 'Nuova'} appartenenza</h3>
          <button type="button" onClick={onClose}><X className="text-gray-400" size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            value={form.personaggio || ''}
            onChange={(e) => setForm({ ...form, personaggio: e.target.value })}
          >
            <option value="">Personaggio</option>
            {personaggi.map((p) => (
              <option key={p.id} value={p.id}>{p.nome}</option>
            ))}
          </select>
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            value={form.tipo_carriera_id || ''}
            onChange={(e) => setForm({ ...form, tipo_carriera_id: e.target.value, carriera_id: '', carica_id: '' })}
          >
            <option value="">Tipo</option>
            {tipi.map((t) => (
              <option key={t.id} value={t.id}>{t.nome}</option>
            ))}
          </select>
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            value={form.carriera_id || ''}
            onChange={(e) => setForm({ ...form, carriera_id: e.target.value, carica_id: '' })}
          >
            <option value="">Carriera / KORP</option>
            {carriereFiltrate.map((c) => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </select>
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            value={form.carica_id || ''}
            onChange={(e) => setForm({ ...form, carica_id: e.target.value || null })}
          >
            <option value="">Carica (opzionale)</option>
            {caricheOptions.map((c) => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </select>
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

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [t, c, ch, m, p] = await Promise.all([
        staffGetTipiCarriera(onLogout),
        staffGetCarriere(onLogout),
        staffGetCariche(onLogout),
        staffGetCarriereMemberships(onLogout),
        getPersonaggiEditList(onLogout),
      ]);
      setTipi(Array.isArray(t) ? t : []);
      setCarriere(Array.isArray(c) ? c : []);
      setCariche(Array.isArray(ch) ? ch : []);
      setMemberships(Array.isArray(m) ? m : []);
      setPersonaggi(Array.isArray(p) ? p : []);
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

  const saveCarriera = async (form, mode) => {
    try {
      const payload = {
        nome: form.nome,
        descrizione: form.descrizione || '',
        tipo: form.tipo || 'T3',
        tipo_carriera_id: form.tipo_carriera_id,
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
        carriera_id: form.carriera_id,
        nome: form.nome,
        bonus_stipendio_evento: form.bonus_stipendio_evento ?? 0,
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
      const payload = {
        personaggio: form.personaggio,
        carriera_id: form.carriera_id,
        tipo_carriera_id: form.tipo_carriera_id,
        carica_id: form.carica_id || null,
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

      <div className="flex-1 overflow-auto p-4">
        {tab === 'org' && (
          <MasterGenericList
            items={carriereFiltered}
            columns={[
              { key: 'nome', label: 'Nome' },
              { key: 'tipo_carriera_nome', label: 'Tipo' },
              { key: 'tipo', label: 'Tier wiki' },
            ]}
            onAdd={() => setModalCarriera({ tipo: 'T3', tipo_carriera_id: tipi.find((t) => t.codice === 'professione')?.id })}
            onEdit={(item) => setModalCarriera({ ...item, tipo_carriera_id: item.tipo_carriera_id || tipi.find((t) => t.codice === item.tipo_carriera_codice)?.id })}
            onDelete={async (item) => {
              if (!window.confirm(`Eliminare "${item.nome}"?`)) return;
              await staffDeleteCarriera(item.id, onLogout);
              await loadAll();
            }}
          />
        )}
        {tab === 'cariche' && (
          <MasterGenericList
            items={cariche}
            columns={[
              { key: 'carriera_nome', label: 'Carriera' },
              { key: 'nome', label: 'Carica' },
              { key: 'ordine', label: 'Ordine' },
            ]}
            onAdd={() => setModalCarica({ attiva: true, ordine: 0 })}
            onEdit={(item) => setModalCarica({ ...item, carriera_id: item.carriera })}
            onDelete={async (item) => {
              if (!window.confirm(`Eliminare carica "${item.nome}"?`)) return;
              await staffDeleteCarica(item.id, onLogout);
              await loadAll();
            }}
          />
        )}
        {tab === 'membership' && (
          <MasterGenericList
            items={memberships}
            columns={[
              { key: 'personaggio_nome', label: 'PG' },
              { key: 'carriera_nome', label: 'Carriera' },
              { key: 'tipo_carriera_codice', label: 'Tipo' },
              { key: 'carica_nome', label: 'Carica' },
            ]}
            onAdd={() => setModalMembership({ _cariche: cariche })}
            onEdit={(item) => setModalMembership({
              ...item,
              personaggio: item.personaggio,
              carriera_id: item.carriera,
              tipo_carriera_id: item.tipo_carriera,
              carica_id: item.carica,
              _cariche: cariche,
            })}
            onDelete={async (item) => {
              if (!window.confirm('Eliminare questa appartenenza?')) return;
              await staffDeleteCarriereMembership(item.id, onLogout);
              await loadAll();
            }}
          />
        )}
      </div>

      <CarrieraModal
        isOpen={!!modalCarriera}
        onClose={() => setModalCarriera(null)}
        onSave={saveCarriera}
        value={modalCarriera}
        tipi={tipi}
        statusMessage={statusMessage}
        statusType={statusType}
      />
      <CaricaModal
        isOpen={!!modalCarica}
        onClose={() => setModalCarica(null)}
        onSave={saveCarica}
        value={modalCarica}
        carriere={carriere}
        statusMessage={statusMessage}
        statusType={statusType}
      />
      <MembershipModal
        isOpen={!!modalMembership}
        onClose={() => setModalMembership(null)}
        onSave={saveMembership}
        value={modalMembership}
        carriere={carriere}
        tipi={tipi}
        personaggi={personaggi}
        statusMessage={statusMessage}
        statusType={statusType}
      />
    </div>
  );
}
