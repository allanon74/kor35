/** Allineamento MSE → flexbox (orizzontale + verticale separati). */
export function parseFlexAlignment(alignment) {
  const parts = String(alignment || "left top")
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);

  let justifyContent = "flex-start";
  let alignItems = "flex-start";

  if (parts.includes("right")) justifyContent = "flex-end";
  else if (parts.includes("center")) justifyContent = "center";

  if (parts.includes("bottom")) alignItems = "flex-end";
  else if (parts.includes("middle") || (parts.includes("center") && !parts.includes("left") && !parts.includes("right"))) {
    alignItems = "center";
  }

  return { justifyContent, alignItems };
}
