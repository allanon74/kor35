import React from 'react';
import { CheckCircle2, AlertTriangle } from 'lucide-react';

/**
 * Badge compatto prontezza negozio (plot quest / staff).
 * readiness: { pronto, checks: [{ ok, label, detail }] }
 */
const NegozioReadinessBadge = ({ readiness, compact = false }) => {
  if (!readiness) return null;
  const { pronto, checks = [] } = readiness;

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 text-[9px] font-black uppercase px-1.5 py-0.5 rounded ${
          pronto ? 'bg-emerald-900/50 text-emerald-400' : 'bg-amber-900/50 text-amber-300'
        }`}
        title={checks.filter((c) => !c.ok).map((c) => c.detail || c.label).join(' · ')}
      >
        {pronto ? <CheckCircle2 size={10} /> : <AlertTriangle size={10} />}
        {pronto ? 'Pronto' : 'Da completare'}
      </span>
    );
  }

  return (
    <div className="text-[10px] space-y-1 mt-1">
      {checks.map((c) => (
        <div
          key={c.code}
          className={`flex items-start gap-1 ${c.ok ? 'text-emerald-500/90' : 'text-amber-400'}`}
        >
          {c.ok ? <CheckCircle2 size={12} className="shrink-0 mt-0.5" /> : (
            <AlertTriangle size={12} className="shrink-0 mt-0.5" />
          )}
          <span>
            {c.label}
            {c.detail ? <span className="text-gray-500"> — {c.detail}</span> : null}
          </span>
        </div>
      ))}
    </div>
  );
};

export default NegozioReadinessBadge;
