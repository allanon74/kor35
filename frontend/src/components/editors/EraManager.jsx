import React, { useEffect, useMemo, useState, memo } from 'react';
import { ArrowLeft, X } from 'lucide-react';
import MasterGenericList from './MasterGenericList';
import {
  staffGetEre,
  staffCreateEra,
  staffUpdateEra,
  staffDeleteEra,
  staffGetPrefetture,
  staffGetRegioni,
  staffCreateRegione,
  staffUpdateRegione,
  staffDeleteRegione,
  staffCreatePrefettura,
  staffUpdatePrefettura,
  staffDeletePrefettura,
} from '../../api';

const EraFormModal = ({ isOpen, onClose, onSave, value }) => {
  const [form, setForm] = useState(value || {});
  useEffect(() => setForm(value || {}), [value]);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-gray-900 border border-gray-700 rounded-xl">
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">{form?.id ? 'Modifica Era' : 'Nuova Era'}</h3>
          <button onClick={onClose}><X className="text-gray-400" size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <input className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" placeholder="Nome" value={form.nome || ''} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
          <input className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" placeholder="Abbreviazione (opzionale)" value={form.abbreviazione || ''} onChange={(e) => setForm({ ...form, abbreviazione: e.target.value })} />
          <input className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" placeholder="Descrizione breve" value={form.descrizione_breve || ''} onChange={(e) => setForm({ ...form, descrizione_breve: e.target.value })} />
          <textarea className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white min-h-[110px]" placeholder="Descrizione" value={form.descrizione || ''} onChange={(e) => setForm({ ...form, descrizione: e.target.value })} />
          <div className="flex gap-2">
            <input type="number" className="w-32 bg-gray-800 border border-gray-700 rounded p-2 text-white" value={form.ordine ?? 0} onChange={(e) => setForm({ ...form, ordine: parseInt(e.target.value || '0', 10) })} />
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input type="checkbox" checked={!!form.attiva} onChange={(e) => setForm({ ...form, attiva: e.target.checked })} />
              Era attiva
            </label>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700">
          <button onClick={() => onSave(form)} className="w-full bg-indigo-600 hover:bg-indigo-500 rounded p-2 text-white font-bold">Salva</button>
        </div>
      </div>
    </div>
  );
};

const RegioneFormModal = ({ isOpen, onClose, onSave, value }) => {
  const [form, setForm] = useState(value || {});
  useEffect(() => setForm(value || {}), [value]);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-gray-900 border border-gray-700 rounded-xl">
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">{form?.id ? 'Modifica Regione' : 'Nuova Regione'}</h3>
          <button onClick={onClose}><X className="text-gray-400" size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <input className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" placeholder="Nome regione" value={form.nome || ''} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
          <input className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" placeholder="Sigla (opzionale)" value={form.sigla || ''} onChange={(e) => setForm({ ...form, sigla: e.target.value })} />
          <textarea className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white min-h-[110px]" placeholder="Descrizione" value={form.descrizione || ''} onChange={(e) => setForm({ ...form, descrizione: e.target.value })} />
          <div className="flex gap-2">
            <input type="number" className="w-32 bg-gray-800 border border-gray-700 rounded p-2 text-white" value={form.ordine ?? 0} onChange={(e) => setForm({ ...form, ordine: parseInt(e.target.value || '0', 10) })} />
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input type="checkbox" checked={!!form.attiva} onChange={(e) => setForm({ ...form, attiva: e.target.checked })} />
              Regione attiva
            </label>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700">
          <button onClick={() => onSave(form)} className="w-full bg-indigo-600 hover:bg-indigo-500 rounded p-2 text-white font-bold">Salva</button>
        </div>
      </div>
    </div>
  );
};

