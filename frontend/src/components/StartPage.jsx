import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Edit3, LogOut, Plus, Sparkles, BookOpen, Shield, ArrowRight, Lock, Star } from 'lucide-react';
import {
  createPersonaggio,
  getArcanaPasswordStatus,
  getEre,
  getPersonaggiEditList,
  updatePersonaggio,
  fetchAuthenticated,
  resolveMediaUrl,
  socialUpdateMyProfile,
} from '../api';
import { useCharacter } from './CharacterContext';
import PasswordChangeModal from './PasswordChangeModal';
import RichTextEditor from './RichTextEditor';

export default function StartPage({ onLogout, onSwitchToMaster }) {
  const navigate = useNavigate();
  const { selectCharacter, fetchPersonaggi, isStaff, isMaster, preferredCharacterId, setPreferredCharacter } = useCharacter();

  const [characters, setCharacters] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [ere, setEre] = useState([]);
  const [segni, setSegni] = useState([]);

  const [showReminder, setShowReminder] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [playerName, setPlayerName] = useState('Giocatore');
  const [lastCharacterId, setLastCharacterId] = useState(() => localStorage.getItem('kor35_last_char_id') || '');
  const [adStatus, setAdStatus] = useState({
    code: 'not_logged',
    label: 'Non loggato con AD',
    color: 'red',
  });

  const [showEditor, setShowEditor] = useState(false);
  const [isCreateMode, setIsCreateMode] = useState(true);
  const [formData, setFormData] = useState({
    id: null,
    nome: '',
    testo: '',
    era: '',
    prefettura: '',
    prefettura_esterna: false,
  });
  const [editPermissions, setEditPermissions] = useState({ can_edit_era: true, can_edit_razza: true });
  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreviewBlob, setAvatarPreviewBlob] = useState(null);
  const [avatarRemoteUrl, setAvatarRemoteUrl] = useState(null);

  useEffect(() => {
    if (!avatarFile) {
      setAvatarPreviewBlob(null);
      return undefined;
    }
    const u = URL.createObjectURL(avatarFile);
    setAvatarPreviewBlob(u);
    return () => URL.revokeObjectURL(u);
  }, [avatarFile]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setIsLoading(true);
      try {
        const [pgs, ereList, segniList, pwdStatus, me] = await Promise.all([
          getPersonaggiEditList(onLogout, { mineOnly: true }),
          getEre(onLogout),
          fetchAuthenticated('/api/personaggi/api/segni-zodiacali/', { method: 'GET' }, onLogout),
          getArcanaPasswordStatus(onLogout),
          fetchAuthenticated('/api/personaggi/api/user/me/', { method: 'GET' }, onLogout),
        ]);
        if (!mounted) return;
        const ordered = Array.isArray(pgs)
          ? [...pgs].sort((a, b) => String(a?.nome || '').localeCompare(String(b?.nome || '')))
          : [];
        setCharacters(ordered);
        setEre(Array.isArray(ereList) ? ereList : []);
        setSegni(Array.isArray(segniList) ? segniList : []);
        setShowReminder(!!pwdStatus?.show_reminder);
        setAdStatus(
          pwdStatus?.ad_status || {
            code: 'not_logged',
            label: 'Non loggato con AD',
            color: 'red',
          }
        );
        const fullName = `${me?.first_name || ''} ${me?.last_name || ''}`.trim();
        setPlayerName(fullName || me?.username || 'Giocatore');
      } catch (_err) {
        if (mounted) setCharacters([]);
        setAdStatus({
          code: 'not_logged',
          label: 'Non loggato con AD',
          color: 'red',
        });
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [onLogout]);

  const selectedEra = useMemo(
    () => ere.find((e) => String(e.id) === String(formData.era)),
    [ere, formData.era]
  );
  const allPrefetture = useMemo(
    () => ere.flatMap((era) => (era.prefetture || []).map((p) => ({ ...p, era_ref: era }))),
    [ere]
  );
  const prefettureDisponibili = useMemo(() => {
    if (formData.prefettura_esterna) return allPrefetture;
    return selectedEra?.prefetture || [];
  }, [formData.prefettura_esterna, allPrefetture, selectedEra]);
  const hasMultipleEre = ere.length > 1;

  useEffect(() => {
    if (hasMultipleEre || ere.length !== 1) return;
    const onlyEraId = String(ere[0].id);
    if (String(formData.era || '') === onlyEraId) return;
    setFormData((prev) => ({ ...prev, era: onlyEraId, prefettura: '' }));
  }, [hasMultipleEre, ere, formData.era]);

  const openCreate = () => {
    setIsCreateMode(true);
    setAvatarFile(null);
    setAvatarRemoteUrl(null);
    setFormData({
      id: null,
      nome: '',
      testo: '',
      era: '',
      prefettura: '',
      prefettura_esterna: false,
    });
    setShowEditor(true);
    setEditPermissions({ can_edit_era: true, can_edit_razza: true });
  };

  const openEdit = (char) => {
    setIsCreateMode(false);
    setAvatarFile(null);
    setAvatarRemoteUrl(char.avatar_url || null);
    setFormData({
      id: char.id,
      nome: char.nome || '',
      testo: char.testo || '',
      era: char.era || '',
      prefettura: char.prefettura || '',
      prefettura_esterna: !!char.prefettura_esterna,
    });
    setShowEditor(true);
    setEditPermissions({
      can_edit_era: !!char.can_edit_era,
      can_edit_razza: !!char.can_edit_razza,
    });
  };

  const saveCharacter = async () => {
    const payload = { ...formData };
    if (!payload.era) payload.era = null;
    if (!payload.prefettura) payload.prefettura = null;
    payload.prefettura_esterna = !!payload.prefettura_esterna;
    if (!isCreateMode) {
      if (!editPermissions.can_edit_era) {
        delete payload.era;
        delete payload.prefettura;
        delete payload.prefettura_esterna;
      }
      if (!editPermissions.can_edit_razza) {
        delete payload.nome;
        delete payload.testo;
      }
    }
    try {
      let charId = formData.id;
      if (isCreateMode) {
        delete payload.id;
        const created = await createPersonaggio(payload, onLogout);
        charId = created?.id;
      } else {
        await updatePersonaggio(payload.id, payload, onLogout);
      }
      if (avatarFile && charId) {
        const fd = new FormData();
        fd.append('foto_principale', avatarFile);
        await socialUpdateMyProfile(fd, charId, onLogout);
      }
      const updated = await getPersonaggiEditList(onLogout, { mineOnly: true });
      const ordered = Array.isArray(updated)
        ? [...updated].sort((a, b) => String(a?.nome || '').localeCompare(String(b?.nome || '')))
        : [];
      setCharacters(ordered);
      await fetchPersonaggi();
      setAvatarFile(null);
      setShowEditor(false);
    } catch (err) {
      alert(err?.message || 'Errore salvataggio personaggio');
    }
  };

  const enterCharacter = (char) => {
    selectCharacter(char.id);
    setLastCharacterId(String(char.id));
    navigate('/app/play?tab=home');
  };

  const closeEditor = () => {
    setShowEditor(false);
    setAvatarFile(null);
    setAvatarRemoteUrl(null);
  };

  const modalAvatarSrc = avatarPreviewBlob || (avatarRemoteUrl ? resolveMediaUrl(avatarRemoteUrl) : null);
  const loginMethod = String(localStorage.getItem('kor35_login_method') || 'local').toLowerCase();
  const effectiveAdStatus =
    loginMethod === 'arcana'
      ? adStatus
      : {
          code: 'not_logged',
          label: 'Non loggato con AD',
          color: 'red',
        };
  const adBadgeClass =
    effectiveAdStatus.color === 'green'
      ? 'border-emerald-700 bg-emerald-900/60 text-emerald-200'
      : effectiveAdStatus.color === 'yellow'
      ? 'border-amber-700 bg-amber-950/70 text-amber-200'
      : 'border-red-700 bg-red-950/70 text-red-200';

  return (
    <div className="h-dvh max-h-dvh flex flex-col overflow-hidden bg-gray-900 text-white">
      <div className="flex-1 min-h-0 overflow-y-auto p-4 md:p-6">
      <div className="max-w-6xl mx-auto space-y-5 pb-8">
        <div className="rounded-xl border border-gray-700 bg-gray-800 p-4 md:p-5">
          <h1 className="text-2xl font-black italic text-indigo-400">Benvenuto, {playerName}</h1>
          <p className="text-sm text-gray-300 mt-1">
            Scegli un personaggio, crea un nuovo PG o entra nelle sezioni di gioco.
          </p>
          <div className="mt-3">
            <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold ${adBadgeClass}`}>
              {effectiveAdStatus.label}
            </span>
          </div>
        </div>

        {showReminder && (
          <div className="rounded-xl border border-gray-700 bg-gray-800 p-4 md:p-5">
            <h2 className="text-lg font-bold mb-3">Avvisi</h2>
            <div className="rounded-lg border border-amber-500/60 bg-amber-950/70 p-3 text-amber-100 flex items-center justify-between gap-3">
              <span>Password locale non configurata, per inserirla cliccare qui.</span>
              <button
                onClick={() => setShowPasswordModal(true)}
                className="px-3 py-1.5 rounded bg-amber-400 text-gray-900 font-bold text-xs"
              >
                Configura
              </button>
            </div>
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <button
            onClick={() => navigate('/')}
            className="rounded-xl border border-gray-700 bg-gray-800 p-4 text-left hover:bg-gray-750"
          >
            <BookOpen size={20} className="text-blue-300 mb-2" />
            <div className="font-bold">Wiki</div>
          </button>
          <button
            onClick={() => navigate('/app/social')}
            className="rounded-xl border border-gray-700 bg-gray-800 p-4 text-left hover:bg-gray-750"
          >
            <Sparkles size={20} className="text-pink-300 mb-2" />
            <div className="font-bold">InstaFame</div>
          </button>
          {(isStaff || isMaster) && (
            <button
              onClick={() => onSwitchToMaster('home')}
              className="rounded-xl border border-gray-700 bg-gray-800 p-4 text-left hover:bg-gray-750"
            >
              <Shield size={20} className="text-emerald-300 mb-2" />
              <div className="font-bold">Dashboard Staff</div>
            </button>
          )}
          <button
            onClick={onLogout}
            className="rounded-xl border border-red-900 bg-red-950/40 p-4 text-left hover:bg-red-950/60"
          >
            <LogOut size={20} className="text-red-300 mb-2" />
            <div className="font-bold text-red-100">Logout</div>
          </button>
        </div>

        <div className="rounded-xl border border-gray-700 bg-gray-800 p-4 md:p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold">I tuoi personaggi</h2>
            <div className="flex gap-2">
              <button
                onClick={() => navigate('/app/play?tab=personaggi')}
                className="px-3 py-2 text-xs font-bold rounded bg-indigo-700 hover:bg-indigo-600"
              >
                Gestione personaggi
              </button>
              <button
                onClick={openCreate}
                className="inline-flex items-center gap-1 px-3 py-2 text-xs font-bold rounded bg-emerald-700 hover:bg-emerald-600"
              >
                <Plus size={14} /> Nuovo PG
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="text-gray-400 text-sm">Caricamento personaggi...</div>
          ) : (
            <div className="space-y-3">
              {characters.map((char) => (
                <div
                  key={char.id}
                  className="rounded-lg border border-gray-700 bg-gray-900/40 p-3 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-indigo-800 text-indigo-100 font-black flex items-center justify-center shrink-0 overflow-hidden">
                      {char.avatar_url ? (
                        <img
                          src={resolveMediaUrl(char.avatar_url)}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        (char.nome || '?').charAt(0).toUpperCase()
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="font-bold text-white truncate">{char.nome}</div>
                      <div className="flex gap-1 mt-1">
                        {String(preferredCharacterId || '') === String(char.id) && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-900/70 text-amber-200 border border-amber-700 inline-flex items-center gap-1">
                            <Star size={10} /> Preferito
                          </span>
                        )}
                        {String(lastCharacterId || '') === String(char.id) && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-900/70 text-indigo-200 border border-indigo-700">
                            Ultimo usato
                          </span>
                        )}
                        {char.can_edit_era ? (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-900/70 text-emerald-200 border border-emerald-700">
                            Dati modificabili
                          </span>
                        ) : (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-600 inline-flex items-center gap-1">
                            <Lock size={10} /> Dati bloccati da evento
                          </span>
                        )}
                      </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {char.era_nome || 'Era non impostata'}
                      {char.prefettura_nome
                        ? ` - ${char.prefettura_regione_sigla ? `${char.prefettura_regione_sigla} ` : ''}${char.prefettura_nome}`
                        : ''}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      Segno zodiacale: {char.segno_zodiacale_nome || 'Non assegnato'}
                    </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() =>
                        setPreferredCharacter(
                          String(preferredCharacterId || '') === String(char.id) ? '' : String(char.id)
                        )
                      }
                      className={`p-2 rounded border ${
                        String(preferredCharacterId || '') === String(char.id)
                          ? 'bg-amber-800/60 border-amber-600 text-amber-200'
                          : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
                      }`}
                      title={
                        String(preferredCharacterId || '') === String(char.id)
                          ? 'Rimuovi preferito'
                          : 'Imposta come preferito'
                      }
                    >
                      <Star size={16} />
                    </button>
                    <button
                      onClick={() => openEdit(char)}
                      className="p-2 rounded bg-gray-700 hover:bg-gray-600"
                      title="Modifica dati generali"
                    >
                      <Edit3 size={16} />
                    </button>
                    <button
                      onClick={() => enterCharacter(char)}
                      className="inline-flex items-center gap-1 px-3 py-2 text-xs font-bold rounded bg-indigo-700 hover:bg-indigo-600"
                    >
                      Entra <ArrowRight size={14} />
                    </button>
                  </div>
                </div>
              ))}
              {characters.length === 0 && (
                <div className="text-sm text-gray-400">Nessun personaggio presente. Creane uno per iniziare.</div>
              )}
            </div>
          )}
        </div>
      </div>
      </div>

      {showEditor && (
        <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
          <div className="w-full max-w-3xl bg-gray-800 border border-gray-700 rounded-xl flex flex-col max-h-[95vh]">
            <div className="px-5 py-4 border-b border-gray-700 text-lg font-bold">
              {isCreateMode ? 'Nuovo personaggio' : 'Modifica dati personaggio'}
            </div>
            <div className="p-5 overflow-y-auto space-y-4">
              {!isCreateMode && !editPermissions.can_edit_era && (
                <div className="rounded-lg border border-amber-700 bg-amber-950/60 text-amber-200 p-3 text-sm">
                  I campi Era/Prefettura sono bloccati: il primo evento associato al personaggio e gia iniziato.
                </div>
              )}
              {!isCreateMode && !editPermissions.can_edit_razza && (
                <div className="rounded-lg border border-amber-700 bg-amber-950/60 text-amber-200 p-3 text-sm">
                  Il background non e piu modificabile per questo personaggio.
                </div>
              )}
              <div>
                <label className="text-xs text-gray-400 uppercase">Avatar (InstaFame e schede)</label>
                <div className="mt-2 flex flex-wrap items-center gap-4">
                  <div className="h-20 w-20 rounded-full border border-gray-600 bg-gray-900 overflow-hidden flex items-center justify-center shrink-0">
                    {modalAvatarSrc ? (
                      <img src={modalAvatarSrc} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <span className="text-2xl font-black text-indigo-300">
                        {(formData.nome || '?').charAt(0).toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div>
                    <input
                      type="file"
                      accept="image/*"
                      className="text-sm text-gray-300 file:mr-2 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-indigo-700 file:text-white"
                      onChange={(e) => setAvatarFile(e.target.files?.[0] || null)}
                    />
                    <p className="text-[11px] text-gray-500 mt-1">Usato anche per InstaFame e la scheda personaggio.</p>
                  </div>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 uppercase">Nome</label>
                <input
                  className="mt-1 w-full bg-gray-900 border border-gray-700 rounded p-2"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  disabled={!isCreateMode && !editPermissions.can_edit_razza}
                />
              </div>
              <RichTextEditor
                label="Background"
                value={formData.testo}
                onChange={(val) =>
                  !(!isCreateMode && !editPermissions.can_edit_razza) &&
                  setFormData({ ...formData, testo: val })
                }
              />
              <div className="grid md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 uppercase">Era</label>
                  {hasMultipleEre ? (
                    <select
                      className="mt-1 w-full bg-gray-900 border border-gray-700 rounded p-2"
                      value={formData.era || ''}
                      onChange={(e) =>
                        setFormData({ ...formData, era: e.target.value || '', prefettura: '' })
                      }
                      disabled={!isCreateMode && !editPermissions.can_edit_era}
                    >
                      <option value="">Seleziona era</option>
                      {ere.map((era) => (
                        <option key={era.id} value={era.id}>
                          {era.nome}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="mt-1 w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-gray-200">
                      {ere[0]?.nome || 'Campagna base'}
                    </div>
                  )}
                </div>
                <div>
                  <label className="text-xs text-gray-400 uppercase">Prefettura</label>
                  <select
                    className="mt-1 w-full bg-gray-900 border border-gray-700 rounded p-2"
                    value={formData.prefettura || ''}
                    onChange={(e) => setFormData({ ...formData, prefettura: e.target.value || '' })}
                    disabled={!isCreateMode && !editPermissions.can_edit_era}
                  >
                    <option value="">Seleziona prefettura</option>
                    {prefettureDisponibili.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.regione_sigla ? `${p.regione_sigla} ${p.nome}` : p.nome}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <label className="inline-flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={!!formData.prefettura_esterna}
                  onChange={(e) =>
                    setFormData({ ...formData, prefettura_esterna: e.target.checked, prefettura: '' })
                  }
                  disabled={!isCreateMode && !editPermissions.can_edit_era}
                />
                Prefettura esterna
              </label>
              <div className="text-xs text-gray-400">
                Segni zodiacali disponibili: {segni.length > 0 ? segni.map((s) => s.nome).join(', ') : 'n/d'}
              </div>
            </div>
            <div className="px-5 py-4 border-t border-gray-700 flex justify-end gap-2">
              <button
                type="button"
                onClick={closeEditor}
                className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm"
              >
                Annulla
              </button>
              <button
                onClick={saveCharacter}
                className="px-4 py-2 rounded bg-indigo-700 hover:bg-indigo-600 text-sm font-bold"
              >
                Salva
              </button>
            </div>
          </div>
        </div>
      )}

      <PasswordChangeModal
        isOpen={showPasswordModal}
        onClose={() => setShowPasswordModal(false)}
        onLogout={onLogout}
        forceSetMode={true}
        onSuccess={() => setShowReminder(false)}
      />
    </div>
  );
}
