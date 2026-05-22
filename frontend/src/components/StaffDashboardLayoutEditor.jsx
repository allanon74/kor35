import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  GripVertical,
  Layers,
  Pin,
  PinOff,
  Plus,
  RotateCcw,
  Trash2,
  X,
} from 'lucide-react';
import { updateStaffDashboardLayout } from '../api';
import { DEFAULT_STAFF_DASHBOARD_LAYOUT, STAFF_GROUP_ICON_MAP, STAFF_TOOLS_REGISTRY } from '../staff/staffToolsRegistry';
import { STAFF_PALETTE_OPTIONS, getPaletteColor } from '../staff/staffGroupPalettes';
import {
  createEmptyGroup,
  editorDraftToLayoutPayload,
  getUnassignedToolIds,
  layoutToEditorDraft,
  moveToolInZone,
  PINNED_ZONE_ID,
  removeToolFromDraft,
  reorderInList,
  UNASSIGNED_ZONE_ID,
} from '../staff/staffLayoutEditorState';

function ToolChip({
  toolId,
  draft,
  setDraft,
  paletteId,
  colorIndex,
  draggable = true,
  onDragStart,
  onDragEnd,
}) {
  const meta = STAFF_TOOLS_REGISTRY[toolId];
  const Icon = meta?.icon || Layers;
  const colorClass = getPaletteColor(paletteId, colorIndex);
  const isPinned = draft.pinned_tool_ids.includes(toolId);

  const setLabel = (value) => {
    setDraft((prev) => {
      const next = { ...prev, tool_labels: { ...prev.tool_labels } };
      const trimmed = value.trim();
      if (!trimmed || trimmed === meta?.label) {
        delete next.tool_labels[toolId];
      } else {
        next.tool_labels[toolId] = trimmed;
      }
      return next;
    });
  };

  const togglePin = () => {
    setDraft((prev) => {
      const next = layoutToEditorDraft(editorDraftToLayoutPayload(prev));
      if (isPinned) {
        next.pinned_tool_ids = next.pinned_tool_ids.filter((id) => id !== toolId);
      } else {
        removeToolFromDraft(next, toolId);
        next.pinned_tool_ids = [...next.pinned_tool_ids.filter((id) => id !== toolId), toolId];
      }
      return next;
    });
  };

  return (
    <div
      className={`flex items-center gap-2 p-2 rounded-xl border border-white/10 ${colorClass} shadow-md`}
    >
      <span
        draggable={draggable}
        onDragStart={(e) => {
          e.stopPropagation();
          onDragStart(e, toolId);
        }}
        onDragEnd={onDragEnd}
        className="cursor-grab text-white/60 shrink-0 touch-none p-0.5 -m-0.5 rounded hover:bg-black/20"
        title="Trascina per riordinare o spostare"
      >
        <GripVertical size={16} />
      </span>
      <Icon size={18} className="text-white shrink-0" />
      <input
        type="text"
        value={draft.tool_labels[toolId] ?? meta?.label ?? toolId}
        onChange={(e) => setLabel(e.target.value)}
        className="flex-1 min-w-0 bg-black/25 border border-white/20 rounded-lg px-2 py-1 text-xs text-white placeholder-white/40"
        placeholder={meta?.label}
        onClick={(e) => e.stopPropagation()}
      />
      <button
        type="button"
        onClick={togglePin}
        className={`p-1.5 rounded-lg shrink-0 ${isPinned ? 'bg-white/25 text-amber-200' : 'bg-black/20 text-white/70 hover:text-white'}`}
        title={isPinned ? 'Rimuovi da accesso rapido' : 'Aggiungi ad accesso rapido'}
      >
        {isPinned ? <Pin size={14} /> : <PinOff size={14} />}
      </button>
      <span className="text-[10px] text-white/50 font-mono shrink-0 hidden sm:inline">{toolId}</span>
    </div>
  );
}

function DropSlot({ slotIndex, zoneId, onToolDrop, acceptsToolDrop, isActive }) {
  return (
    <div
      onDragOver={(e) => {
        if (!acceptsToolDrop) return;
        e.preventDefault();
        e.stopPropagation();
      }}
      onDrop={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onToolDrop(e, zoneId, slotIndex);
      }}
      className={`h-2 -my-0.5 rounded transition-all ${
        isActive ? 'bg-violet-400/90 shadow-[0_0_8px_rgba(167,139,250,0.6)]' : 'bg-transparent hover:bg-violet-500/20'
      }`}
      title="Rilascia qui per inserire in questa posizione"
    />
  );
}

