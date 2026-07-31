/**
 * Risolve lo stylesheet MSE effettivo per una carta.
 *
 * Cascata:
 * 1. override sulla carta (`studio_template`)
 * 2. default del set (`espansione.default_studio_template`)
 * 3. default del gioco (`is_default_for_new_cards`)
 * 4. primo template del gioco selezionato
 */
export function resolveStudioTemplateId({
  cardStudioTemplate = null,
  espansione = null,
  defaultTemplateByGame = {},
  templatesForSelectedGame = [],
  templatesById = {},
  selectedGameId = "",
} = {}) {
  const cardId = cardStudioTemplate || null;
  if (cardId && (!templatesById || templatesById[cardId])) {
    return cardId;
  }

  const fromSet = espansione?.default_studio_template || null;
  if (fromSet && (!templatesById || templatesById[fromSet])) {
    return fromSet;
  }

  const gameId = espansione?.gioco_definizione || selectedGameId || "";
  if (gameId && defaultTemplateByGame?.[gameId]) {
    return defaultTemplateByGame[gameId];
  }

  return templatesForSelectedGame?.[0]?.id || null;
}

export function describeStudioTemplateSource({
  cardStudioTemplate = null,
  resolvedId = null,
  espansione = null,
  templatesById = {},
} = {}) {
  if (!resolvedId) return "Nessuno stylesheet";
  const nome = templatesById[resolvedId]?.nome || resolvedId;
  if (cardStudioTemplate && cardStudioTemplate === resolvedId) {
    return `${nome} (override carta)`;
  }
  if (espansione?.default_studio_template === resolvedId) {
    return `${nome} (default del set)`;
  }
  return `${nome} (default gioco)`;
}
