import React, { useEffect, useMemo, useState } from 'react';
import packageInfo from '../../package.json';

function shortSha(sha) {
  const s = (sha || '').trim();
  if (!s) return '';
  return s.slice(0, 12);
}

export default function BuildVersions({ className = '' }) {
  const frontend = useMemo(() => {
    const pkg = packageInfo?.version || '';
    const buildVersion = (import.meta.env.VITE_BUILD_VERSION || '').trim();
    const buildSha = (import.meta.env.VITE_BUILD_SHA || '').trim();
    const buildTime = (import.meta.env.VITE_BUILD_TIME || '').trim();
    return {
      pkg,
      buildVersion,
      buildSha,
      buildTime,
    };
  }, []);

  const [backend, setBackend] = useState(null);
  const [backendError, setBackendError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch('/api/version/', { method: 'GET' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setBackend(data?.backend || null);
      } catch (e) {
        if (cancelled) return;
        setBackendError(true);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const frontendLabel = (() => {
    const bits = [];
    if (frontend.pkg) bits.push(`v${frontend.pkg}`);
    if (frontend.buildVersion) bits.push(frontend.buildVersion);
    else if (frontend.buildSha) bits.push(`g${frontend.buildSha.slice(0, 7)}`);
    return bits.join(' ');
  })();

  const backendLabel = (() => {
    if (!backend) return backendError ? 'backend: non disponibile' : 'backend: ...';
    const bits = [];
    if (backend.version) bits.push(backend.version);
    if (backend.sha && backend.sha !== 'unknown') bits.push(shortSha(backend.sha));
    return `backend: ${bits.join(' ')}`.trim();
  })();

  return (
    <div className={`text-[10px] text-gray-500 font-mono ${className}`}>
      <div className="truncate" title={frontendLabel}>
        front: {frontendLabel || 'n/d'}
      </div>
      <div className="truncate" title={typeof backendLabel === 'string' ? backendLabel : ''}>
        {backendLabel}
      </div>
    </div>
  );
}

