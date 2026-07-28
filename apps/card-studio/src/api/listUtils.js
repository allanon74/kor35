/** Inserisce o aggiorna un record nella lista per id (UUID). */
export function mergeRecordById(list, record) {
  if (!record?.id) return list;
  const idx = list.findIndex((row) => row.id === record.id);
  if (idx < 0) return [...list, record];
  const next = list.slice();
  next[idx] = { ...list[idx], ...record };
  return next;
}
