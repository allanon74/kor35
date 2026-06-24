import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Users, Search, X, QrCode, Briefcase, Coins, FileText, StickyNote, Loader2, Plus, Skull, Heart, RotateCcw,
  Sparkles, Watch, Package, ScrollText, Calendar, Mail, Wand2, Archive,
} from 'lucide-react';
import RichTextEditor from '../RichTextEditor';
import StaffCostumePhotosSection from '../StaffCostumePhotosSection';
import StaffQrTab from '../StaffQrTab';
import SearchableSelect from './SearchableSelect';
import { useStaffQrAssociation } from '../../hooks/useStaffQrAssociation';
import {
  staffGetPersonaggi,
  staffGetPersonaggioDetail,
  staffPatchPersonaggio,
  staffAddResourcesToPersonaggio,
  staffCreaOggettoDaBasePerPersonaggio,
  staffPersonaggioAggiungiOggetto,
  staffPersonaggioRimuoviOggetto,
  staffPersonaggioDistruggiOggetto,
  staffGetOggettiSenzaPosizione,
  staffGetOggettoStaff,
  staffGetOggettiBase,
  staffGetPersonaggioLogs,
  staffRigeneraLikePersonaggio,
  staffSendMessageToPersonaggio,
  staffGetPersonaggioCreazioneGuidataProposte,
  staffIncrementaRisorsaPool,
  staffGetCarriere,
  staffGetCarriereMemberships,
  staffCreateCarriereMembership,
  staffUpdateCarriereMembership,
  staffDeleteCarriereMembership,
  staffGetTipiCarriera,
  staffGetCariche,
  getEre,
  resetPersonaggio,
  staffKillPersonaggio,
  staffRevivePersonaggio,
  deletePersonaggio,
  resolveMediaUrl,
} from '../../api';

const TABS = [
  { id: 'bg', label: 'BG / Anagrafica', icon: FileText },
  { id: 'qr', label: 'QR', icon: QrCode },
  { id: 'membership', label: 'Carriere / KORP', icon: Briefcase },
  { id: 'risorse', label: 'Risorse', icon: Coins },
  { id: 'inventario', label: 'Inventario', icon: Package },
  { id: 'instafame', label: 'InstaFame', icon: Sparkles },
  { id: 'watch', label: 'Watch', icon: Watch },
  { id: 'log', label: 'Log / Diario', icon: ScrollText },
  { id: 'eventi', label: 'Eventi', icon: Calendar },
  { id: 'messaggio', label: 'Messaggio', icon: Mail },
  { id: 'creazione', label: 'Creazione guidata', icon: Wand2 },
  { id: 'note', label: 'Note master', icon: StickyNote },
  { id: 'azioni', label: 'Azioni', icon: RotateCcw },
];