const PrefetturaFormModal = ({ isOpen, onClose, onSave, value, ere, regioni }) => {
  const [form, setForm] = useState(value || {});
  useEffect(() => setForm(value || {}), [value]);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-xl bg-gray-900 border border-gray-700 rounded-xl">
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">{form?.id ? 'Modifica Prefettura' : 'Nuova Prefettura'}</h3>
          <button onClick={onClose}><X className="text-gray-400" size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <select className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" value={form.era || ''} onChange={(e) => setForm({ ...form, era: e.target.value })}>
            <option value="">Seleziona Era</option>
            {ere.map((era) => <option key={era.id} value={era.id}>{era.nome}</option>)}
          </select>
          <select className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" value={form.regione || ''} onChange={(e) => setForm({ ...form, regione: e.target.value || null })}>
            <option value="">Regione (opzionale)</option>
            {regioni.map((r) => <option key={r.id} value={r.id}>{r.sigla ? `${r.sigla} - ${r.nome}` : r.nome}</option>)}
          </select>
          <input className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white" placeholder="Nome prefettura" value={form.nome || ''} onChange={(e) => setForm({ ...form, nome: e.target.value })} />
          <textarea className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white min-h-[110px]" placeholder="Descrizione" value={form.descrizione || ''} onChange={(e) => setForm({ ...form, descrizione: e.target.value })} />
          <input type="number" className="w-32 bg-gray-800 border border-gray-700 rounded p-2 text-white" value={form.ordine ?? 0} onChange={(e) => setForm({ ...form, ordine: parseInt(e.target.value || '0', 10) })} />
        </div>
        <div className="p-4 border-t border-gray-700">
          <button onClick={() => onSave(form)} className="w-full bg-indigo-600 hover:bg-indigo-500 rounded p-2 text-white font-bold">Salva</button>
        </div>
      </div>
    </div>
  );
};

