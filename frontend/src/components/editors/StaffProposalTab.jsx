import React, { useState, useEffect, useCallback, useMemo, memo } from 'react';
import { createPortal } from 'react-dom';
import { staffGetProposteInValutazione, staffRifiutaProposta, staffApprovaProposta, getEventi } from '../../api';
import { Eye, X, Check, ClipboardCheck, AlertCircle } from 'lucide-react';
import RichTextEditor from '../RichTextEditor';
import RichHtml from '../RichHtml';
import ConfirmDialog from './ConfirmDialog';
import { getAuraName } from '../../utils/auraDisplay';

import InfusioneEditor from './InfusioneEditor';
import TessituraEditor from './TessituraEditor';
import CerimonialeEditor from './CerimonialeEditor';
import MissioneResolvePicker from '../MissioneResolvePicker';
import SearchableSelect from './SearchableSelect';
import {
  StaffToolBody,
  StaffToolHeader,
  StaffToolShell,
  staffModalBackdropClass,
  staffModalCenterClass,
  scrollStaffMainToTop,
} from '../../staff/StaffToolShell';
import { UiEmptyState } from '../ui/AsyncState';

function getPgName(p) {
  if (p?.personaggio_nome) return p.personaggio_nome;
  if (p?.personaggio && typeof p.personaggio === 'object') return p.personaggio.nome;
  return p?.personaggio ? `Personaggio (ID ${p.personaggio})` : 'Personaggio';
}

function getGiocatoreName(p) {
  return String(p?.giocatore_nome || '').trim();
}

function tipoLabel(tipo) {
  if (tipo === 'INF') return 'Infusione';
  if (tipo === 'TES') return 'Tessitura';
  return 'Cerimoniale';
}

function tipoBadgeClass(tipo) {
  if (tipo === 'INF') return 'bg-indigo-900/30 text-indigo-300 border-indigo-700';
  if (tipo === 'TES') return 'bg-cyan-900/30 text-cyan-300 border-cyan-700';
  return 'bg-purple-900/30 text-purple-300 border-purple-700';
}

function PersonaggioConGiocatore({ proposal, nameClass = 'font-bold text-white break-words' }) {
  const giocatore = getGiocatoreName(proposal);
  return (
    <div className="min-w-0">
      <div className={nameClass}>{getPgName(proposal)}</div>
      {giocatore ? (
        <div className="mt-0.5 text-[11px] leading-tight text-gray-400 break-words">{giocatore}</div>
      ) : null}
    </div>
  );
}

