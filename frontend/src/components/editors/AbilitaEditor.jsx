import React, { useState, useEffect } from 'react';
import { staffCreateAbilita, staffUpdateAbilita, staffGetAbilita, getAbilitaEditorResources } from '../../api';
import RichTextEditor from '../RichTextEditor';
import StatModInline from './inlines/StatModInline';
import GenericRelationInline from './inlines/GenericRelationInline';
import SearchableSelect from './SearchableSelect';

const DURATA_OPTIONS = ['O1H', 'DAY', 'EVT'];
const TIPO_MOD_OPTIONS = ['ADD', 'MOL'];

const EMPTY_ABILITA_FORM = {
    nome: '',
    descrizione: '',
    caratteristica: null,
    caratteristica_2: null,
    caratteristica_3: null,
    costo_pc: 0,
    costo_crediti: 0,
    is_tratto_aura: false,
    aura_riferimento: null,
    livello_riferimento: 0,
    tiers: [],
    requisiti: [],
    punteggi_assegnati: [],
    punteggi_dipendenti: [],
    prerequisiti: [],
    statistiche: [],
    effetto_uso_risorsa_str: '',
    recupero_risorsa_str: '',
};

const EMPTY_EFFETTO_WIZARD = {
    stat_sigla: 'FRT',
    durata: 'O1H',
    modifiche: [{ stat_sigla: 'PV', valore: 1, tipo_modificatore: 'ADD' }],
};

const EMPTY_RECUPERO_WIZARD = {
    rigenerazioni: [{ stat_sigla: 'PV', ogni_minuti: 5, step: 1 }],
};

/** La lista staff restituisce righe senza relazioni annidate: senza merge, .map sugli inline va in errore. */
function mergeAbilitaFormState(initialData) {
    if (!initialData) {
        return { ...EMPTY_ABILITA_FORM };
    }
    return {
        ...EMPTY_ABILITA_FORM,
        ...initialData,
        tiers: Array.isArray(initialData.tiers) ? initialData.tiers : [],
        requisiti: Array.isArray(initialData.requisiti) ? initialData.requisiti : [],
        punteggi_assegnati: Array.isArray(initialData.punteggi_assegnati) ? initialData.punteggi_assegnati : [],
        punteggi_dipendenti: Array.isArray(initialData.punteggi_dipendenti) ? initialData.punteggi_dipendenti : [],
        prerequisiti: Array.isArray(initialData.prerequisiti) ? initialData.prerequisiti : [],
        statistiche: Array.isArray(initialData.statistiche) ? initialData.statistiche : [],
        effetto_uso_risorsa_str:
            initialData.effetto_uso_risorsa != null
                ? JSON.stringify(initialData.effetto_uso_risorsa, null, 2)
                : '',
        recupero_risorsa_str:
            initialData.recupero_risorsa != null
                ? JSON.stringify(initialData.recupero_risorsa, null, 2)
                : '',
    };
}