const EraManager = ({ onLogout, onBack }) => {
  const [ere, setEre] = useState([]);
  const [regioni, setRegioni] = useState([]);
  const [prefetture, setPrefetture] = useState([]);
  const [activeTab, setActiveTab] = useState('ere');
  const [editingEra, setEditingEra] = useState(null);
  const [editingRegione, setEditingRegione] = useState(null);
  const [editingPref, setEditingPref] = useState(null);

  const load = async () => {
    const [ereData, prefData, regioniData] = await Promise.all([
      staffGetEre(onLogout),
      staffGetPrefetture(onLogout),
      staffGetRegioni(onLogout),
    ]);
    setEre(Array.isArray(ereData) ? ereData : []);
    setPrefetture(Array.isArray(prefData) ? prefData : []);
    setRegioni(Array.isArray(regioniData) ? regioniData : []);
  };

  useEffect(() => { load(); }, []);

  const eraColumns = useMemo(() => [
    { header: 'Nome', render: (x) => <span className="font-bold">{x.nome}</span> },
    { header: 'Abbr.', render: (x) => x.abbreviazione || '-' },
    { header: 'Ordine', render: (x) => x.ordine ?? 0, align: 'center', width: 90 },
    { header: 'Attiva', render: (x) => (x.attiva ? 'Si' : 'No'), align: 'center', width: 90 },
  ], []);

  const prefColumns = useMemo(() => [
    { header: 'Nome', render: (x) => <span className="font-bold">{x.nome}</span> },
    { header: 'Era', render: (x) => x.era_nome || '-' },
    { header: 'Reg.', render: (x) => x.regione_sigla || '-' },
    { header: 'Ordine', render: (x) => x.ordine ?? 0, align: 'center', width: 90 },
  ], []);

  const regioneColumns = useMemo(() => [
    { header: 'Nome', render: (x) => <span className="font-bold">{x.nome}</span> },
    { header: 'Sigla', render: (x) => x.sigla || '-' },
    { header: 'Ordine', render: (x) => x.ordine ?? 0, align: 'center', width: 90 },
    { header: 'Attiva', render: (x) => (x.attiva ? 'Si' : 'No'), align: 'center', width: 90 },
  ], []);

  return (
    <div className="h-full p-4 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button onClick={onBack} className="px-3 py-2 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 flex items-center gap-2 w-full sm:w-auto justify-center sm:justify-start">
          <ArrowLeft size={16} /> Indietro
        </button>
        <div className="text-gray-400 text-sm text-center sm:text-right">Gestione anagrafiche Era / Regione / Prefettura</div>
      </div>

      <div className="bg-gray-900/70 border border-gray-700 rounded-xl p-2">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <button
            onClick={() => setActiveTab('ere')}
            className={`px-3 py-2 rounded-lg text-sm font-bold transition-colors ${activeTab === 'ere' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            Ere
          </button>
          <button
            onClick={() => setActiveTab('regioni')}
            className={`px-3 py-2 rounded-lg text-sm font-bold transition-colors ${activeTab === 'regioni' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            Regioni
          </button>
          <button
            onClick={() => setActiveTab('prefetture')}
            className={`px-3 py-2 rounded-lg text-sm font-bold transition-colors ${activeTab === 'prefetture' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            Prefetture
          </button>
        </div>
      </div>

      <div className="h-[calc(100%-116px)]">
        {activeTab === 'ere' && (
          <MasterGenericList
            title="Ere"
            items={ere}
            columns={eraColumns}
            onAdd={() => setEditingEra({ nome: '', abbreviazione: '', descrizione_breve: '', descrizione: '', ordine: 0, attiva: true })}
            onEdit={(item) => setEditingEra(item)}
            onDelete={async (id) => {
              await staffDeleteEra(id, onLogout);
              await load();
            }}
            addLabel="Nuova Era"
          />
        )}

        {activeTab === 'regioni' && (
          <MasterGenericList
            title="Regioni"
            items={regioni}
            columns={regioneColumns}
            onAdd={() => setEditingRegione({ nome: '', sigla: '', descrizione: '', ordine: 0, attiva: true })}
            onEdit={(item) => setEditingRegione(item)}
            onDelete={async (id) => {
              await staffDeleteRegione(id, onLogout);
              await load();
            }}
            addLabel="Nuova Regione"
          />
        )}

        {activeTab === 'prefetture' && (
          <MasterGenericList
            title="Prefetture"
            items={prefetture}
            columns={prefColumns}
            onAdd={() => setEditingPref({ era: '', regione: '', nome: '', descrizione: '', ordine: 0 })}
            onEdit={(item) => setEditingPref(item)}
            onDelete={async (id) => {
              await staffDeletePrefettura(id, onLogout);
              await load();
            }}
            addLabel="Nuova Prefettura"
            filterConfig={[
              {
                key: 'era',
                label: 'Era',
                options: ere.map((e) => ({ id: e.id, label: e.nome })),
              },
              {
                key: 'regione',
                label: 'Regione',
                options: regioni.map((r) => ({ id: r.id, label: r.sigla ? `${r.sigla} - ${r.nome}` : r.nome })),
              },
            ]}
          />
        )}
      </div>

      <EraFormModal
        isOpen={!!editingEra}
        value={editingEra}
        onClose={() => setEditingEra(null)}
        onSave={async (form) => {
          if (!form.nome?.trim()) return alert('Il nome era è obbligatorio');
          if (form.id) await staffUpdateEra(form.id, form, onLogout);
          else await staffCreateEra(form, onLogout);
          setEditingEra(null);
          await load();
        }}
      />

      <PrefetturaFormModal
        isOpen={!!editingPref}
        value={editingPref}
        ere={ere}
        regioni={regioni}
        onClose={() => setEditingPref(null)}
        onSave={async (form) => {
          if (!form.era) return alert("Seleziona un'era");
          if (!form.nome?.trim()) return alert('Il nome prefettura è obbligatorio');
          const payload = {
            ...form,
            era: parseInt(form.era, 10),
            regione: form.regione ? parseInt(form.regione, 10) : null,
          };
          if (form.id) await staffUpdatePrefettura(form.id, payload, onLogout);
          else await staffCreatePrefettura(payload, onLogout);
          setEditingPref(null);
          await load();
        }}
      />

      <RegioneFormModal
        isOpen={!!editingRegione}
        value={editingRegione}
        onClose={() => setEditingRegione(null)}
        onSave={async (form) => {
          if (!form.nome?.trim()) return alert('Il nome regione è obbligatorio');
          if (form.id) await staffUpdateRegione(form.id, form, onLogout);
          else await staffCreateRegione(form, onLogout);
          setEditingRegione(null);
          await load();
        }}
      />
    </div>
  );
};

export default memo(EraManager);
