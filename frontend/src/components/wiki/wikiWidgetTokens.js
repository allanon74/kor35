export const getWidgetToken = (item) => String(item?.sync_id || item?.id || '').trim();

export const getUsedWidgetIds = (content) => {
  const safeContent = String(content || '');
  const usedIds = {
    tiers: [],
    ere: [],
    tierCollections: [],
    images: [],
    buttons: [],
    mattoni: [],
  };

  const tierMatches = safeContent.matchAll(/\{\{WIDGET_TIER:([A-Za-z0-9-]+)\}\}/g);
  for (const match of tierMatches) {
    usedIds.tiers.push(String(match[1]));
  }

  const tierCollectionMatches = safeContent.matchAll(/\{\{WIDGET_TIER_COLLECTION:([A-Za-z0-9-]+)\}\}/g);
  for (const match of tierCollectionMatches) {
    usedIds.tierCollections.push(String(match[1]));
  }

  const ereMatches = safeContent.matchAll(/\{\{WIDGET_(?:ERA|ERE):([A-Za-z0-9-]+)\}\}/g);
  for (const match of ereMatches) {
    usedIds.ere.push(String(match[1]));
  }

  const imageMatches = safeContent.matchAll(/\{\{WIDGET_(?:IMAGE|IMMAGINE):([A-Za-z0-9-]+)\}\}/g);
  for (const match of imageMatches) {
    usedIds.images.push(String(match[1]));
  }

  const buttonMatches = safeContent.matchAll(/\{\{WIDGET_(?:BUTTONS|PULSANTI):([A-Za-z0-9-]+)\}\}/g);
  for (const match of buttonMatches) {
    usedIds.buttons.push(String(match[1]));
  }

  const mattoniMatches = safeContent.matchAll(/\{\{WIDGET_MATTONI:([A-Za-z0-9-]+)\}\}/g);
  for (const match of mattoniMatches) {
    usedIds.mattoni.push(String(match[1]));
  }

  return usedIds;
};

export const sortByUsage = (items, usedIds) => {
  return [...items].sort((a, b) => {
    const aUsed = usedIds.includes(getWidgetToken(a));
    const bUsed = usedIds.includes(getWidgetToken(b));

    if (aUsed && !bUsed) return -1;
    if (!aUsed && bUsed) return 1;
    return 0;
  });
};