const AbilitaEditor = ({ onBack, onLogout, initialData = null }) => {
    const [punteggi, setPunteggi] = useState([]); 
    const [abilitaList, setAbilitaList] = useState([]); 
    const [tiersList, setTiersList] = useState([]); 
    const [effettoWizard, setEffettoWizard] = useState(EMPTY_EFFETTO_WIZARD);
    const [recuperoWizard, setRecuperoWizard] = useState(EMPTY_RECUPERO_WIZARD);

    const statsOptions = punteggi.filter(p => p.tipo === 'ST');
    const auraOptions = punteggi.filter(p => p.tipo === 'AU');
    const elementOptions = punteggi.filter(p => p.tipo === 'EL' || p.tipo === 'MA'); // 'EL' o 'MA' a seconda di come codifichi gli elementi/materie nel DB

    const initialKey = initialData?.id ?? 'new';
    const [formData, setFormData] = useState(() => mergeAbilitaFormState(initialData));

    useEffect(() => {
        setFormData(mergeAbilitaFormState(initialData));
    }, [initialKey]);

    useEffect(() => {
        const editId = initialData?.id;
        if (!editId) return undefined;
        let cancelled = false;
        (async () => {
            try {
                const full = await staffGetAbilita(editId, onLogout);
                if (cancelled || !full || String(full.id) !== String(editId)) return;
                setFormData(mergeAbilitaFormState(full));
            } catch (err) {
                console.error('Errore caricamento dettaglio abilità', err);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [initialData?.id, onLogout]);

    useEffect(() => {
        const loadResources = async () => {
            try {
                const resources = await getAbilitaEditorResources(onLogout);
                setPunteggi(resources?.punteggi || []);
                setAbilitaList(resources?.abilita || []);
                setTiersList(resources?.tiers || []);
            } catch (err) {
                console.error("Errore caricamento risorse editor", err);
            }
        };
        loadResources();
    }, [onLogout]);

    const handleSave = async () => {
        try {
            let effetto_uso_risorsa = null;
            let recupero_risorsa = null;
            try {
                const t = (formData.effetto_uso_risorsa_str || '').trim();
                if (t) effetto_uso_risorsa = JSON.parse(t);
            } catch {
                alert('JSON non valido in «Effetto all\'uso risorsa» (pool Fortuna / …).');
                return;
            }
            try {
                const t = (formData.recupero_risorsa_str || '').trim();
                if (t) recupero_risorsa = JSON.parse(t);
            } catch {
                alert('JSON non valido in «Recupero risorsa».');
                return;
            }

            const tiers = formData.tiers || [];
            const requisiti = formData.requisiti || [];
            const punteggiAssegnati = formData.punteggi_assegnati || [];
            const punteggiDipendenti = formData.punteggi_dipendenti || [];
            const prerequisiti = formData.prerequisiti || [];

            const {
                effetto_uso_risorsa_str: _s1,
                recupero_risorsa_str: _s2,
                effetto_uso_risorsa: _o1,
                recupero_risorsa: _o2,
                ...formRest
            } = formData;

            const payload = {
                ...formRest,
                effetto_uso_risorsa,
                recupero_risorsa,
                caratteristica: formData.caratteristica ? parseInt(formData.caratteristica) : null,
                caratteristica_2: formData.caratteristica_2 ? parseInt(formData.caratteristica_2) : null,
                caratteristica_3: formData.caratteristica_3 ? parseInt(formData.caratteristica_3) : null,
                aura_riferimento: formData.aura_riferimento ? parseInt(formData.aura_riferimento) : null,
                tiers: tiers.map(t => ({...t, tabella: parseInt(t.tabella)})),
                requisiti: requisiti.map(r => ({...r, requisito: parseInt(r.requisito)})),
                punteggi_assegnati: punteggiAssegnati.map(p => ({...p, punteggio: parseInt(p.punteggio)})),
                punteggi_dipendenti: punteggiDipendenti.map(p => ({
                    ...p,
                    punteggio_target: parseInt(p.punteggio_target),
                    punteggio_sorgente: parseInt(p.punteggio_sorgente),
                    incremento: parseInt(p.incremento || 0),
                    ogni_x: Math.max(1, parseInt(p.ogni_x || 1)),
                })),
                prerequisiti: prerequisiti.map(p => ({...p, prerequisito: parseInt(p.prerequisito)})),
                // Statistiche è già gestito come array di oggetti da StatModInline
            };

            if (formData.id) {
                await staffUpdateAbilita(formData.id, payload, onLogout);
            } else {
                await staffCreateAbilita(payload, onLogout);
            }
            onBack(); 
        } catch (error) {
            alert("Errore durante il salvataggio: " + error.message);
        }
    };

    // Helper per StatModInline
    const handleUpdateStat = (index, field, value) => {
        const newStats = [...formData.statistiche];
        newStats[index] = { ...newStats[index], [field]: value };
        setFormData({ ...formData, statistiche: newStats });
    };

    const handleRemoveStat = (index) => {
        const newStats = formData.statistiche.filter((_, i) => i !== index);
        setFormData({ ...formData, statistiche: newStats });
    };

    const handleAddStat = () => {
        setFormData({
            ...formData,
            statistiche: [
                ...formData.statistiche,
                { statistica: null, valore: 1, tipo_modificatore: 'ADD' } // Default
            ]
        });
    };

    const caratteristiche = punteggi.filter(p => p.tipo === 'CA' || p.tipo === 'CO');
    const aure = punteggi.filter(p => p.tipo === 'AU');
    const allStats = punteggi.filter(p => p.tipo === 'ST');

    const pushEffettoWizardToJson = () => {
        const payload = {
            stat_sigla: (effettoWizard.stat_sigla || '').toUpperCase().trim(),
            durata: (effettoWizard.durata || 'O1H').toUpperCase().trim(),
            modifiche: (effettoWizard.modifiche || [])
                .filter((r) => r && r.stat_sigla)
                .map((r) => ({
                    stat_sigla: String(r.stat_sigla || '').toUpperCase().trim(),
                    valore: Number(r.valore || 0),
                    tipo_modificatore: String(r.tipo_modificatore || 'ADD').toUpperCase().trim(),
                })),
        };
        setFormData({ ...formData, effetto_uso_risorsa_str: JSON.stringify(payload, null, 2) });
    };

    const pushRecuperoWizardToJson = () => {
        const payload = {
            rigenerazioni: (recuperoWizard.rigenerazioni || [])
                .filter((r) => r && r.stat_sigla)
                .map((r) => ({
                    stat_sigla: String(r.stat_sigla || '').toUpperCase().trim(),
                    ogni_minuti: Math.max(1, Number(r.ogni_minuti || 1)),
                    step: Math.max(1, Number(r.step || 1)),
                })),
        };
        setFormData({ ...formData, recupero_risorsa_str: JSON.stringify(payload, null, 2) });
    };

    return (
        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 shadow-2xl text-white max-w-7xl mx-auto overflow-y-auto max-h-[90vh]">
            {/* HEADER EDITOR */}
            <div className="flex justify-between items-center border-b border-gray-700 pb-4 mb-6 sticky top-0 bg-gray-800 z-10">
                <h2 className="text-xl font-bold text-emerald-400 uppercase tracking-tighter">
                    {formData.id ? `Modifica: ${formData.nome}` : 'Nuova Abilità'}
                </h2>
                <div className="flex gap-3">
                    <button onClick={handleSave} className="bg-emerald-600 hover:bg-emerald-500 px-6 py-2 rounded-lg font-black text-sm shadow-lg">SALVA</button>
                    <button onClick={onBack} className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg font-bold text-sm">ANNULLA</button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* COLONNA 1: DATI BASE */}
                <div className="space-y-4 lg:col-span-1">
                    <div>
                        <label className="text-xs text-gray-500 uppercase font-bold">Nome</label>
                        <input 
                            type="text" 
                            className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white"
                            value={formData.nome}
                            onChange={e => setFormData({...formData, nome: e.target.value})}
                        />
                    </div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div>
                            <label className="text-xs text-gray-500 uppercase font-bold">Caratteristica 1 (base)</label>
                            <SearchableSelect
                                options={caratteristiche}
                                value={formData.caratteristica || ""}
                                onChange={val => setFormData({...formData, caratteristica: val || null})}
                                placeholder="- Nessuna -"
                            />
                        </div>
                        <div>
                            <label className="text-xs text-gray-500 uppercase font-bold">Caratteristica 2 (opz.)</label>
                            <SearchableSelect
                                options={caratteristiche}
                                value={formData.caratteristica_2 || ""}
                                onChange={val => setFormData({...formData, caratteristica_2: val || null})}
                                placeholder="- Nessuna -"
                            />
                        </div>
                        <div>
                            <label className="text-xs text-gray-500 uppercase font-bold">Caratteristica 3 (opz.)</label>
                            <SearchableSelect
                                options={caratteristiche}
                                value={formData.caratteristica_3 || ""}
                                onChange={val => setFormData({...formData, caratteristica_3: val || null})}
                                placeholder="- Nessuna -"
                            />
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-xs text-gray-500 uppercase font-bold">Costo PC</label>
                            <input 
                                type="number" 
                                className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white text-right"
                                value={formData.costo_pc}
                                onChange={e => setFormData({...formData, costo_pc: parseInt(e.target.value)})}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="text-xs text-gray-500 uppercase font-bold">Costo Crediti</label>
                        <input 
                            type="number" 
                            className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white text-right"
                            value={formData.costo_crediti}
                            onChange={e => setFormData({...formData, costo_crediti: parseInt(e.target.value)})}
                        />
                    </div>

                    {/* BOX AURA */}
                    <div className="bg-gray-900/30 p-3 rounded border border-purple-900/30">
                        <label className="flex items-center gap-2 mb-2 cursor-pointer">
                            <input 
                                type="checkbox" 
                                checked={formData.is_tratto_aura} 
                                onChange={e => setFormData({...formData, is_tratto_aura: e.target.checked})}
                            />
                            <span className="text-xs font-bold text-purple-400 uppercase">È un Tratto d'Aura</span>
                        </label>
                        
                        {formData.is_tratto_aura && (
                            <div className="space-y-2 pl-4 border-l-2 border-purple-500/30">
                                <div>
                                    <label className="text-xs text-gray-500 uppercase font-bold">Aura Rif.</label>
                                    <SearchableSelect
                                        options={aure}
                                        value={formData.aura_riferimento || ""}
                                        onChange={val => setFormData({...formData, aura_riferimento: val || null})}
                                        placeholder="- Seleziona -"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500 uppercase font-bold">Livello Sblocco</label>
                                    <input 
                                        type="number" 
                                        className="w-full bg-gray-950 border border-gray-700 rounded p-1 text-white"
                                        value={formData.livello_riferimento}
                                        onChange={e => setFormData({...formData, livello_riferimento: parseInt(e.target.value)})}
                                    />
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* COLONNA 2: DESCRIZIONE */}
                <div className="lg:col-span-2 h-full flex flex-col">
                    <label className="text-xs text-gray-500 uppercase font-bold mb-1">Descrizione Effetto</label>
                    <div className="flex-1 bg-gray-950 border border-gray-700 rounded min-h-[200px]">
                        <RichTextEditor 
                            value={formData.descrizione || ''} 
                            onChange={(val) => setFormData({...formData, descrizione: val})} 
                        />
                    </div>
                </div>
            </div>

            {/* Pool risorse statistiche (Fortuna FRT, …) */}
            <div className="mt-8 p-5 rounded-xl border border-amber-900/40 bg-amber-950/20 space-y-4">
                <h3 className="text-sm font-bold text-amber-200 uppercase tracking-wide">Risorse pool (Fortuna / altre)</h3>
                <p className="text-xs text-gray-400 leading-relaxed">
                    Opzionale. Inserisci JSON valido: al salvataggio viene controllato; campi vuoti = nessuna regola.
                </p>

                <details className="group rounded-lg border border-gray-700 bg-gray-950/60 text-left">
                    <summary className="cursor-pointer list-none px-4 py-3 text-xs font-bold text-amber-100/95 uppercase tracking-wide flex items-center justify-between gap-2">
                        <span>Come compilare questi campi</span>
                        <span className="text-gray-500 font-normal normal-case">clic per aprire</span>
                    </summary>
                    <div className="px-4 pb-4 pt-0 space-y-4 text-xs text-gray-300 leading-relaxed border-t border-gray-800/80">
                        <p>
                            Le <strong className="text-gray-200">statistiche “pool”</strong> (es. Fortuna, sigla{' '}
                            <code className="text-amber-200/90">FRT</code>) vanno marcate nel database come risorsa a pool;
                            il massimo in scheda è il tetto, il giocatore consuma punti dal tab Gioco.
                        </p>

                        <div>
                            <p className="font-bold text-gray-200 mb-1">1. Effetto all&apos;uso risorsa</p>
                            <p className="mb-2">
                                Si applica quando un personaggio che <strong>possiede questa abilità</strong> consuma{' '}
                                <strong>un punto</strong> della risorsa indicata in <code className="text-amber-200/90">stat_sigla</code>.
                                Possono essere attivi più effetti se più abilità definiscono regole sulla stessa risorsa.
                            </p>
                            <ul className="list-disc pl-4 space-y-1 text-gray-400">
                                <li>
                                    <code className="text-gray-200">stat_sigla</code>: sigla della statistica pool (es.{' '}
                                    <code>FRT</code>).
                                </li>
                                <li>
                                    <code className="text-gray-200">durata</code>: fine dell&apos;effetto temporaneo su altre stat —{' '}
                                    <code>O1H</code> un&apos;ora, <code>DAY</code> fino a fine giornata (orario locale),{' '}
                                    <code>EVT</code> fino alla fine dell&apos;evento in corso (se nessun evento attivo, fallback breve).
                                </li>
                                <li>
                                    <code className="text-gray-200">modifiche</code>: array di bonus/malusi temporanei. Ogni voce:{' '}
                                    <code>stat_sigla</code> (statistica modificata, es. <code>PV</code>),{' '}
                                    <code>valore</code> (numero), <code>tipo_modificatore</code>: <code>ADD</code> additivo o{' '}
                                    <code>MOL</code> moltiplicativo (come altrove nel sistema).
                                </li>
                            </ul>
                        </div>

                        <div>
                            <p className="font-bold text-gray-200 mb-1">2. Recupero risorsa</p>
                            <p>
                                Definisce la <strong>rigenerazione automatica</strong> per questa abilita. Formato consigliato:{' '}
                                <code className="text-amber-200/90">{"{\"rigenerazioni\":[{\"stat_sigla\":\"PV\",\"ogni_minuti\":5,\"step\":1}]}"}</code>.
                                Puoi usare anche <code>interval_seconds</code> invece di <code>ogni_minuti</code>. Se più abilita
                                definiscono la stessa stat, il sistema usa l&apos;intervallo più veloce e lo step più alto.
                            </p>
                        </div>
                    </div>
                </details>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div>
                        <div className="mb-2 p-3 rounded border border-emerald-900/40 bg-emerald-950/20 space-y-2">
                            <div className="text-[11px] text-emerald-200 font-bold uppercase tracking-wide">Wizard rapido effetto</div>
                            <div className="grid grid-cols-4 gap-2">
                                <input
                                    className="col-span-1 bg-gray-950 border border-gray-700 rounded p-2 text-xs font-mono text-gray-200"
                                    value={effettoWizard.stat_sigla}
                                    onChange={(e) => setEffettoWizard({ ...effettoWizard, stat_sigla: e.target.value })}
                                    placeholder="Stat risorsa (es FRT)"
                                />
                                <select
                                    className="col-span-1 bg-gray-950 border border-gray-700 rounded p-2 text-xs text-gray-200"
                                    value={effettoWizard.durata}
                                    onChange={(e) => setEffettoWizard({ ...effettoWizard, durata: e.target.value })}
                                >
                                    {DURATA_OPTIONS.map((d) => (
                                        <option key={d} value={d}>{d}</option>
                                    ))}
                                </select>
                                <button
                                    type="button"
                                    className="col-span-2 bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded p-2 text-xs font-bold"
                                    onClick={() =>
                                        setEffettoWizard({
                                            ...effettoWizard,
                                            modifiche: [...(effettoWizard.modifiche || []), { stat_sigla: 'PV', valore: 1, tipo_modificatore: 'ADD' }],
                                        })
                                    }
                                >
                                    + Aggiungi modifica
                                </button>
                            </div>
                            {(effettoWizard.modifiche || []).map((m, idx) => (
                                <div key={`effmod-${idx}`} className="grid grid-cols-5 gap-2">
                                    <input
                                        className="col-span-2 bg-gray-950 border border-gray-700 rounded p-2 text-xs font-mono text-gray-200"
                                        value={m.stat_sigla}
                                        onChange={(e) => {
                                            const next = [...(effettoWizard.modifiche || [])];
                                            next[idx] = { ...next[idx], stat_sigla: e.target.value };
                                            setEffettoWizard({ ...effettoWizard, modifiche: next });
                                        }}
                                        placeholder="Stat target"
                                    />
                                    <input
                                        type="number"
                                        className="col-span-1 bg-gray-950 border border-gray-700 rounded p-2 text-xs font-mono text-gray-200"
                                        value={m.valore}
                                        onChange={(e) => {
                                            const next = [...(effettoWizard.modifiche || [])];
                                            next[idx] = { ...next[idx], valore: e.target.value };
                                            setEffettoWizard({ ...effettoWizard, modifiche: next });
                                        }}
                                    />
                                    <select
                                        className="col-span-1 bg-gray-950 border border-gray-700 rounded p-2 text-xs text-gray-200"
                                        value={m.tipo_modificatore}
                                        onChange={(e) => {
                                            const next = [...(effettoWizard.modifiche || [])];
                                            next[idx] = { ...next[idx], tipo_modificatore: e.target.value };
                                            setEffettoWizard({ ...effettoWizard, modifiche: next });
                                        }}
                                    >
                                        {TIPO_MOD_OPTIONS.map((t) => (
                                            <option key={t} value={t}>{t}</option>
                                        ))}
                                    </select>
                                    <button
                                        type="button"
                                        className="col-span-1 bg-red-900/60 hover:bg-red-800 border border-red-700 rounded p-2 text-xs font-bold"
                                        onClick={() => {
                                            const next = (effettoWizard.modifiche || []).filter((_, i) => i !== idx);
                                            setEffettoWizard({ ...effettoWizard, modifiche: next });
                                        }}
                                    >
                                        X
                                    </button>
                                </div>
                            ))}
                            <button
                                type="button"
                                className="w-full bg-emerald-700 hover:bg-emerald-600 rounded p-2 text-xs font-black uppercase"
                                onClick={pushEffettoWizardToJson}
                            >
                                Genera JSON effetto
                            </button>
                        </div>
                        <label className="text-xs text-gray-500 uppercase font-bold block mb-1">
                            Effetto all&apos;uso risorsa (JSON)
                        </label>
                        <textarea
                            className="w-full min-h-[140px] bg-gray-950 border border-gray-700 rounded p-3 text-sm font-mono text-gray-200"
                            spellCheck={false}
                            placeholder={`{\n  "stat_sigla": "FRT",\n  "durata": "O1H",\n  "modifiche": [\n    { "stat_sigla": "PV", "valore": 1, "tipo_modificatore": "ADD" }\n  ]\n}`}
                            value={formData.effetto_uso_risorsa_str}
                            onChange={(e) => setFormData({ ...formData, effetto_uso_risorsa_str: e.target.value })}
                        />
                    </div>
                    <div>
                        <div className="mb-2 p-3 rounded border border-indigo-900/40 bg-indigo-950/20 space-y-2">
                            <div className="text-[11px] text-indigo-200 font-bold uppercase tracking-wide">Wizard rapido rigenerazione</div>
                            <button
                                type="button"
                                className="w-full bg-gray-800 hover:bg-gray-700 border border-gray-600 rounded p-2 text-xs font-bold"
                                onClick={() =>
                                    setRecuperoWizard({
                                        ...recuperoWizard,
                                        rigenerazioni: [...(recuperoWizard.rigenerazioni || []), { stat_sigla: 'PA', ogni_minuti: 5, step: 1 }],
                                    })
                                }
                            >
                                + Aggiungi rigenerazione
                            </button>
                            {(recuperoWizard.rigenerazioni || []).map((r, idx) => (
                                <div key={`recr-${idx}`} className="grid grid-cols-4 gap-2">
                                    <input
                                        className="col-span-1 bg-gray-950 border border-gray-700 rounded p-2 text-xs font-mono text-gray-200"
                                        value={r.stat_sigla}
                                        onChange={(e) => {
                                            const next = [...(recuperoWizard.rigenerazioni || [])];
                                            next[idx] = { ...next[idx], stat_sigla: e.target.value };
                                            setRecuperoWizard({ ...recuperoWizard, rigenerazioni: next });
                                        }}
                                        placeholder="Sigla stat"
                                    />
                                    <input
                                        type="number"
                                        min="1"
                                        className="col-span-1 bg-gray-950 border border-gray-700 rounded p-2 text-xs font-mono text-gray-200"
                                        value={r.ogni_minuti}
                                        onChange={(e) => {
                                            const next = [...(recuperoWizard.rigenerazioni || [])];
                                            next[idx] = { ...next[idx], ogni_minuti: e.target.value };
                                            setRecuperoWizard({ ...recuperoWizard, rigenerazioni: next });
                                        }}
                                        placeholder="min"
                                    />
                                    <input
                                        type="number"
                                        min="1"
                                        className="col-span-1 bg-gray-950 border border-gray-700 rounded p-2 text-xs font-mono text-gray-200"
                                        value={r.step}
                                        onChange={(e) => {
                                            const next = [...(recuperoWizard.rigenerazioni || [])];
                                            next[idx] = { ...next[idx], step: e.target.value };
                                            setRecuperoWizard({ ...recuperoWizard, rigenerazioni: next });
                                        }}
                                        placeholder="step"
                                    />
                                    <button
                                        type="button"
                                        className="col-span-1 bg-red-900/60 hover:bg-red-800 border border-red-700 rounded p-2 text-xs font-bold"
                                        onClick={() => {
                                            const next = (recuperoWizard.rigenerazioni || []).filter((_, i) => i !== idx);
                                            setRecuperoWizard({ ...recuperoWizard, rigenerazioni: next });
                                        }}
                                    >
                                        X
                                    </button>
                                </div>
                            ))}
                            <button
                                type="button"
                                className="w-full bg-indigo-700 hover:bg-indigo-600 rounded p-2 text-xs font-black uppercase"
                                onClick={pushRecuperoWizardToJson}
                            >
                                Genera JSON rigenerazione
                            </button>
                        </div>
                        <label className="text-xs text-gray-500 uppercase font-bold block mb-1">
                            Recupero risorsa (JSON)
                        </label>
                        <textarea
                            className="w-full min-h-[140px] bg-gray-950 border border-gray-700 rounded p-3 text-sm font-mono text-gray-200"
                            spellCheck={false}
                            placeholder={`{\n  "rigenerazioni": [\n    { "stat_sigla": "PV", "ogni_minuti": 5, "step": 1 },\n    { "stat_sigla": "CHK", "ogni_minuti": 10, "step": 1 }\n  ]\n}`}
                            value={formData.recupero_risorsa_str}
                            onChange={(e) => setFormData({ ...formData, recupero_risorsa_str: e.target.value })}
                        />
                    </div>
                </div>
            </div>

            {/* SEZIONE INLINES */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
                
                {/* 1. Tiers */}
                <GenericRelationInline 
                    title="Tabelle (Ordine)"
                    items={formData.tiers}
                    options={tiersList}
                    targetKey="tabella"
                    valueKey="ordine"
                    onChange={list => setFormData({...formData, tiers: list})}
                    labelFinder={t => t.nome}
                />

                {/* 2. Requisiti */}
                <GenericRelationInline 
                    title="Punteggi Richiesti"
                    items={formData.requisiti}
                    options={punteggi}
                    targetKey="requisito"
                    valueKey="valore"
                    onChange={list => setFormData({...formData, requisiti: list})}
                />

                {/* 3. Prerequisiti */}
                <GenericRelationInline 
                    title="Abilità di prerequisito"
                    items={formData.prerequisiti}
                    options={abilitaList.filter(a => a.id !== formData.id)}
                    targetKey="prerequisito"
                    valueKey={null}
                    onChange={list => setFormData({...formData, prerequisiti: list})}
                />

                {/* 4. Punteggi Assegnati */}
                <GenericRelationInline 
                    title="Assegna Punteggi (Bonus Generali)"
                    items={formData.punteggi_assegnati}
                    options={punteggi.filter(p => p.tipo !== 'ST')}
                    targetKey="punteggio"
                    valueKey="valore"
                    onChange={list => setFormData({...formData, punteggi_assegnati: list})}
                />

                {/* 5. Punteggi Dipendenti */}
                <div className="md:col-span-2 lg:col-span-3 bg-gray-900/50 p-5 rounded-lg border border-cyan-800/50 space-y-4">
                    <div className="flex items-center justify-between">
                        <h4 className="text-sm font-bold text-cyan-300 uppercase">Punteggi dipendenti</h4>
                        <button
                            type="button"
                            className="bg-cyan-700 hover:bg-cyan-600 text-white text-xs font-bold px-3 py-1 rounded"
                            onClick={() =>
                                setFormData({
                                    ...formData,
                                    punteggi_dipendenti: [
                                        ...(formData.punteggi_dipendenti || []),
                                        {
                                            punteggio_target: null,
                                            incremento: 1,
                                            ogni_x: 1,
                                            punteggio_sorgente: null,
                                        },
                                    ],
                                })
                            }
                        >
                            + Aggiungi
                        </button>
                    </div>
                    {(formData.punteggi_dipendenti || []).length === 0 && (
                        <p className="text-xs text-gray-400">
                            Nessuna regola. Esempio: Danni a distanza +1 ogni 2 Forza.
                        </p>
                    )}
                    {(formData.punteggi_dipendenti || []).map((row, idx) => (
                        <div key={idx} className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end bg-gray-950/60 p-3 rounded border border-gray-800">
                            <div className="md:col-span-4">
                                <label className="text-[10px] uppercase text-gray-500 font-bold">Punteggio X</label>
                                <SearchableSelect
                                    options={punteggi}
                                    value={row.punteggio_target || ''}
                                    placeholder="Cerca punteggio target..."
                                    onChange={(e) => {
                                        const next = [...(formData.punteggi_dipendenti || [])];
                                        next[idx] = { ...next[idx], punteggio_target: e };
                                        setFormData({ ...formData, punteggi_dipendenti: next });
                                    }}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="text-[10px] uppercase text-gray-500 font-bold">Aumenta di</label>
                                <input
                                    type="number"
                                    className="w-full bg-gray-950 border border-gray-700 rounded p-1 text-white text-right"
                                    value={row.incremento ?? 1}
                                    onChange={(e) => {
                                        const next = [...(formData.punteggi_dipendenti || [])];
                                        next[idx] = { ...next[idx], incremento: e.target.value };
                                        setFormData({ ...formData, punteggi_dipendenti: next });
                                    }}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="text-[10px] uppercase text-gray-500 font-bold">Ogni</label>
                                <input
                                    type="number"
                                    min="1"
                                    className="w-full bg-gray-950 border border-gray-700 rounded p-1 text-white text-right"
                                    value={row.ogni_x ?? 1}
                                    onChange={(e) => {
                                        const next = [...(formData.punteggi_dipendenti || [])];
                                        next[idx] = { ...next[idx], ogni_x: e.target.value };
                                        setFormData({ ...formData, punteggi_dipendenti: next });
                                    }}
                                />
                            </div>
                            <div className="md:col-span-3">
                                <label className="text-[10px] uppercase text-gray-500 font-bold">Punteggio Y</label>
                                <SearchableSelect
                                    options={punteggi}
                                    value={row.punteggio_sorgente || ''}
                                    placeholder="Cerca punteggio sorgente..."
                                    onChange={(e) => {
                                        const next = [...(formData.punteggi_dipendenti || [])];
                                        next[idx] = { ...next[idx], punteggio_sorgente: e };
                                        setFormData({ ...formData, punteggi_dipendenti: next });
                                    }}
                                />
                            </div>
                            <div className="md:col-span-1">
                                <button
                                    type="button"
                                    className="w-full bg-red-800 hover:bg-red-700 rounded p-1 text-xs font-bold"
                                    onClick={() => {
                                        const next = (formData.punteggi_dipendenti || []).filter((_, i) => i !== idx);
                                        setFormData({ ...formData, punteggi_dipendenti: next });
                                    }}
                                >
                                    X
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {/* 6. Statistiche (Inline Complessa) */}
                <div className="md:col-span-2 lg:col-span-3 bg-gray-900/50 p-4 rounded-lg border border-gray-700">
                    {/* Nota: StatModInline include già il suo header e il pulsante 'Aggiungi', 
                         quindi non serve ricrearli esternamente come facevo prima. 
                         Usiamolo esattamente come in OggettoEditor. */}
                    <StatModInline 
                        items={formData.statistiche}
                        
                        // PROPS FONDAMENTALI (senza queste crasha il map)
                        options={statsOptions}        
                        auraOptions={auraOptions}
                        elementOptions={elementOptions}
                        
                        // Gestione Aggiunta
                        onAdd={() => setFormData({
                            ...formData, 
                            statistiche: [
                                ...formData.statistiche, 
                                // Struttura oggetto vuoto allineata a OggettoEditor
                                { statistica: null, valore: 0, tipo_modificatore: 'ADD' }
                            ]
                        })}
                        
                        // Gestione Modifica
                        onChange={(index, field, value) => {
                            const newStats = [...formData.statistiche];
                            newStats[index] = { ...newStats[index], [field]: value };
                            setFormData({ ...formData, statistiche: newStats });
                        }}
                        
                        // Gestione Rimozione
                        onRemove={(index) => {
                            const newStats = formData.statistiche.filter((_, i) => i !== index);
                            setFormData({ ...formData, statistiche: newStats });
                        }}
                    />
                </div>

            </div>
        </div>
    );
};

export default AbilitaEditor;