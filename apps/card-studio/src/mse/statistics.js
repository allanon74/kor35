import {
  cardFieldValue,
  formatFieldValueForDisplay,
  lookupChoiceColor,
  normFieldKey,
} from "./fieldUtils";

export function statisticsDimensions(cardFields) {
  if (!Array.isArray(cardFields) || cardFields.length === 0) {
    return [
      { key: "tipo", label: "Type", field: { name: "type", type: "choice" } },
      { key: "energia", label: "Energy", field: { name: "energy", type: "choice" } },
      { key: "rarita", label: "Rarity", field: { name: "rarity", type: "choice" } },
    ];
  }
  return cardFields
    .filter((f) => f.show_statistics !== false)
    .map((f) => ({
      key: normFieldKey(f.name),
      label: f.card_list_name || f.name,
      field: f,
    }));
}

export function buildSetStatistics({ cards, cardFields }) {
  const dimensions = statisticsDimensions(cardFields);
  const total = cards.length;
  const breakdown = dimensions.map((dim) => {
    const counts = new Map();
    cards.forEach((card) => {
      const raw = cardFieldValue(card, dim.field);
      const label = formatFieldValueForDisplay(raw, dim.field);
      counts.set(label, (counts.get(label) || 0) + 1);
    });
    const rows = Array.from(counts.entries())
      .map(([label, count]) => ({
        label,
        count,
        pct: total ? Math.round((count / total) * 1000) / 10 : 0,
        color:
          lookupChoiceColor(dim.field.choice_colors, label) ||
          lookupChoiceColor(dim.field.choice_colors_cardlist, label) ||
          "",
      }))
      .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
    return { ...dim, total, rows };
  });
  return { total, dimensions: breakdown };
}