function ToolSortableList({
  zoneId,
  toolIds,
  draft,
  setDraft,
  paletteId,
  onDragStart,
  onDragEnd,
  onToolDrop,
  acceptsToolDrop,
  label,
  emptyHint,
}) {
  const [activeSlot, setActiveSlot] = useState(null);

  return (
    <div
      className="rounded-xl border-2 border-dashed p-3 min-h-[3rem] border-gray-600 bg-gray-800/40"
      onDragLeave={() => setActiveSlot(null)}
    >
      {label && (
        <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-2">{label}</p>
      )}
      {toolIds.length === 0 && (
        <p className="text-xs text-gray-500 italic mb-2">{emptyHint}</p>
      )}
      <div className="space-y-0">
        {toolIds.map((toolId, idx) => (
          <React.Fragment key={toolId}>
            <div onDragEnter={() => setActiveSlot(idx)}>
              <DropSlot
                slotIndex={idx}
                zoneId={zoneId}
                onToolDrop={(e, z, i) => {
                  setActiveSlot(null);
                  onToolDrop(e, z, i);
                }}
                acceptsToolDrop={acceptsToolDrop}
                isActive={activeSlot === idx}
              />
            </div>
            <ToolChip
              toolId={toolId}
              draft={draft}
              setDraft={setDraft}
              paletteId={paletteId}
              colorIndex={idx}
              onDragStart={(e, id) => onDragStart(e, id, zoneId)}
              onDragEnd={() => {
                setActiveSlot(null);
                onDragEnd();
              }}
            />
          </React.Fragment>
        ))}
        <div onDragEnter={() => setActiveSlot(toolIds.length)}>
          <DropSlot
            slotIndex={toolIds.length}
            zoneId={zoneId}
            onToolDrop={(e, z, i) => {
              setActiveSlot(null);
              onToolDrop(e, z, i);
            }}
            acceptsToolDrop={acceptsToolDrop}
            isActive={activeSlot === toolIds.length}
          />
        </div>
      </div>
    </div>
  );
}

