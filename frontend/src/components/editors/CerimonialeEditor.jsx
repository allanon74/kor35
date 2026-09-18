import React, { useState, useMemo } from 'react';
import { useCharacter } from '../CharacterContext';
import { staffUpdateCerimoniale, staffCreateCerimoniale } from '../../api';
import CharacteristicInline from './inlines/CharacteristicInline';
import RichTextEditor from '../RichTextEditor';
import EditorSaveActions from './EditorSaveActions';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';
import CatalogoAccademiaFlags from './CatalogoAccademiaFlags';
import { staffEditorShellClass, StaffEditorHeader } from '../../staff/StaffToolShell';

const MATTONI_PER_LIVELLO_CERIMONIALE = 5;
const livelloSuggeritoCerimoniale = (totaleMattoni) =>
  Math.floor(Math.max(0, Number(totaleMattoni) || 0) / MATTONI_PER_LIVELLO_CERIMONIALE);

// Aggiunto onCancel e onSave ai props
const CerimonialeEditor = ({ onBack, onCancel, onSave, onLogout, initialData = null }) => {
  const { punteggiList } = useCharacter();
  
  // FIX: Uniamo initialData ai default per non perdere i campi non presenti nella proposta
  const defaultData = {
    nome: '', testo: '', formula_attacco: '',
    aura_richiesta: null,
    prerequisiti: '',
    svolgimento: '',
    effetto: '',
    liv: 1,
    mattoni_generici: 0,
    non_acquistabile: false,
    escluso_negozio_ufficiale: false,
    non_vendibile: false,
    componenti: []
  };

  const [formData, setFormData] = useState({ ...defaultData, ...initialData });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState({ type: 'success', message: '' });

  const totaleSpecifici = useMemo(
    () => (formData.componenti || []).reduce((acc, c) => acc + (Number(c.valore) || 0), 0),
    [formData.componenti],
  );
  const mattoniGenerici = Number(formData.mattoni_generici) || 0;
  const totaleMattoniMinimi = totaleSpecifici + mattoniGenerici;
  const livelloSuggerito = livelloSuggeritoCerimoniale(totaleMattoniMinimi);

  // Gestione alias per chiusura
  const handleClose = onCancel || onBack;

  const updateInline = (key, index, field, value) => {
    const newList = [...(formData[key] || [])]; // Protezione array vuoto
    newList[index] = { ...newList[index], [field]: value };
    setFormData({ ...formData, [key]: newList });
  };

  const handleSave = async (mode = 'save_close') => {
    try {
      setSaving(true);
      const dataToSend = { 
        ...formData,
        liv: Number(formData.liv) || 1,
        mattoni_generici: mattoniGenerici,
        aura_richiesta: formData.aura_richiesta?.id || formData.aura_richiesta || null
      };

      if (onSave) {
        // MODALITÀ APPROVAZIONE PROPOSTA
        // Passiamo i dati al padre (StaffProposalTab) che gestirà la chiamata API di approvazione
        await onSave(dataToSend);
      } else {
        // MODALITÀ EDITOR STANDARD
        const isSaveAsNew = mode === 'save_as_new';
        const isExisting = !!formData.id && !isSaveAsNew;
        const saved = isExisting
          ? await staffUpdateCerimoniale(formData.id, dataToSend, onLogout)
          : await staffCreateCerimoniale(dataToSend, onLogout);
        const recordName = saved?.nome || dataToSend.nome || 'Record';
        if (mode === 'save_as_new') setStatus({ type: 'success', message: `Nuovo record "${recordName}" inserito.` });
        if (mode === 'save_continue') setStatus({ type: 'success', message: `"${recordName}" salvato.` });
        if (mode === 'save_new_blank') {
          setFormData({ ...defaultData });
          setStatus({ type: 'success', message: `"${recordName}" salvato. Pronto per un nuovo inserimento.` });
        }
        if (mode === 'save_close' && handleClose) handleClose();
        if (mode !== 'save_close' && mode !== 'save_new_blank' && saved?.id) {
          setFormData((prev) => ({ ...prev, ...saved }));
        }
      }
    } catch (e) { 
        console.error(e);
        setStatus({ type: 'error', message: `Errore salvataggio: ${e.message || 'Errore sconosciuto'}` });
    } finally {
        setSaving(false);
    }
  };

  return (
    <div className={`${staffEditorShellClass} max-w-7xl`}>
      <StaffEditorHeader
        title={formData.id ? `Edit Cerimoniale: ${formData.nome}` : 'Nuovo Cerimoniale'}
        titleClassName="text-amber-400"
        actions={(
          <EditorSaveActions
            onSave={() => handleSave('save_close')}
            onSaveAndContinue={onSave ? null : () => handleSave('save_continue')}
            onSaveAsNew={onSave || !formData.id ? null : () => handleSave('save_as_new')}
            onSaveAndNew={onSave ? null : () => handleSave('save_new_blank')}
            onCancel={handleClose}
            saving={saving}
            saveLabel={onSave ? 'Approva e crea' : 'Salva'}
            statusMessage={status.message}
            statusType={status.type}
          />
        )}
      />

      <div className="bg-gray-900/40 p-5 rounded-xl border border-gray-700/50 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Select label="Aura" value={formData.aura_richiesta?.id || formData.aura_richiesta} 
                    options={punteggiList.filter(p => p.tipo === 'AU')} 
                    onChange={v => setFormData({...formData, aura_richiesta: v ? parseInt(v, 10) : null})} />
            <div className="md:col-span-2">
                <Input label="Nome Cerimoniale" value={formData.nome} onChange={v => setFormData({...formData, nome: v})} />
            </div>
            <Input
              label="Livello (liv)"
              type="number"
              value={formData.liv}
              onChange={v => setFormData({...formData, liv: parseInt(v, 10) || 1})}
            />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="w-full text-left">
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">
              Livello suggerito
            </label>
            <div className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white shadow-inner flex justify-between">
              <span className="font-bold">{livelloSuggerito}</span>
              <span className="text-gray-500 text-xs">mattoni÷{MATTONI_PER_LIVELLO_CERIMONIALE}</span>
            </div>
          </div>
          <div className="w-full text-left">
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">
              Totale mattoni minimi
            </label>
            <div className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white shadow-inner flex justify-between">
              <span className="font-bold">{totaleMattoniMinimi}</span>
              <span className="text-gray-500 text-xs">{totaleSpecifici} + {mattoniGenerici} gen.</span>
            </div>
          </div>
          <Input
            label="Mattoni generici"
            type="number"
            value={formData.mattoni_generici}
            onChange={v => setFormData({...formData, mattoni_generici: Math.max(0, parseInt(v, 10) || 0)})}
          />
        </div>
        <div className="space-y-2">
          <label className="text-[10px] font-black uppercase text-gray-400 tracking-widest cursor-pointer flex items-center gap-2 justify-end">
            <input
              type="checkbox"
              checked={!!formData.non_acquistabile}
              onChange={(e) => setFormData({ ...formData, non_acquistabile: e.target.checked })}
            />
            Non acquistabile (tab Accademia)
          </label>
          <CatalogoAccademiaFlags formData={formData} setFormData={setFormData} syncTecnicaNonAcquistabile />
        </div>
      </div>

      <RichTextEditor label="Effetto Tecnico / Formula (HTML)" value={formData.effetto} onChange={v => setFormData({...formData, effetto: v})} />
      <RichTextEditor label="Prerequisiti e Materiali" value={formData.prerequisiti} onChange={v => setFormData({...formData, prerequisiti: v})} />
      <RichTextEditor label="Svolgimento e Testo Narrativo" value={formData.testo} onChange={v => setFormData({...formData, testo: v})} />

      <CharacteristicInline 
        items={formData.componenti || []} 
        options={punteggiList.filter(p => p.tipo === 'CA')}
        onAdd={() => setFormData({...formData, componenti: [...(formData.componenti || []), {caratteristica:'', valore:1}]})}
        onChange={(i, f, v) => updateInline('componenti', i, f, v)}
        onRemove={(i) => setFormData({...formData, componenti: formData.componenti.filter((_, idx) => idx !== i)})}
      />
      <StaffMinigiocoQrSection qrcodeId={formData.qrcode_id} onLogout={onLogout} />
    </div>
  );
};

// Helper locali...
const Input = ({ label, value, onChange, type="text" }) => (
    <div className="w-full text-left">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">{label}</label>
      <input type={type} className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white focus:border-amber-500 outline-none shadow-inner" value={value || ""} onChange={e => onChange(e.target.value)} />
    </div>
);

const Select = ({ label, value, options, onChange }) => (
    <div className="w-full text-left">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">{label}</label>
      <select className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white cursor-pointer focus:border-amber-500 outline-none" value={value ? String(value) : ""} onChange={e => onChange(e.target.value)}>
        <option value="">- SELEZIONA -</option>
        {options.map(o => <option key={o.id} value={String(o.id)}>{o.nome}</option>)}
      </select>
    </div>
);

export default CerimonialeEditor;