const PersonaggiStaffManager = ({ onLogout }) => {
  const [filters, setFilters] = useState({
    q: '', tipo: 'all', era: '', carriera: '', morto: 'vivo', page: 1,
  });
  const [listData, setListData] = useState({ results: [], count: 0, next: null, previous: null });
  const [loading, setLoading] = useState(true);
  const [ere, setEre] = useState([]);
  const [carriere, setCarriere] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [modalTab, setModalTab] = useState('bg');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [showQrScan, setShowQrScan] = useState(false);
  const [resourceForm, setResourceForm] = useState({ tipo: 'crediti', amount: 0, reason: 'Intervento staff' });
  const [poolInputs, setPoolInputs] = useState({});
  const [memberships, setMemberships] = useState([]);
  const [tipiCarriera, setTipiCarriera] = useState([]);
  const [cariche, setCariche] = useState([]);
  const [membershipForm, setMembershipForm] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [msgForm, setMsgForm] = useState({ titolo: '', testo: '' });
  const [creazioneProposte, setCreazioneProposte] = useState(null);
  const [oggettiBase, setOggettiBase] = useState([]);
  const [oggettoBaseDraft, setOggettoBaseDraft] = useState({ id: '', motivo: 'Assegnazione staff' });
  const [oggettiSenzaPosizione, setOggettiSenzaPosizione] = useState([]);
  const [oggettoEsistenteDraft, setOggettoEsistenteDraft] = useState({ id: '', motivo: 'Assegnazione staff' });
  const [manualOggettoId, setManualOggettoId] = useState('');
  const [inventarioMotivo, setInventarioMotivo] = useState('Intervento staff inventario');

  const loadOggettiSenzaPosizione = useCallback(async () => {
    try {
      const data = await staffGetOggettiSenzaPosizione(onLogout);
      const list = Array.isArray(data) ? data : [];
      setOggettiSenzaPosizione(list.map((o) => ({
        id: o.id,
        nome: `${o.nome} (#${o.id}, ${o.tipo_oggetto || '?'})`,
      })));
    } catch {
      setOggettiSenzaPosizione([]);
    }
  }, [onLogout]);

  const loadLogs = useCallback(async (id) => {
    if (!id) return;
    setLogsLoading(true);
    try {
      const data = await staffGetPersonaggioLogs(id, 1, onLogout);
      setLogs(data?.results || (Array.isArray(data) ? data : []));
    } catch {
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  }, [onLogout]);

  const loadCreazioneProposte = useCallback(async (id) => {
    if (!id) return;
    try {
      const data = await staffGetPersonaggioCreazioneGuidataProposte(id, onLogout);
      setCreazioneProposte(data);
    } catch {
      setCreazioneProposte(null);
    }
  }, [onLogout]);

  const reloadDetail = useCallback(async (id) => {
    if (!id) return;
    setDetailLoading(true);
    try {
      const d = await staffGetPersonaggioDetail(id, onLogout);
      setDetail(d);
      const mem = await staffGetCarriereMemberships(onLogout);
      const all = Array.isArray(mem) ? mem : mem?.results || [];
      setMemberships(all.filter((m) => String(m.personaggio) === String(id)));
    } catch (e) {
      setMessage(e.message || 'Errore caricamento dettaglio');
    } finally {
      setDetailLoading(false);
    }
  }, [onLogout]);

  const { pendingQrConflict, conflictLoading, handleQrScan, confirmConflict, cancelConflict } =
    useStaffQrAssociation({
      onLogout,
      onReload: () => selected && reloadDetail(selected.id),
    });

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetPersonaggi({
        q: filters.q,
        tipo: filters.tipo,
        era: filters.era,
        carriera: filters.carriera,
        morto: filters.morto,
        page: filters.page,
      }, onLogout);
      setListData(data);
    } catch (e) {
      setMessage(e.message || 'Errore caricamento lista');
    } finally {
      setLoading(false);
    }
  }, [filters, onLogout]);

  useEffect(() => {
    loadList();
  }, [loadList]);

  useEffect(() => {
    getEre(onLogout).then((d) => Array.isArray(d) && setEre(d));
    staffGetCarriere(onLogout).then((d) => setCarriere(Array.isArray(d) ? d : d?.results || []));
    staffGetTipiCarriera(onLogout).then((d) => setTipiCarriera(Array.isArray(d) ? d : d?.results || []));
    staffGetCariche(onLogout).then((d) => setCariche(Array.isArray(d) ? d : d?.results || []));
    staffGetOggettiBase(onLogout).then((d) => {
      const list = Array.isArray(d) ? d : d?.results || [];
      setOggettiBase(list.map((ob) => ({
        id: ob.id,
        nome: `${ob.nome} (${ob.tipo_oggetto || 'FIS'})${ob.in_vendita ? '' : ' · non in vendita'}`,
      })));
    });
  }, [onLogout]);

  const openPersonaggio = async (row) => {
    setSelected(row);
    setModalTab('bg');
    setShowQrScan(false);
    setLogs([]);
    setCreazioneProposte(null);
    loadOggettiSenzaPosizione();
    await reloadDetail(row.id);
  };

  const closeModal = () => {
    setSelected(null);
    setDetail(null);
    setShowQrScan(false);
    setMembershipForm(null);
  };

  const handleSaveFields = async (fields) => {
    if (!detail?.id) return;
    setSaving(true);
    setMessage('');
    try {
      const updated = await staffPatchPersonaggio(detail.id, fields, onLogout);
      setDetail(updated);
      setMessage('Salvato.');
      await loadList();
    } catch (e) {
      setMessage(e.message || 'Errore salvataggio');
    } finally {
      setSaving(false);
    }
  };

  const handleAddResources = async () => {
    if (!detail?.id) return;
    try {
      await staffAddResourcesToPersonaggio(
        detail.id,
        resourceForm.tipo,
        Number(resourceForm.amount),
        resourceForm.reason,
        onLogout,
      );
      await reloadDetail(detail.id);
      setMessage('Risorse aggiornate.');
    } catch (e) {
      setMessage(e.message || 'Errore risorse');
    }
  };

  const handlePoolAdjust = async (sigla) => {
    const row = poolInputs[sigla] || {};
    const delta = parseInt(row.delta, 10);
    if (Number.isNaN(delta) || delta === 0) {
      alert('Variazione non valida.');
      return;
    }
    try {
      await staffIncrementaRisorsaPool(
        detail.id,
        sigla,
        row.motivo || resourceForm.reason,
        onLogout,
        delta,
      );
      await reloadDetail(detail.id);
      setMessage(`Pool ${sigla} aggiornato.`);
    } catch (e) {
      setMessage(e.message || 'Errore pool');
    }
  };

  const saveMembership = async (form) => {
    try {
      const payload = {
        personaggio: detail.id,
        carriera: form.carriera || form.carriera_id,
        tipo_carriera: form.tipo_carriera || form.tipo_carriera_id,
        carica: form.carica || form.carica_id || null,
        data_da: form.data_da || undefined,
        data_a: form.data_a || null,
        visibile_social: form.visibile_social !== false,
      };
      if (form.id) await staffUpdateCarriereMembership(form.id, payload, onLogout);
      else await staffCreateCarriereMembership({ ...payload, chiudi_korp_precedenti: !!form.chiudi_korp_precedenti }, onLogout);
      setMembershipForm(null);
      await reloadDetail(detail.id);
      setMessage('Appartenenza salvata.');
    } catch (e) {
      setMessage(e.message || 'Errore membership');
    }
  };

  const caricheFiltrate = useMemo(() => {
    const cid = membershipForm?.carriera || membershipForm?.carriera_id;
    if (!cid) return cariche;
    return cariche.filter((c) => String(c.carriera) === String(cid) || String(c.carriera_id) === String(cid));
  }, [cariche, membershipForm]);

  const totalPages = Math.max(1, Math.ceil((listData.count || 0) / 40));

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      <div className="p-4 border-b border-gray-800 space-y-3">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <Users size={22} className="text-teal-400" />
          Personaggi
        </h2>
        <div className="flex flex-wrap gap-2 items-end">
          <div className="flex-1 min-w-[180px]">
            <label className="text-xs text-gray-500 block mb-1">Cerca</label>
            <div className="relative">
              <Search size={14} className="absolute left-2 top-2.5 text-gray-500" />
              <input
                className="w-full bg-gray-800 border border-gray-700 rounded pl-8 pr-2 py-1.5 text-sm"
                placeholder="Nome, utente, costume…"
                value={filters.q}
                onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value, page: 1 }))}
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Tipo</label>
            <select
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm"
              value={filters.tipo}
              onChange={(e) => setFilters((f) => ({ ...f, tipo: e.target.value, page: 1 }))}
            >
              <option value="all">Tutti</option>
              <option value="pg">PG (giocanti)</option>
              <option value="png">PNG</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Era</label>
            <select
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm max-w-[140px]"
              value={filters.era}
              onChange={(e) => setFilters((f) => ({ ...f, era: e.target.value, page: 1 }))}
            >
              <option value="">Tutte</option>
              {ere.map((era) => (
                <option key={era.id} value={era.id}>{era.nome}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">KORP / Carriera</label>
            <select
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm max-w-[160px]"
              value={filters.carriera}
              onChange={(e) => setFilters((f) => ({ ...f, carriera: e.target.value, page: 1 }))}
            >
              <option value="">Tutte</option>
              {carriere.map((c) => (
                <option key={c.id} value={c.id}>{c.nome}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Stato</label>
            <select
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm"
              value={filters.morto}
              onChange={(e) => setFilters((f) => ({ ...f, morto: e.target.value, page: 1 }))}
            >
              <option value="vivo">Vivi</option>
              <option value="morto">Morti</option>
              <option value="all">Tutti</option>
            </select>
          </div>
          <button
            type="button"
            onClick={() => loadList()}
            className="px-3 py-1.5 bg-teal-700 hover:bg-teal-600 rounded text-sm font-bold"
          >
            Aggiorna
          </button>
        </div>
        {message && !selected && (
          <p className="text-sm text-teal-300">{message}</p>
        )}
      </div>

      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Caricamento…</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-800 sticky top-0">
              <tr className="text-left text-gray-400 text-xs uppercase">
                <th className="p-2">Nome</th>
                <th className="p-2">Tipo</th>
                <th className="p-2">Proprietario</th>
                <th className="p-2">Era</th>
                <th className="p-2">KORP / Carriere</th>
                <th className="p-2">QR</th>
                <th className="p-2 text-right">CR</th>
              </tr>
            </thead>
            <tbody>
              {(listData.results || []).map((row) => (
                <tr
                  key={row.id}
                  onClick={() => openPersonaggio(row)}
                  className="border-b border-gray-800 hover:bg-gray-800/60 cursor-pointer"
                >
                  <td className="p-2 font-bold text-white">
                    {row.data_morte && <Skull size={12} className="inline mr-1 text-red-400" />}
                    {row.nome}
                  </td>
                  <td className="p-2 text-gray-400">{row.giocante ? 'PG' : 'PNG'}</td>
                  <td className="p-2 text-gray-300">{row.proprietario_nome || row.proprietario_username}</td>
                  <td className="p-2 text-gray-400">{row.era_nome || '—'}</td>
                  <td className="p-2 text-gray-400 text-xs">{(row.korp_attivi || []).join(', ') || '—'}</td>
                  <td className="p-2 font-mono text-xs text-indigo-300">{row.qrcode_id || '—'}</td>
                  <td className="p-2 text-right text-amber-300">{row.crediti}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="p-3 border-t border-gray-800 flex justify-between items-center text-sm">
        <button
          type="button"
          disabled={!listData.previous}
          onClick={() => setFilters((f) => ({ ...f, page: Math.max(1, f.page - 1) }))}
          className="px-3 py-1 bg-gray-800 rounded disabled:opacity-30"
        >
          Indietro
        </button>
        <span className="text-gray-500">Pagina {filters.page} / {totalPages} · {listData.count ?? 0} personaggi</span>
        <button
          type="button"
          disabled={!listData.next}
          onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
          className="px-3 py-1 bg-gray-800 rounded disabled:opacity-30"
        >
          Avanti
        </button>
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-2 md:p-4">
          <div className="w-full max-w-5xl max-h-[95vh] bg-gray-900 border border-gray-700 rounded-xl flex flex-col">
            <div className="p-4 border-b border-gray-700 flex justify-between items-start gap-3">
              <div>
                <h3 className="text-lg font-bold text-white">{detail?.nome || selected.nome}</h3>
                <p className="text-xs text-gray-400">
                  {detail?.proprietario_nome} · {detail?.tipologia_nome} · {detail?.era_nome || '—'}
                </p>
              </div>
              <button type="button" onClick={closeModal}><X className="text-gray-400" /></button>
            </div>

            <div className="px-4 pt-2 flex flex-wrap gap-1 border-b border-gray-800">
              {TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setModalTab(id)}
                  className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
                    modalTab === id ? 'bg-teal-700 text-white' : 'bg-gray-800 text-gray-400'
                  }`}
                >
                  <Icon size={12} />
                  {label}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {detailLoading || !detail ? (
                <div className="flex justify-center py-12"><Loader2 className="animate-spin text-teal-400" /></div>
              ) : (
                <>
                  {message && <p className="text-sm text-teal-300 mb-3">{message}</p>}

                  {modalTab === 'bg' && (
                    <div className="space-y-4">
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Nome</label>
                        <input
                          className="w-full bg-gray-800 border border-gray-700 rounded p-2"
                          value={detail.nome || ''}
                          onChange={(e) => setDetail((d) => ({ ...d, nome: e.target.value }))}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Background (visibile al giocatore)</label>
                        <RichTextEditor
                          value={detail.testo || ''}
                          onChange={(html) => setDetail((d) => ({ ...d, testo: html }))}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Appunti costume</label>
                        <textarea
                          className="w-full bg-gray-800 border border-gray-700 rounded p-2 min-h-[80px]"
                          value={detail.costume || ''}
                          onChange={(e) => setDetail((d) => ({ ...d, costume: e.target.value }))}
                        />
                      </div>
                      <StaffCostumePhotosSection
                        personaggioId={detail.id}
                        fotoTruccoUrl={detail.foto_trucco_url}
                        fotoOutfitUrl={detail.foto_outfit_url}
                        onLogout={onLogout}
                        disabled={saving}
                        onUpdated={(urls) => setDetail((d) => ({ ...d, ...urls }))}
                      />
                      {detail.avatar_url && (
                        <img src={resolveMediaUrl(detail.avatar_url)} alt="" className="w-20 h-20 rounded-full object-cover border border-gray-600" />
                      )}
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => handleSaveFields({ nome: detail.nome, testo: detail.testo, costume: detail.costume })}
                        className="px-4 py-2 bg-teal-700 rounded font-bold text-sm disabled:opacity-50"
                      >
                        Salva BG / anagrafica
                      </button>
                    </div>
                  )}

                  {modalTab === 'qr' && (
                    <div className="space-y-4">
                      <div className="bg-gray-800 rounded p-3 border border-gray-700">
                        <p className="text-sm text-gray-300">
                          QR associato:{' '}
                          <span className="font-mono text-indigo-300">{detail.qrcode_id || 'nessuno'}</span>
                        </p>
                        {detail.qrcode_testo && (
                          <p className="text-xs text-gray-500 mt-1">{detail.qrcode_testo}</p>
                        )}
                      </div>
                      {!showQrScan ? (
                        <button
                          type="button"
                          onClick={() => setShowQrScan(true)}
                          className="px-4 py-2 bg-indigo-700 rounded font-bold text-sm"
                        >
                          Scansiona / associa QR
                        </button>
                      ) : (
                        <div className="border border-gray-700 rounded-lg overflow-hidden">
                          <StaffQrTab
                            onLogout={onLogout}
                            onScanSuccess={(qrId) => handleQrScan(detail.id, qrId, {
                              closeScan: () => setShowQrScan(false),
                              onMessage: setMessage,
                            })}
                          />
                        </div>
                      )}
                      {pendingQrConflict && (
                        <div className="bg-amber-900/30 border border-amber-700 rounded p-3 text-sm">
                          <p className="mb-2">QR già associato altrove. Forzare?</p>
                          <div className="flex gap-2">
                            <button type="button" onClick={() => confirmConflict(setMessage)} disabled={conflictLoading} className="px-3 py-1 bg-amber-700 rounded text-xs">Forza</button>
                            <button type="button" onClick={cancelConflict} className="px-3 py-1 bg-gray-700 rounded text-xs">Annulla</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {modalTab === 'membership' && (
                    <div className="space-y-3">
                      <button
                        type="button"
                        onClick={() => setMembershipForm({
                          personaggio: detail.id,
                          tipo_carriera: tipiCarriera.find((t) => t.codice === 'korp')?.id,
                          chiudi_korp_precedenti: true,
                        })}
                        className="flex items-center gap-1 px-3 py-1.5 bg-violet-700 rounded text-sm font-bold"
                      >
                        <Plus size={14} /> Nuova appartenenza
                      </button>
                      <ul className="space-y-2">
                        {(memberships.length ? memberships : detail.carriere_membership || []).map((m) => (
                          <li key={m.id} className="bg-gray-800 border border-gray-700 rounded p-2 flex justify-between text-sm">
                            <span>
                              <strong>{m.carriera_nome}</strong>
                              {m.carica_nome ? ` · ${m.carica_nome}` : ''}
                              <span className="text-gray-500 ml-2">{m.data_a ? 'Chiusa' : 'Attiva'}</span>
                            </span>
                            <div className="flex gap-2">
                              <button type="button" className="text-xs text-indigo-400" onClick={() => setMembershipForm(m)}>Modifica</button>
                              {m.id && (
                                <button
                                  type="button"
                                  className="text-xs text-red-400"
                                  onClick={async () => {
                                    if (!window.confirm('Eliminare appartenenza?')) return;
                                    await staffDeleteCarriereMembership(m.id, onLogout);
                                    await reloadDetail(detail.id);
                                  }}
                                >
                                  Elimina
                                </button>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                      {membershipForm && (
                        <div className="border border-violet-800 rounded p-3 space-y-2 bg-violet-950/20">
                          <SearchableSelect
                            options={carriere}
                            value={membershipForm.carriera || membershipForm.carriera_id}
                            onChange={(v) => setMembershipForm((f) => ({ ...f, carriera: v, carriera_id: v }))}
                            placeholder="Carriera / KORP"
                          />
                          <SearchableSelect
                            options={tipiCarriera}
                            value={membershipForm.tipo_carriera || membershipForm.tipo_carriera_id}
                            onChange={(v) => setMembershipForm((f) => ({ ...f, tipo_carriera: v, tipo_carriera_id: v }))}
                            placeholder="Tipo"
                          />
                          <SearchableSelect
                            options={caricheFiltrate}
                            value={membershipForm.carica || membershipForm.carica_id}
                            onChange={(v) => setMembershipForm((f) => ({ ...f, carica: v, carica_id: v }))}
                            placeholder="Carica (opz.)"
                          />
                          <label className="flex items-center gap-2 text-xs text-gray-400">
                            <input
                              type="checkbox"
                              checked={!!membershipForm.chiudi_korp_precedenti}
                              onChange={(e) => setMembershipForm((f) => ({ ...f, chiudi_korp_precedenti: e.target.checked }))}
                            />
                            Chiudi KORP precedenti
                          </label>
                          <div className="flex gap-2">
                            <button type="button" onClick={() => saveMembership(membershipForm)} className="px-3 py-1 bg-violet-700 rounded text-sm">Salva</button>
                            <button type="button" onClick={() => setMembershipForm(null)} className="px-3 py-1 bg-gray-700 rounded text-sm">Annulla</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {modalTab === 'risorse' && (
                    <div className="space-y-6">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="bg-gray-800 rounded p-3 border border-gray-700">
                          <span className="text-gray-400">Crediti</span>
                          <p className="text-2xl font-bold text-amber-300">{detail.crediti}</p>
                        </div>
                        <div className="bg-gray-800 rounded p-3 border border-gray-700">
                          <span className="text-gray-400">Punti caratteristica</span>
                          <p className="text-2xl font-bold text-blue-300">{detail.punti_caratteristica}</p>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 items-end">
                        <select
                          className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm"
                          value={resourceForm.tipo}
                          onChange={(e) => setResourceForm((f) => ({ ...f, tipo: e.target.value }))}
                        >
                          <option value="crediti">Crediti</option>
                          <option value="pc">Punti caratteristica</option>
                        </select>
                        <input
                          type="number"
                          className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm w-24"
                          value={resourceForm.amount}
                          onChange={(e) => setResourceForm((f) => ({ ...f, amount: e.target.value }))}
                        />
                        <input
                          className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm flex-1 min-w-[120px]"
                          placeholder="Motivo"
                          value={resourceForm.reason}
                          onChange={(e) => setResourceForm((f) => ({ ...f, reason: e.target.value }))}
                        />
                        <button type="button" onClick={handleAddResources} className="px-3 py-1.5 bg-amber-700 rounded text-sm font-bold">Applica</button>
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-gray-300 mb-2">Pool risorse</h4>
                        <div className="space-y-2">
                          {(detail.risorse_pool_ui || []).map((pool) => (
                            <div key={pool.sigla} className="bg-gray-800 border border-gray-700 rounded p-2 flex flex-wrap gap-2 items-center text-sm">
                              <span className="font-bold w-16">{pool.sigla}</span>
                              <span className="text-gray-400">{pool.valore_corrente} / {pool.valore_max}</span>
                              <input
                                type="number"
                                placeholder="Δ"
                                className="w-16 bg-gray-900 border border-gray-600 rounded px-1 py-0.5 text-xs"
                                value={poolInputs[pool.sigla]?.delta || ''}
                                onChange={(e) => setPoolInputs((p) => ({
                                  ...p,
                                  [pool.sigla]: { ...p[pool.sigla], delta: e.target.value },
                                }))}
                              />
                              <button
                                type="button"
                                onClick={() => handlePoolAdjust(pool.sigla)}
                                className="px-2 py-0.5 bg-teal-800 rounded text-xs"
                              >
                                Applica
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {modalTab === 'inventario' && (
                    <div className="space-y-4">
                      <div className="bg-gray-800/80 border border-teal-900/50 rounded-lg p-3 space-y-2">
                        <p className="text-xs text-gray-400">
                          Crea un&apos;istanza da <strong>oggetto base</strong> (template) e mettila nell&apos;inventario.
                          Funziona anche se il template è <em>non acquistabile</em> in Accademia.
                        </p>
                        <SearchableSelect
                          options={oggettiBase}
                          value={oggettoBaseDraft.id}
                          onChange={(v) => setOggettoBaseDraft((f) => ({ ...f, id: v }))}
                          placeholder="Seleziona oggetto base…"
                        />
                        <input
                          className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm"
                          placeholder="Motivo (log PG)"
                          value={oggettoBaseDraft.motivo}
                          onChange={(e) => setOggettoBaseDraft((f) => ({ ...f, motivo: e.target.value }))}
                        />
                        <button
                          type="button"
                          disabled={!oggettoBaseDraft.id}
                          onClick={async () => {
                            try {
                              const res = await staffCreaOggettoDaBasePerPersonaggio(
                                detail.id,
                                oggettoBaseDraft.id,
                                oggettoBaseDraft.motivo,
                                onLogout,
                              );
                              setMessage(res.detail || 'Oggetto creato.');
                              await reloadDetail(detail.id);
                            } catch (e) {
                              setMessage(e.message || 'Errore creazione oggetto');
                            }
                          }}
                          className="px-4 py-2 bg-teal-700 rounded font-bold text-sm disabled:opacity-40"
                        >
                          Crea istanza in inventario
                        </button>
                      </div>
                      <div className="bg-gray-800/80 border border-indigo-900/50 rounded-lg p-3 space-y-2">
                        <p className="text-xs text-gray-400">
                          Associa un&apos;istanza <strong>oggetto</strong> già esistente (es. senza posizione o da altro inventario).
                        </p>
                        <SearchableSelect
                          options={oggettiSenzaPosizione}
                          value={oggettoEsistenteDraft.id}
                          onChange={(v) => setOggettoEsistenteDraft((f) => ({ ...f, id: v }))}
                          placeholder="Oggetti senza inventario…"
                        />
                        <div className="flex gap-2">
                          <input
                            className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm font-mono"
                            placeholder="Oppure ID oggetto"
                            value={manualOggettoId}
                            onChange={(e) => setManualOggettoId(e.target.value)}
                          />
                          <button
                            type="button"
                            className="px-2 py-1 bg-gray-700 rounded text-xs"
                            onClick={async () => {
                              const id = parseInt(manualOggettoId.trim(), 10);
                              if (Number.isNaN(id)) {
                                setMessage('ID oggetto non valido.');
                                return;
                              }
                              try {
                                const o = await staffGetOggettoStaff(id, onLogout);
                                setOggettiSenzaPosizione((prev) => {
                                  if (prev.some((x) => String(x.id) === String(id))) return prev;
                                  return [...prev, { id: o.id, nome: `${o.nome} (#${o.id}, ${o.tipo_oggetto || '?'})` }];
                                });
                                setOggettoEsistenteDraft((f) => ({ ...f, id: o.id }));
                                setManualOggettoId('');
                              } catch (e) {
                                setMessage(e.message || 'Oggetto non trovato');
                              }
                            }}
                          >
                            Cerca ID
                          </button>
                        </div>
                        <input
                          className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm"
                          placeholder="Motivo (log PG)"
                          value={oggettoEsistenteDraft.motivo}
                          onChange={(e) => setOggettoEsistenteDraft((f) => ({ ...f, motivo: e.target.value }))}
                        />
                        <button
                          type="button"
                          disabled={!oggettoEsistenteDraft.id}
                          onClick={async () => {
                            try {
                              const res = await staffPersonaggioAggiungiOggetto(
                                detail.id,
                                oggettoEsistenteDraft.id,
                                oggettoEsistenteDraft.motivo,
                                onLogout,
                              );
                              setMessage(res.detail || 'Oggetto associato.');
                              setOggettoEsistenteDraft({ id: '', motivo: 'Assegnazione staff' });
                              await reloadDetail(detail.id);
                              await loadOggettiSenzaPosizione();
                            } catch (e) {
                              setMessage(e.message || 'Errore associazione oggetto');
                            }
                          }}
                          className="px-4 py-2 bg-indigo-700 rounded font-bold text-sm disabled:opacity-40"
                        >
                          Associa oggetto esistente
                        </button>
                        <button type="button" onClick={loadOggettiSenzaPosizione} className="text-xs text-gray-500 underline">
                          Aggiorna elenco senza posizione
                        </button>
                      </div>
                      <p className="text-xs text-gray-500">
                        Inventario ({detail.oggetti_inventario?.length || 0} oggetti, max 80).
                      </p>
                      <input
                        className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs"
                        placeholder="Motivo predefinito rimuovi/distruggi"
                        value={inventarioMotivo}
                        onChange={(e) => setInventarioMotivo(e.target.value)}
                      />
                      <ul className="space-y-1 max-h-[50vh] overflow-y-auto text-sm">
                        {(detail.oggetti_inventario || []).map((o) => (
                          <li key={o.id} className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 flex flex-wrap items-center justify-between gap-2">
                            <span>
                              {o.nome}
                              <span className="text-gray-500 font-mono text-xs ml-2">#{o.id} · {o.tipo_oggetto}</span>
                            </span>
                            <span className="flex gap-1">
                              <button
                                type="button"
                                className="px-2 py-0.5 bg-gray-700 rounded text-xs"
                                onClick={async () => {
                                  if (!window.confirm(`Rimuovere «${o.nome}» dall'inventario (l'oggetto resta nel DB)?`)) return;
                                  try {
                                    const res = await staffPersonaggioRimuoviOggetto(
                                      detail.id, o.id, inventarioMotivo, onLogout,
                                    );
                                    setMessage(res.detail || 'Oggetto rimosso.');
                                    await reloadDetail(detail.id);
                                    await loadOggettiSenzaPosizione();
                                  } catch (e) {
                                    setMessage(e.message || 'Errore rimozione');
                                  }
                                }}
                              >
                                Rimuovi
                              </button>
                              <button
                                type="button"
                                className="px-2 py-0.5 bg-red-900/60 border border-red-800 rounded text-xs"
                                onClick={async () => {
                                  if (!window.confirm(`Distruggere definitivamente «${o.nome}»?`)) return;
                                  try {
                                    const res = await staffPersonaggioDistruggiOggetto(
                                      detail.id, o.id, inventarioMotivo, onLogout,
                                    );
                                    setMessage(res.detail || 'Oggetto distrutto.');
                                    await reloadDetail(detail.id);
                                    await loadOggettiSenzaPosizione();
                                  } catch (e) {
                                    setMessage(e.message || 'Errore distruzione');
                                  }
                                }}
                              >
                                Distruggi
                              </button>
                            </span>
                          </li>
                        ))}
                        {!detail.oggetti_inventario?.length && (
                          <li className="text-gray-500 text-sm">Inventario vuoto.</li>
                        )}
                      </ul>
                    </div>
                  )}

                  {modalTab === 'instafame' && (
                    <div className="space-y-4 text-sm">
                      <label className="flex items-center gap-2">
                        <span className="text-gray-400 w-32">Peso influencer</span>
                        <input
                          type="number"
                          min={1}
                          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 w-24"
                          value={detail.peso_influencer ?? 1}
                          onChange={(e) => setDetail((d) => ({ ...d, peso_influencer: e.target.value }))}
                        />
                      </label>
                      <label className="flex items-center gap-2">
                        <span className="text-gray-400 w-32">Badge</span>
                        <select
                          className="bg-gray-800 border border-gray-700 rounded px-2 py-1"
                          value={detail.badge_instafame || ''}
                          onChange={(e) => setDetail((d) => ({ ...d, badge_instafame: e.target.value }))}
                        >
                          <option value="">Nessuno</option>
                          <option value="GOLD">Gold</option>
                          <option value="DIAMOND">Diamond</option>
                          <option value="PREMIUM">Premium</option>
                        </select>
                      </label>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={saving}
                          onClick={() => handleSaveFields({
                            peso_influencer: Math.max(1, parseInt(detail.peso_influencer, 10) || 1),
                            badge_instafame: detail.badge_instafame || '',
                          })}
                          className="px-4 py-2 bg-teal-700 rounded font-bold text-sm disabled:opacity-50"
                        >
                          Salva InstaFame
                        </button>
                        <button
                          type="button"
                          onClick={async () => {
                            await staffRigeneraLikePersonaggio(detail.id, onLogout);
                            setMessage('Like InstaFame rigenerati.');
                          }}
                          className="px-4 py-2 bg-violet-800 rounded font-bold text-sm"
                        >
                          Rigenera like storici
                        </button>
                      </div>
                    </div>
                  )}

                  {modalTab === 'watch' && (
                    <div className="space-y-4 text-sm">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={!!detail.watch_enabled}
                          onChange={(e) => setDetail((d) => ({ ...d, watch_enabled: e.target.checked }))}
                        />
                        Watch abilitato per questo personaggio
                      </label>
                      {detail.watch_binding ? (
                        <div className="bg-gray-800 border border-gray-700 rounded p-3 space-y-1">
                          <p><span className="text-gray-500">Device:</span> {detail.watch_binding.device_id}</p>
                          <p><span className="text-gray-500">Firmware:</span> {detail.watch_binding.firmware_version || '—'}</p>
                          <p><span className="text-gray-500">Ultimo contatto:</span> {detail.watch_binding.last_seen_at || '—'}</p>
                        </div>
                      ) : (
                        <p className="text-gray-500">Nessun dispositivo associato.</p>
                      )}
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => handleSaveFields({ watch_enabled: !!detail.watch_enabled })}
                        className="px-4 py-2 bg-teal-700 rounded font-bold text-sm disabled:opacity-50"
                      >
                        Salva Watch
                      </button>
                    </div>
                  )}

                  {modalTab === 'log' && (
                    <div className="space-y-2">
                      <button
                        type="button"
                        onClick={() => loadLogs(detail.id)}
                        className="px-3 py-1 bg-gray-700 rounded text-xs"
                      >
                        {logsLoading ? 'Caricamento…' : 'Carica log'}
                      </button>
                      <ul className="space-y-1 max-h-[50vh] overflow-y-auto text-sm">
                        {logs.map((entry, idx) => (
                          <li key={idx} className="bg-gray-800 border border-gray-700 rounded px-2 py-1">
                            <span className="text-gray-500 text-xs">{entry.data}</span>
                            <p>{entry.testo_log}</p>
                          </li>
                        ))}
                        {!logs.length && !logsLoading && (
                          <li className="text-gray-500">Nessun log caricato.</li>
                        )}
                      </ul>
                    </div>
                  )}

                  {modalTab === 'eventi' && (
                    <ul className="space-y-2 text-sm max-h-[50vh] overflow-y-auto">
                      {(detail.eventi_partecipati || []).map((ev) => (
                        <li key={ev.id} className="bg-gray-800 border border-gray-700 rounded p-2">
                          <strong>{ev.titolo || ev.nome}</strong>
                          <p className="text-xs text-gray-500">
                            {ev.data_inizio}{ev.data_fine ? ` → ${ev.data_fine}` : ''}
                          </p>
                        </li>
                      ))}
                      {!detail.eventi_partecipati?.length && (
                        <li className="text-gray-500">Nessun evento registrato.</li>
                      )}
                    </ul>
                  )}

                  {modalTab === 'messaggio' && (
                    <div className="space-y-3 text-sm">
                      <input
                        className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5"
                        placeholder="Titolo"
                        value={msgForm.titolo}
                        onChange={(e) => setMsgForm((f) => ({ ...f, titolo: e.target.value }))}
                      />
                      <textarea
                        className="w-full bg-gray-800 border border-gray-700 rounded p-2 min-h-[120px]"
                        placeholder="Testo del messaggio al giocatore"
                        value={msgForm.testo}
                        onChange={(e) => setMsgForm((f) => ({ ...f, testo: e.target.value }))}
                      />
                      <button
                        type="button"
                        onClick={async () => {
                          await staffSendMessageToPersonaggio(detail.id, msgForm.titolo, msgForm.testo, onLogout);
                          setMsgForm({ titolo: '', testo: '' });
                          setMessage('Messaggio inviato.');
                        }}
                        className="px-4 py-2 bg-emerald-700 rounded font-bold"
                      >
                        Invia messaggio
                      </button>
                    </div>
                  )}

                  {modalTab === 'creazione' && (
                    <div className="space-y-3 text-sm">
                      <p className="text-gray-500">
                        Bozze salvate dal wizard di creazione guidata per questo personaggio.
                      </p>
                      <button
                        type="button"
                        onClick={() => loadCreazioneProposte(detail.id)}
                        className="px-3 py-1 bg-violet-800 rounded text-xs"
                      >
                        Carica proposte wizard
                      </button>
                      {creazioneProposte?.effetti?.length > 0 ? (
                        <pre className="bg-gray-950 border border-gray-700 rounded p-2 text-xs overflow-auto max-h-48">
                          {JSON.stringify(creazioneProposte.effetti, null, 2)}
                        </pre>
                      ) : (
                        <p className="text-gray-500">Nessuna bozza caricata o salvata.</p>
                      )}
                      <p className="text-xs text-gray-600">
                        Per applicare il flusso completo usa il tool «Creazione guidata PG» nella dashboard staff.
                      </p>
                    </div>
                  )}

                  {modalTab === 'note' && (
                    <div className="space-y-3">
                      <p className="text-xs text-gray-500">Visibile solo allo staff — non mostrato al giocatore.</p>
                      <textarea
                        className="w-full bg-gray-800 border border-gray-700 rounded p-3 min-h-[200px] text-sm"
                        value={detail.note_master || ''}
                        onChange={(e) => setDetail((d) => ({ ...d, note_master: e.target.value }))}
                      />
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => handleSaveFields({ note_master: detail.note_master || '' })}
                        className="px-4 py-2 bg-teal-700 rounded font-bold text-sm"
                      >
                        Salva note
                      </button>
                    </div>
                  )}

                  {modalTab === 'azioni' && (
                    <div className="space-y-3">
                      <button
                        type="button"
                        className="w-full flex items-center gap-2 px-4 py-3 bg-gray-800 border border-gray-700 rounded hover:bg-gray-750 text-sm"
                        onClick={async () => {
                          if (!window.confirm('Reset completo del personaggio?')) return;
                          await resetPersonaggio(detail.id, 'Reset da hub staff personaggi', onLogout);
                          await reloadDetail(detail.id);
                          setMessage('Reset eseguito.');
                        }}
                      >
                        <RotateCcw size={16} /> Reset personaggio
                      </button>
                      {!detail.data_morte ? (
                        <button
                          type="button"
                          className="w-full flex items-center gap-2 px-4 py-3 bg-red-900/40 border border-red-800 rounded text-sm"
                          onClick={async () => {
                            if (!window.confirm('Segnare come morto?')) return;
                            await staffKillPersonaggio(detail.id, onLogout);
                            await reloadDetail(detail.id);
                            await loadList();
                          }}
                        >
                          <Skull size={16} /> Segna morto
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="w-full flex items-center gap-2 px-4 py-3 bg-green-900/40 border border-green-800 rounded text-sm"
                          onClick={async () => {
                            await staffRevivePersonaggio(detail.id, onLogout);
                            await reloadDetail(detail.id);
                            await loadList();
                          }}
                        >
                          <Heart size={16} /> Rivivi
                        </button>
                      )}
                      <button
                        type="button"
                        className="w-full flex items-center gap-2 px-4 py-3 bg-amber-900/30 border border-amber-800 rounded text-sm"
                        onClick={async () => {
                          if (!window.confirm('Archiviare questo personaggio? Potrai ripristinarlo da «Personaggi eliminati».')) return;
                          await deletePersonaggio(detail.id, onLogout);
                          closeModal();
                          await loadList();
                          setMessage('Personaggio archiviato.');
                        }}
                      >
                        <Archive size={16} /> Archivia personaggio
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PersonaggiStaffManager;