export default function StaffDashboardLayoutEditor({ initialLayout, onClose, onSaved, onLogout }) {
  const [draft, setDraft] = useState(() => layoutToEditorDraft(initialLayout));
  const [dragPayload, setDragPayload] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setDraft(layoutToEditorDraft(initialLayout));
    setError('');
  }, [initialLayout]);

  const unassignedIds = useMemo(() => getUnassignedToolIds(draft), [draft]);

  const onDragStart = useCallback((e, toolId, fromZone) => {
    const payload = { type: 'tool', toolId, fromZone };
    setDragPayload(payload);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/json', JSON.stringify(payload));
  }, []);

  const onDragEnd = useCallback(() => setDragPayload(null), []);

  const onGroupDragStart = useCallback((e, groupId) => {
    e.stopPropagation();
    const payload = { type: 'group', groupId };
    setDragPayload(payload);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/json', JSON.stringify(payload));
  }, []);

  const readDragPayload = useCallback((e) => {
    let payload = dragPayload;
    try {
      const raw = e.dataTransfer.getData('application/json');
      if (raw) payload = JSON.parse(raw);
    } catch {
      /* ignore */
    }
    return payload;
  }, [dragPayload]);

  const handleToolDrop = useCallback((e, targetZone, targetIndex = 0) => {
    const payload = readDragPayload(e);
    if (!payload || payload.type !== 'tool') return;

    setDraft((prev) => {
      const next = layoutToEditorDraft(editorDraftToLayoutPayload(prev));
      moveToolInZone(
        next,
        payload.toolId,
        targetZone,
        targetIndex,
        payload.fromZone || UNASSIGNED_ZONE_ID,
      );
      return next;
    });
    setDragPayload(null);
  }, [readDragPayload]);

  const handleGroupDrop = useCallback((e, targetIndex) => {
    const payload = readDragPayload(e);
    if (!payload || payload.type !== 'group') return;

    setDraft((prev) => {
      const fromIdx = prev.groups.findIndex((g) => g.id === payload.groupId);
      if (fromIdx < 0) return prev;
      const toIdx = typeof targetIndex === 'number' && targetIndex >= 0 ? targetIndex : prev.groups.length - 1;
      if (fromIdx === toIdx) return prev;
      return { ...prev, groups: reorderInList(prev.groups, fromIdx, toIdx) };
    });
    setDragPayload(null);
  }, [readDragPayload]);

  const updateGroup = (groupId, patch) => {
    setDraft((prev) => ({
      ...prev,
      groups: prev.groups.map((g) => (g.id === groupId ? { ...g, ...patch } : g)),
    }));
  };

  const removeGroup = (groupId) => {
    setDraft((prev) => {
      const next = layoutToEditorDraft(editorDraftToLayoutPayload(prev));
      const group = next.groups.find((g) => g.id === groupId);
      if (group) {
        for (const tid of group.tool_ids) {
          /* restano non assegnati */
        }
      }
      next.groups = next.groups.filter((g) => g.id !== groupId);
      return next;
    });
  };

  const moveGroup = (groupId, direction) => {
    setDraft((prev) => {
      const idx = prev.groups.findIndex((g) => g.id === groupId);
      if (idx < 0) return prev;
      const newIdx = direction < 0 ? idx - 1 : idx + 1;
      if (newIdx < 0 || newIdx >= prev.groups.length) return prev;
      return { ...prev, groups: reorderInList(prev.groups, idx, newIdx) };
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload = editorDraftToLayoutPayload(draft);
      const res = await updateStaffDashboardLayout(payload, onLogout);
      onSaved(res?.staff_dashboard_layout || payload);
    } catch (err) {
      console.error(err);
      setError(err?.message || 'Errore durante il salvataggio del layout.');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (!window.confirm('Ripristinare il layout predefinito? Le modifiche non salvate andranno perse.')) return;
    setDraft(layoutToEditorDraft(DEFAULT_STAFF_DASHBOARD_LAYOUT));
  };

  return (
    <div
      className="fixed inset-0 z-[110] flex flex-col bg-gray-950 text-white"
      role="dialog"
      aria-modal="true"
      aria-labelledby="staff-layout-editor-title"
    >
      <header className="shrink-0 flex items-center justify-between gap-4 px-4 py-3 border-b border-gray-800 bg-gray-900">
        <div>
          <h2 id="staff-layout-editor-title" className="text-lg font-black text-violet-300 uppercase tracking-wide">
            Organizza menu staff
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Trascina le voci dalla maniglia ⋮⋮ (riordina nello stesso gruppo o spostale); i gruppi solo dalla maniglia in intestazione.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-gray-800 text-gray-400"
          aria-label="Chiudi senza salvare"
        >
          <X size={22} />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 custom-scrollbar max-w-4xl mx-auto w-full">
        {error && (
          <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{error}</p>
        )}

        <section>
          <h3 className="text-xs font-black uppercase tracking-widest text-amber-300 mb-2 flex items-center gap-2">
            <Pin size={14} /> Accesso rapido (pin)
          </h3>
          <ToolSortableList
            zoneId={PINNED_ZONE_ID}
            toolIds={draft.pinned_tool_ids}
            draft={draft}
            setDraft={setDraft}
            paletteId="violet"
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            onToolDrop={handleToolDrop}
            acceptsToolDrop={dragPayload?.type !== 'group'}
            label="Accesso rapido — rilascia sulla barra viola tra le voci per riordinare"
            emptyHint="Nessun pin — trascina una voce o usa l&apos;icona pin."
          />
        </section>

        <section className="space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-xs font-black uppercase tracking-widest text-indigo-300">Gruppi del menu</h3>
            <button
              type="button"
              onClick={() => setDraft((prev) => ({
                ...prev,
                groups: [...prev.groups, createEmptyGroup(prev.groups.length)],
              }))}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 text-xs font-bold"
            >
              <Plus size={14} /> Nuovo gruppo
            </button>
          </div>

          {draft.groups.map((group, groupIndex) => {
            const GroupIcon = STAFF_GROUP_ICON_MAP[group.icon] || Layers;
            const paletteId = group.palette || 'slate';
            return (
              <div
                key={group.id}
                className="rounded-2xl border border-gray-700 bg-gray-900/80 overflow-hidden"
              >
                <div
                  className="flex flex-wrap items-center gap-2 p-3 bg-gray-800/80 border-b border-gray-700"
                  onDragOver={(e) => {
                    if (dragPayload?.type === 'group') {
                      e.preventDefault();
                      e.stopPropagation();
                    }
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleGroupDrop(e, groupIndex);
                  }}
                >
                  <span
                    draggable
                    onDragStart={(e) => onGroupDragStart(e, group.id)}
                    onDragEnd={onDragEnd}
                    className="cursor-grab text-gray-500 shrink-0 touch-none"
                    title="Trascina gruppo (solo da qui)"
                  >
                    <GripVertical size={18} />
                  </span>
                  <GroupIcon size={18} className="text-indigo-300 shrink-0" />
                  <input
                    type="text"
                    value={group.label}
                    onChange={(e) => updateGroup(group.id, { label: e.target.value })}
                    className="flex-1 min-w-[8rem] bg-gray-950 border border-gray-600 rounded-lg px-2 py-1 text-sm font-bold"
                  />
                  <select
                    value={group.icon}
                    onChange={(e) => updateGroup(group.id, { icon: e.target.value })}
                    className="bg-gray-950 border border-gray-600 rounded-lg px-2 py-1 text-xs"
                    title="Icona gruppo"
                  >
                    {Object.keys(STAFF_GROUP_ICON_MAP).map((name) => (
                      <option key={name} value={name}>{name}</option>
                    ))}
                  </select>
                  <select
                    value={group.palette}
                    onChange={(e) => updateGroup(group.id, { palette: e.target.value })}
                    className="bg-gray-950 border border-gray-600 rounded-lg px-2 py-1 text-xs"
                    title="Palette colori"
                  >
                    {STAFF_PALETTE_OPTIONS.map((p) => (
                      <option key={p.id} value={p.id}>{p.label}</option>
                    ))}
                  </select>
                  <label className="flex items-center gap-1 text-[10px] text-gray-400 uppercase font-bold">
                    <input
                      type="checkbox"
                      checked={group.collapsed_default}
                      onChange={(e) => updateGroup(group.id, { collapsed_default: e.target.checked })}
                    />
                    Chiuso
                  </label>
                  <div className="flex items-center gap-1 ml-auto">
                    <button type="button" onClick={() => moveGroup(group.id, -1)} className="p-1.5 rounded hover:bg-gray-700 text-gray-400" title="Su">
                      <ChevronUp size={16} />
                    </button>
                    <button type="button" onClick={() => moveGroup(group.id, 1)} className="p-1.5 rounded hover:bg-gray-700 text-gray-400" title="Giù">
                      <ChevronDown size={16} />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (window.confirm(`Eliminare il gruppo "${group.label}"? Le voci resteranno non assegnate.`)) {
                          removeGroup(group.id);
                        }
                      }}
                      className="p-1.5 rounded hover:bg-red-500/20 text-red-400"
                      title="Elimina gruppo"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
                <div className="p-3">
                  <div className="flex gap-1 mb-2">
                    {STAFF_PALETTE_OPTIONS.find((p) => p.id === paletteId)?.sample && (
                      <span className={`w-full h-1.5 rounded-full ${getPaletteColor(paletteId, 0)}`} />
                    )}
                  </div>
                  <ToolSortableList
                    zoneId={group.id}
                    toolIds={group.tool_ids}
                    draft={draft}
                    setDraft={setDraft}
                    paletteId={paletteId}
                    onDragStart={onDragStart}
                    onDragEnd={onDragEnd}
                    onToolDrop={handleToolDrop}
                    acceptsToolDrop={dragPayload?.type !== 'group'}
                    label={`Voci in "${group.label}"`}
                    emptyHint="Trascina qui le voci del gruppo."
                  />
                </div>
              </div>
            );
          })}
        </section>

        {unassignedIds.length > 0 && (
          <section>
            <h3 className="text-xs font-black uppercase tracking-widest text-gray-500 mb-2">Non assegnati</h3>
            <div
              className="rounded-xl border-2 border-dashed p-3 border-gray-600 bg-gray-800/40"
              onDragOver={(e) => {
                if (dragPayload?.type === 'group') return;
                e.preventDefault();
                e.stopPropagation();
              }}
              onDrop={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleToolDrop(e, UNASSIGNED_ZONE_ID, 0);
              }}
            >
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-2">Non assegnati</p>
              <div className="space-y-2">
                {unassignedIds.map((toolId, idx) => (
                  <ToolChip
                    key={toolId}
                    toolId={toolId}
                    draft={draft}
                    setDraft={setDraft}
                    paletteId="stone"
                    colorIndex={idx}
                    onDragStart={(e, id) => onDragStart(e, id, UNASSIGNED_ZONE_ID)}
                    onDragEnd={onDragEnd}
                  />
                ))}
              </div>
            </div>
          </section>
        )}
      </div>

      <footer className="shrink-0 flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-gray-800 bg-gray-900">
        <button
          type="button"
          onClick={handleReset}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white"
        >
          <RotateCcw size={16} /> Ripristina predefinito
        </button>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm font-bold"
          >
            Annulla
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-sm font-black uppercase tracking-wide disabled:opacity-50"
          >
            {saving ? 'Salvataggio...' : 'Salva layout'}
          </button>
        </div>
      </footer>
    </div>
  );
}