function TipoBadge({ tipo }) {
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded text-[10px] font-black tracking-wider uppercase border ${tipoBadgeClass(tipo)}`}>
      {tipoLabel(tipo)}
    </span>
  );
}

const StaffProposalTab = ({ onLogout }) => {
    const [proposals, setProposals] = useState([]);
    const [selectedProposal, setSelectedProposal] = useState(null);
    const [viewMode, setViewMode] = useState('list');
    const [staffNotes, setStaffNotes] = useState("");
    const [loading, setLoading] = useState(false);
    const [feedback, setFeedback] = useState({ type: '', message: '' });
    const [confirmRejectOpen, setConfirmRejectOpen] = useState(false);
    const [eventiOpts, setEventiOpts] = useState([]);
    const [taskEventoId, setTaskEventoId] = useState(null);

    const loadProposals = useCallback(async () => {
        setLoading(true);
        try {
            const data = await staffGetProposteInValutazione(onLogout);
            setProposals(Array.isArray(data) ? data : data.results || []);
        } catch (error) {
            console.error("Errore caricamento proposte", error);
        } finally {
            setLoading(false);
        }
    }, [onLogout]);

    useEffect(() => {
        loadProposals();
    }, [loadProposals]);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const ev = await getEventi(onLogout);
                const rows = Array.isArray(ev) ? ev : ev?.results || [];
                if (!cancelled) setEventiOpts(rows.map((e) => ({ id: e.id, nome: e.titolo || `Evento #${e.id}` })));
            } catch {
                if (!cancelled) setEventiOpts([]);
            }
        })();
        return () => { cancelled = true; };
    }, [onLogout]);

    const handleOpenDetail = useCallback((prop) => {
        setSelectedProposal(prop);
        setStaffNotes(prop.note_staff || "");
        setTaskEventoId(null);
        setViewMode('detail');
        scrollStaffMainToTop();
    }, []);

    const handleBack = useCallback(() => {
        setSelectedProposal(null);
        setViewMode('list');
    }, []);

    const handleRifiuta = async () => {
        try {
            await staffRifiutaProposta(selectedProposal.id, staffNotes, onLogout);
            setFeedback({ type: 'success', message: 'Proposta rifiutata e rimandata al giocatore.' });
            setConfirmRejectOpen(false);
            handleBack();
            loadProposals();
        } catch (err) {
            setFeedback({ type: 'error', message: `Errore: ${err.message}` });
        }
    };

    const handleStartApproval = () => {
        setViewMode('approve_edit');
        scrollStaffMainToTop();
    };

    const editorInitialData = useMemo(() => {
        if (!selectedProposal) return {};
        const p = selectedProposal;

        const cleanComponenti = (p.componenti || []).map(c => ({
            caratteristica: (c.caratteristica && typeof c.caratteristica === 'object') ? c.caratteristica.id : c.caratteristica,
            valore: c.valore
        }));

        return {
            nome: p.nome,
            descrizione: p.descrizione,
            testo: p.descrizione,
            aura_richiesta: (p.aura && typeof p.aura === 'object') ? p.aura.id : p.aura,
            livello: p.livello,
            liv: p.livello_proposto || p.livello || 1,
            mattoni_generici: p.mattoni_generici || 0,
            componenti: cleanComponenti,
            prerequisiti: p.prerequisiti || "",
            svolgimento: p.svolgimento || "",
            effetto: p.effetto || "",
            note_staff: staffNotes
        };
    }, [selectedProposal, staffNotes]);

    const handleFinalizeApproval = async (finalData) => {
        try {
            finalData.note_staff = staffNotes;
            await staffApprovaProposta(selectedProposal.id, finalData, onLogout);
            setFeedback({ type: 'success', message: 'Tecnica approvata e creata con successo.' });
            handleBack();
            setTimeout(() => {
                loadProposals();
            }, 300);
        } catch (err) {
            console.error("Errore Approvazione:", err);
            const errorMsg = err.response?.data?.error || err.message || "Errore sconosciuto";
            setFeedback({ type: 'error', message: `Errore durante l'approvazione: ${errorMsg}` });
            throw err;
        }
    };

    const getCharName = (componente) => {
        if (componente.caratteristica_nome) return componente.caratteristica_nome;
        if (componente.caratteristica && typeof componente.caratteristica === 'object') {
            return componente.caratteristica.nome || componente.caratteristica.sigla || "Caratteristica";
        }
        return "ID: " + componente.caratteristica;
    };

    if (viewMode === 'list') {
        return (
            <StaffToolShell fill>
                <StaffToolHeader
                    title="Valutazione Proposte"
                    description="Tecniche in attesa di revisione staff"
                    icon={<ClipboardCheck size={24} className="text-orange-400" />}
                    sticky
                    actions={(
                        <button
                          type="button"
                          onClick={loadProposals}
                          className="min-h-11 px-3 rounded-lg text-sm underline text-gray-400 hover:text-white"
                        >
                            {loading ? 'Aggiorno…' : 'Aggiorna'}
                        </button>
                    )}
                />
                <StaffToolBody>
                {feedback.message && (
                    <div className={`mb-4 text-xs border rounded-md px-3 py-2 inline-block break-words ${
                        feedback.type === 'error'
                            ? 'text-red-200 bg-red-900/20 border-red-700/40'
                            : 'text-emerald-300 bg-emerald-900/20 border-emerald-700/40'
                    }`}
                    >
                        {feedback.message}
                    </div>
                )}

                {proposals.length === 0 ? (
                    <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-6">
                        <UiEmptyState
                          icon={AlertCircle}
                          title="Nessuna proposta"
                          message="Nessuna proposta in attesa di valutazione."
                        />
                    </div>
                ) : (
                  <>
                    <div className="lg:hidden space-y-3">
                      {proposals.map((p) => (
                        <article
                          key={p.id}
                          className="rounded-xl border border-gray-700 bg-gray-800/60 p-3 space-y-3 min-w-0"
                        >
                          <PersonaggioConGiocatore proposal={p} />
                          <div className="flex flex-wrap items-center gap-2 min-w-0">
                            <TipoBadge tipo={p.tipo} />
                            <span className="text-sm text-white font-medium break-words min-w-0">{p.nome}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleOpenDetail(p)}
                            className="min-h-11 w-full bg-orange-600 hover:bg-orange-500 text-white px-4 rounded-lg text-xs font-bold uppercase shadow-lg flex items-center justify-center gap-2"
                          >
                            <Eye size={14} /> Valuta
                          </button>
                        </article>
                      ))}
                    </div>

                    <div className="hidden lg:block flex-1 overflow-auto rounded-xl border border-gray-700 bg-gray-800/50 shadow-inner min-h-0">
                    <table className="w-full text-left text-gray-300">
                        <thead className="bg-gray-800 text-xs uppercase font-bold text-gray-400 sticky top-0 z-10 shadow-md">
                            <tr>
                                <th className="px-6 py-4">Personaggio</th>
                                <th className="px-6 py-4">Tipo</th>
                                <th className="px-6 py-4">Nome Tecnica</th>
                                <th className="px-6 py-4 text-right">Azioni</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700">
                            {proposals.map((p) => (
                                <tr key={p.id} className="hover:bg-gray-700/50 transition-colors">
                                    <td className="px-6 py-4">
                                        <PersonaggioConGiocatore proposal={p} />
                                    </td>
                                    <td className="px-6 py-4">
                                        <TipoBadge tipo={p.tipo} />
                                    </td>
                                    <td className="px-6 py-4 text-white font-medium break-words">{p.nome}</td>
                                    <td className="px-6 py-4 text-right">
                                        <button
                                            type="button"
                                            onClick={() => handleOpenDetail(p)}
                                            className="min-h-11 bg-orange-600 hover:bg-orange-500 text-white px-4 rounded-lg text-xs font-bold uppercase shadow-lg transition-all inline-flex items-center gap-2 ml-auto"
                                        >
                                            <Eye size={14} /> Valuta
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    </div>
                  </>
                )}
                </StaffToolBody>
            </StaffToolShell>
        );
    }

    if (viewMode === 'approve_edit') {
        const commonProps = {
            initialData: editorInitialData,
            onSave: handleFinalizeApproval,
            onCancel: () => setViewMode('detail'),
            onLogout: onLogout,
            isApprovalMode: true
        };

        return createPortal(
            <div className="fixed inset-0 z-[110] bg-black overflow-y-auto" style={{ height: '100dvh' }}>
                <div className="p-3 sm:p-6 max-w-7xl mx-auto">
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 mb-4 bg-gray-800 p-3 sm:p-4 rounded-xl border border-gray-700">
                        <div className="flex items-start gap-3 min-w-0">
                            <div className="bg-green-600/20 p-2 rounded-lg border border-green-500/50 shrink-0">
                                <Check className="text-green-500" size={24}/>
                            </div>
                            <div className="min-w-0">
                                <h2 className="text-lg sm:text-xl font-bold text-white break-words">Finalizzazione {selectedProposal.tipo}</h2>
                                <PersonaggioConGiocatore proposal={selectedProposal} nameClass="text-sm font-semibold text-gray-200 break-words" />
                                <p className="text-sm text-gray-400 break-words">Modifica se necessario e salva per creare la tecnica effettiva.</p>
                            </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => setViewMode('detail')}
                          className="min-h-11 bg-gray-700 hover:bg-gray-600 text-white px-4 rounded-lg font-bold text-sm w-full sm:w-auto"
                        >
                          Annulla
                        </button>
                    </div>

                    {feedback.type === 'error' && feedback.message && (
                        <div className="mb-4 text-xs border rounded-md px-3 py-2 text-red-200 bg-red-900/20 border-red-700/40 break-words">
                            {feedback.message}
                        </div>
                    )}

                    <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden min-h-[80vh]">
                        {selectedProposal.tipo === 'INF' && <InfusioneEditor {...commonProps} />}
                        {selectedProposal.tipo === 'TES' && <TessituraEditor {...commonProps} />}
                        {selectedProposal.tipo === 'CER' && <CerimonialeEditor {...commonProps} />}
                    </div>
                </div>
            </div>,
            document.body,
        );
    }

    return createPortal(
        <div className={staffModalBackdropClass} role="dialog" aria-modal="true">
            <div className={staffModalCenterClass}>
            <div className="bg-gray-900 border border-gray-600 rounded-t-2xl sm:rounded-2xl w-full max-w-6xl max-h-[min(95vh,100dvh)] flex flex-col shadow-2xl min-w-0">

                <div className="p-4 sm:p-5 border-b border-gray-700 flex justify-between items-start gap-3 bg-gray-800 rounded-t-2xl shrink-0">
                    <div className="min-w-0">
                        <h2 className="text-xl sm:text-2xl font-bold text-white break-words">
                            <span className="text-orange-500">Valutazione:</span> {selectedProposal.nome}
                        </h2>
                        <PersonaggioConGiocatore
                          proposal={selectedProposal}
                          nameClass="text-sm font-semibold text-gray-200 break-words mt-1"
                        />
                        <div className="flex flex-wrap gap-2 mt-1">
                            <span className="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-300 font-mono">ID: {selectedProposal.id}</span>
                            <span className="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-300">Livello: {selectedProposal.livello}</span>
                        </div>
                    </div>
                    <button
                      type="button"
                      onClick={handleBack}
                      className="min-h-11 min-w-11 shrink-0 text-gray-400 hover:text-white bg-gray-700/50 p-2 rounded-full hover:bg-gray-700"
                      aria-label="Chiudi"
                    >
                      <X size={24}/>
                    </button>
                </div>

                <div className="p-4 sm:p-6 overflow-y-auto flex-1 space-y-6 min-h-0">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">

                        <div className="space-y-6 min-w-0">
                            <div className="bg-gray-800/50 p-4 sm:p-5 rounded-xl border border-gray-700">
                                <h3 className="text-cyan-500 font-black uppercase text-xs tracking-widest mb-4 border-b border-gray-700 pb-2">Specifiche Tecniche</h3>
                                <div className="space-y-2 text-sm">
                                    <p><strong className="text-gray-400">Tipo:</strong> {selectedProposal.tipo}</p>
                                    <p className="break-words"><strong className="text-gray-400">Aura Richiesta:</strong> {getAuraName(selectedProposal)}</p>
                                    <p>
                                        <strong className="text-gray-400">Vendita in Accademia:</strong>{' '}
                                        {selectedProposal.permetti_vendita !== false ? (
                                            <span className="text-green-400">Sì</span>
                                        ) : (
                                            <span className="text-amber-400">No (solo negozi speciali)</span>
                                        )}
                                    </p>
                                    {selectedProposal.tipo === 'CER' && (
                                        <p><strong className="text-gray-400">Livello Proposto:</strong> {selectedProposal.livello_proposto}</p>
                                    )}
                                    <div className="mt-3 bg-gray-900 p-3 rounded-lg">
                                        <strong className="text-gray-400 block mb-2 text-xs uppercase">Componenti / Mattoni:</strong>
                                        <ul className="list-disc pl-5 text-gray-300 space-y-1">
                                            {selectedProposal.componenti && selectedProposal.componenti.map((c, i) => (
                                                <li key={i} className="break-words">
                                                    <span className="text-cyan-400 font-bold">{getCharName(c)}</span>
                                                    <span className="text-gray-500 text-xs ml-2">x{c.valore}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-gray-800/50 p-4 sm:p-5 rounded-xl border border-gray-700">
                                <h3 className="text-cyan-500 font-black uppercase text-xs tracking-widest mb-4 border-b border-gray-700 pb-2">Descrizione Giocatore</h3>
                                <RichHtml
                                    content={selectedProposal.descrizione}
                                    className="prose prose-invert text-sm max-w-none text-gray-300 leading-relaxed"
                                />

                                {selectedProposal.spiegazione_teorie && (
                                    <div className="mt-6 pt-4 border-t border-gray-700/50">
                                        <strong className="text-indigo-400 block text-xs uppercase mb-2 tracking-widest">
                                            Teorie coinvolte (in game)
                                        </strong>
                                        <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed break-words">
                                            {selectedProposal.spiegazione_teorie}
                                        </p>
                                    </div>
                                )}

                                {selectedProposal.tipo === 'CER' && (
                                    <div className="mt-6 space-y-4 pt-4 border-t border-gray-700/50">
                                        <div>
                                            <strong className="text-yellow-500 block text-xs uppercase mb-1">Prerequisiti</strong>
                                            <p className="text-sm text-gray-300 break-words">{selectedProposal.prerequisiti}</p>
                                        </div>
                                        <div>
                                            <strong className="text-yellow-500 block text-xs uppercase mb-1">Svolgimento</strong>
                                            <p className="text-sm text-gray-300 break-words">{selectedProposal.svolgimento}</p>
                                        </div>
                                        <div>
                                            <strong className="text-yellow-500 block text-xs uppercase mb-1">Effetto</strong>
                                            <p className="text-sm text-gray-300 break-words">{selectedProposal.effetto}</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="flex flex-col min-h-[240px] bg-gray-800 p-1 rounded-xl border border-gray-700">
                            <div className="bg-gray-900 rounded-t-lg p-3 border-b border-gray-700">
                                <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                                    <ClipboardCheck size={14}/> Note Staff (Visibili al giocatore)
                                </label>
                            </div>
                            <div className="flex-1 overflow-hidden relative min-h-[180px]">
                                <RichTextEditor
                                    value={staffNotes}
                                    onChange={setStaffNotes}
                                    placeholder="Scrivi qui le motivazioni del rifiuto o eventuali note di approvazione..."
                                    className="h-full border-none rounded-none focus:ring-0"
                                />
                            </div>
                        </div>
                    </div>
                </div>

                <div className="space-y-3 border-t border-gray-700 bg-gray-800 p-4 sm:p-5 shadow-lg z-20 rounded-b-2xl shrink-0 pb-[max(1rem,var(--kor-safe-bottom))] sm:pb-5">
                    <div className="grid gap-2 sm:grid-cols-2">
                        <SearchableSelect
                            options={eventiOpts}
                            value={taskEventoId}
                            onChange={setTaskEventoId}
                            placeholder="— Evento per task —"
                            minOptionsForSearch={0}
                        />
                        <MissioneResolvePicker
                            onLogout={onLogout}
                            tipoRisoluzione="TECNICA"
                            eventoId={taskEventoId}
                            personaggioId={selectedProposal?.personaggio || selectedProposal?.personaggio_id}
                            propostaTecnicaId={selectedProposal?.id}
                            label="Questa tecnica risolve task"
                        />
                    </div>
                    <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 sm:gap-4">
                    <button
                        type="button"
                        onClick={() => setConfirmRejectOpen(true)}
                        className="min-h-11 w-full sm:w-auto bg-red-900/30 border border-red-700 text-red-300 hover:bg-red-900/50 px-6 py-3 rounded-xl flex items-center justify-center gap-2 text-sm font-bold uppercase transition-all"
                    >
                        <X size={18} /> Rifiuta (Torna in Bozza)
                    </button>

                    <button
                        type="button"
                        onClick={handleStartApproval}
                        className="min-h-11 w-full sm:w-auto bg-green-600 hover:bg-green-500 text-white px-8 py-3 rounded-xl flex items-center justify-center gap-2 font-black uppercase shadow-lg shadow-green-900/30"
                    >
                        <Check size={18} /> Approva & Crea Tecnica
                    </button>
                    </div>
                </div>
            </div>
            </div>
            <ConfirmDialog
                open={confirmRejectOpen}
                title="Confermi il rifiuto?"
                message="La proposta tornera in bozza al giocatore."
                confirmLabel="Rifiuta"
                onCancel={() => setConfirmRejectOpen(false)}
                onConfirm={handleRifiuta}
            />
        </div>,
        document.body,
    );
};

export default memo(StaffProposalTab);
