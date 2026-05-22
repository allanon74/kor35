import { DEFAULT_STAFF_DASHBOARD_LAYOUT, STAFF_TOOLS_REGISTRY } from './staffToolsRegistry';
import { DEFAULT_GROUP_PALETTE_BY_ID } from './staffGroupPalettes';

export const ALL_STAFF_TOOL_IDS = Object.keys(STAFF_TOOLS_REGISTRY);

export function cloneLayout(layout) {
  return JSON.parse(JSON.stringify(layout || DEFAULT_STAFF_DASHBOARD_LAYOUT));
}

export function createEmptyGroup(order = 0) {
  const id = `gruppo-${Date.now().toString(36)}`;
  return {
    id,
    label: 'Nuovo gruppo',
    icon: 'Layers',
    palette: 'slate',
    order,
    collapsed_default: true,
    tool_ids: [],
  };
}

/** Stato interno editor (draft) da layout API. */
export function layoutToEditorDraft(layout) {
  const base = cloneLayout(layout);
  return {
    version: base.version || 1,
    groups: (base.groups || []).map((g, idx) => ({
      id: g.id,
      label: g.label || 'Gruppo',
      icon: g.icon || 'Layers',
      palette: g.palette || DEFAULT_GROUP_PALETTE_BY_ID[g.id] || 'slate',
      order: typeof g.order === 'number' ? g.order : idx,
      collapsed_default: Boolean(g.collapsed_default),
      tool_ids: [...(g.tool_ids || [])],
    })).sort((a, b) => a.order - b.order),
    pinned_tool_ids: [...(base.pinned_tool_ids || [])],
    tool_labels: { ...(base.tool_labels || {}) },
  };
}

export function editorDraftToLayoutPayload(draft) {
  return {
    version: 1,
    groups: draft.groups.map((g, idx) => ({
      id: g.id,
      label: g.label.trim(),
      icon: g.icon,
      palette: g.palette,
      order: idx,
      collapsed_default: g.collapsed_default,
      tool_ids: g.tool_ids.filter((id) => ALL_STAFF_TOOL_IDS.includes(id)),
    })),
    pinned_tool_ids: draft.pinned_tool_ids.filter((id) => ALL_STAFF_TOOL_IDS.includes(id)),
    tool_labels: Object.fromEntries(
      Object.entries(draft.tool_labels || {})
        .filter(([k, v]) => ALL_STAFF_TOOL_IDS.includes(k) && String(v).trim())
        .map(([k, v]) => [k, String(v).trim()]),
    ),
  };
}

export function getAssignedToolIds(draft) {
  const ids = new Set(draft.pinned_tool_ids);
  for (const g of draft.groups) {
    for (const tid of g.tool_ids) ids.add(tid);
  }
  return ids;
}

export function getUnassignedToolIds(draft) {
  const assigned = getAssignedToolIds(draft);
  return ALL_STAFF_TOOL_IDS.filter((id) => !assigned.has(id));
}

export function getToolDisplayLabel(toolId, draft) {
  const custom = draft.tool_labels?.[toolId];
  if (custom && custom.trim()) return custom.trim();
  return STAFF_TOOLS_REGISTRY[toolId]?.label || toolId;
}

export function removeToolFromDraft(draft, toolId) {
  draft.pinned_tool_ids = draft.pinned_tool_ids.filter((id) => id !== toolId);
  for (const g of draft.groups) {
    g.tool_ids = g.tool_ids.filter((id) => id !== toolId);
  }
}

export function insertToolInGroup(draft, toolId, groupId, index = -1) {
  removeToolFromDraft(draft, toolId);
  if (groupId === '__unassigned__') {
    return;
  }
  if (groupId === '__pinned__') {
    if (!draft.pinned_tool_ids.includes(toolId)) {
      draft.pinned_tool_ids.push(toolId);
    }
    return;
  }
  const group = draft.groups.find((g) => g.id === groupId);
  if (!group) return;
  if (index < 0 || index >= group.tool_ids.length) {
    group.tool_ids.push(toolId);
  } else {
    group.tool_ids.splice(index, 0, toolId);
  }
}

export function reorderInList(list, fromIndex, toIndex) {
  if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) return list;
  const next = [...list];
  const [item] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, item);
  return next;
}
