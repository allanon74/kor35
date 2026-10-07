import React from 'react';

/** Interpreta il campo usi massimi staff: stringa vuota → null (illimitato). */
export function parseStaffQrUsiMax(raw) {
  const s = (raw ?? '').toString().trim();
  if (s === '') return null;
  const n = Number(s);
  if (!Number.isFinite(n) || n < 1) return null;
  return Math.floor(n);
}

/**
 * Campo usi massimi nell'overlay di associazione QR.
 * Vuoto = scansioni/prelievi illimitati.
 */
export default function StaffQrUsiMaxField({ value, onChange, className = '' }) {
  return (
    <div className={`px-4 py-2 bg-gray-900 border-b border-gray-800 ${className}`}>
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">
        Usi massimi (vuoto = illimitato)
      </label>
      <input
        type="number"
        min={1}
        inputMode="numeric"
        className="w-full max-w-xs bg-gray-950 border border-gray-600 rounded px-3 py-2 text-sm text-white min-h-11"
        placeholder="Vuoto = illimitato"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
