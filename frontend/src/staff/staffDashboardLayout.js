import React from 'react';
import { Layers } from 'lucide-react';
import {
  DEFAULT_STAFF_DASHBOARD_LAYOUT,
  STAFF_GROUP_ICON_MAP,
  STAFF_TOOLS_REGISTRY,
} from './staffToolsRegistry';
import {
  getPaletteColor,
  PINNED_PALETTE_ID,
  resolveGroupPalette,
} from './staffGroupPalettes';

const ALTRO_GROUP_ID = 'altro';

function resolveGroupIcon(iconName) {
  return STAFF_GROUP_ICON_MAP[iconName] || Layers;
}

function normalizeLayoutInput(layout) {
  if (!layout || typeof layout !== 'object') {
    return DEFAULT_STAFF_DASHBOARD_LAYOUT;
  }
  const groups = Array.isArray(layout.groups) ? layout.groups : DEFAULT_STAFF_DASHBOARD_LAYOUT.groups;
  const pinned = Array.isArray(layout.pinned_tool_ids)
    ? layout.pinned_tool_ids
    : DEFAULT_STAFF_DASHBOARD_LAYOUT.pinned_tool_ids;
  const tool_labels = layout.tool_labels && typeof layout.tool_labels === 'object'
    ? layout.tool_labels
    : {};
  return {
    version: layout.version || 1,
    tool_labels,
    groups: groups.map((g, idx) => ({
      id: g.id || `group-${idx}`,
      label: g.label || 'Gruppo',
      icon: g.icon || 'Layers',
      palette: g.palette || 'slate',
      order: typeof g.order === 'number' ? g.order : idx,
      collapsed_default: Boolean(g.collapsed_default),
      tool_ids: Array.isArray(g.tool_ids) ? g.tool_ids : [],
    })).sort((a, b) => a.order - b.order),
    pinned_tool_ids: pinned,
  };
}

function enrichTool(tool, layout, paletteId, colorIndex) {
  const customLabel = layout.tool_labels?.[tool.id];
  const label = (customLabel && String(customLabel).trim())
    ? String(customLabel).trim()
    : tool.label;
  return {
    ...tool,
    label,
    color: getPaletteColor(paletteId, colorIndex),
  };
}

function enrichToolList(tools, layout, paletteId) {
  return tools.map((tool, idx) => enrichTool(tool, layout, paletteId, idx));
}

/**
 * Applica layout globale ai tool visibili per ruolo.
 */
export function applyStaffDashboardLayout(visibleTools, layoutRaw) {
  const layout = normalizeLayoutInput(layoutRaw);
  const toolById = new Map(visibleTools.map((t) => [t.id, t]));
  const assigned = new Set();

  const takeTools = (ids, paletteId) => {
    const out = [];
    let idx = 0;
    for (const id of ids || []) {
      if (assigned.has(id)) continue;
      const tool = toolById.get(id);
      if (!tool) continue;
      assigned.add(id);
      out.push(enrichTool(tool, layout, paletteId, idx));
      idx += 1;
    }
    return out;
  };

  const pinned = takeTools(layout.pinned_tool_ids, PINNED_PALETTE_ID);
  const sections = [];

  for (const group of layout.groups) {
    const paletteId = resolveGroupPalette(group);
    const tools = takeTools(group.tool_ids, paletteId);
    if (tools.length === 0) continue;
    sections.push({
      id: group.id,
      label: group.label,
      icon: resolveGroupIcon(group.icon),
      palette: paletteId,
      collapsed_default: group.collapsed_default,
      tools,
    });
  }

  const orphanTools = visibleTools.filter((t) => !assigned.has(t.id));
  if (orphanTools.length > 0) {
    const paletteId = 'stone';
    sections.push({
      id: ALTRO_GROUP_ID,
      label: 'Altro',
      icon: Layers,
      palette: paletteId,
      collapsed_default: false,
      tools: enrichToolList(orphanTools, layout, paletteId),
    });
  }

  const flatOrder = [...pinned, ...sections.flatMap((s) => s.tools)];

  return { pinned, sections, flatOrder, layout };
}

/**
 * Costruisce voci sidebar con gruppi espandibili (subItems).
 */
export function buildStaffSidebarItems({
  activeTool,
  menuStructure,
  handleToolSelect,
  onSwitchToPlayer,
  socialUnreadCount,
  hubIcon,
  shortcutIcons,
}) {
  const { pinned, sections } = menuStructure;
  const items = [
    {
      label: 'Master Hub',
      icon: hubIcon,
      active: activeTool === 'home',
      action: () => handleToolSelect('home'),
    },
  ];

  const toolToSidebarItem = (tool) => ({
    label: tool.label,
    icon: React.createElement(tool.icon, { size: 18 }),
    active: activeTool === tool.id,
    action: () => handleToolSelect(tool.id),
  });

  for (const tool of pinned) {
    items.push(toolToSidebarItem(tool));
  }

  for (const section of sections) {
    if (section.tools.length === 1) {
      items.push(toolToSidebarItem(section.tools[0]));
      continue;
    }
    const GroupIcon = section.icon;
    items.push({
      label: section.label,
      groupId: section.id,
      icon: React.createElement(GroupIcon, { size: 18 }),
      active: section.tools.some((t) => t.id === activeTool),
      collapsed_default: section.collapsed_default,
      subItems: section.tools.map((t) => ({
        label: t.label,
        active: activeTool === t.id,
        action: () => handleToolSelect(t.id),
      })),
    });
  }

  items.push({ label: '----------------', icon: null, action: () => {} });
  items.push({
    label: 'Wiki Pubblica',
    icon: shortcutIcons.globe,
    link: '/',
    active: false,
  });
  items.push({
    label: 'Vai al Social',
    icon: shortcutIcons.sparkles,
    link: '/app/social',
    active: false,
    badgeCount: socialUnreadCount,
  });
  items.push({
    label: 'Vai a Personaggi',
    icon: shortcutIcons.users,
    action: onSwitchToPlayer,
    active: false,
  });

  return items;
}

/** Etichetta di default da registry (per editor). */
export function getDefaultToolLabel(toolId) {
  return STAFF_TOOLS_REGISTRY[toolId]?.label || toolId;
}
