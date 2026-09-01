import React, { useEffect, useId, useRef, useState } from 'react';
import { RotateCcw, RotateCw, Trash2 } from 'lucide-react';
import InstafameAuthorSignature from './InstafameAuthorSignature';
import { normalizeRotationDegrees } from '../utils/profileImage';

/**
 * Editor firma social con anteprima live (banner + testo).
 */
export default function InstafameFirmaEditor({
  firmaTesto = '',
  firmaBannerFile = null,
  firmaBannerRemoteUrl = null,
  firmaBannerRotation = 0,
  onTestoChange,
  onBannerFileChange,
  onBannerRotationChange,
  onClearBanner,
  accentClass = 'file:bg-amber-700',
  rotateButtonClass = 'bg-amber-900/50 hover:bg-amber-800/70 border-amber-700/50 text-amber-100',
  previewLight = false,
}) {
  const inputRef = useRef(null);
  const inputId = useId();
  const [localPreview, setLocalPreview] = useState(null);

  useEffect(() => {
    if (!firmaBannerFile) {
      setLocalPreview(null);
      return undefined;
    }
    const url = URL.createObjectURL(firmaBannerFile);
    setLocalPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [firmaBannerFile]);

  const previewBannerUrl = localPreview || firmaBannerRemoteUrl || null;
  const normalizedRotation = normalizeRotationDegrees(firmaBannerRotation);
  const hasBanner = Boolean(previewBannerUrl);

  const rotate = (delta) => {
    if (!onBannerRotationChange) return;
    onBannerRotationChange(normalizeRotationDegrees(normalizedRotation + delta));
  };

  const handleFileChange = (event) => {
    const nextFile = event.target.files?.[0] || null;
    onBannerFileChange?.(nextFile);
    onBannerRotationChange?.(0);
    if (inputRef.current) inputRef.current.value = '';
  };

  const previewTesto = String(firmaTesto || '').trim();
  const showPreview = Boolean(previewTesto || previewBannerUrl);

  return (
    <div className="space-y-3 rounded-xl border border-gray-700 bg-gray-900/40 p-3">
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wide">Firma social</p>
        <p className="text-[11px] text-gray-500 mt-0.5">
          Appare in automatico sotto i tuoi post InstaFame e gli articoli di rubrica firmati con questo personaggio.
        </p>
      </div>

      <div>
        <label className="text-xs text-gray-400">Testo firma</label>
        <textarea
          className="mt-1 w-full bg-gray-800 rounded p-2 border border-gray-700 min-h-20 text-sm"
          placeholder="Citazione, motto, contatti in-character…"
          value={firmaTesto}
          onChange={(event) => onTestoChange?.(event.target.value)}
        />
      </div>

      <div>
        <label htmlFor={inputId} className="text-xs text-gray-400">
          Banner firma (opzionale)
        </label>
        <div className="mt-2 space-y-2">
          {hasBanner ? (
            <div className="w-full max-w-lg overflow-hidden rounded-lg border border-gray-600 bg-gray-950">
              <img
                src={previewBannerUrl}
                alt=""
                className="w-full h-auto max-h-40 object-contain transition-transform duration-200"
                style={{ transform: `rotate(${normalizedRotation}deg)` }}
              />
            </div>
          ) : (
            <div className="w-full max-w-lg h-16 rounded-lg border border-dashed border-gray-600 bg-gray-950/60 flex items-center justify-center text-[11px] text-gray-500">
              Nessun banner
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={inputRef}
              id={inputId}
              type="file"
              accept="image/*"
              className={`text-sm text-gray-300 file:mr-2 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-white ${accentClass}`}
              onChange={handleFileChange}
            />
            {hasBanner && onBannerRotationChange ? (
              <>
                <button
                  type="button"
                  onClick={() => rotate(-90)}
                  className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold border ${rotateButtonClass}`}
                >
                  <RotateCcw size={14} />
                  Sinistra
                </button>
                <button
                  type="button"
                  onClick={() => rotate(90)}
                  className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold border ${rotateButtonClass}`}
                >
                  <RotateCw size={14} />
                  Destra
                </button>
              </>
            ) : null}
            {hasBanner && onClearBanner ? (
              <button
                type="button"
                onClick={() => {
                  onClearBanner();
                  onBannerRotationChange?.(0);
                }}
                className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold border border-red-700/50 bg-red-950/40 text-red-200 hover:bg-red-900/50"
              >
                <Trash2 size={14} />
                Rimuovi banner
              </button>
            ) : null}
          </div>
          <p className="text-[11px] text-gray-500">
            Consigliato 1200×400 (3:1). L&apos;immagine viene mostrata intera, senza ritaglio.
          </p>
        </div>
      </div>

      <div className="pt-2 border-t border-gray-700/80">
        <p className="text-[11px] uppercase tracking-wide text-gray-500 mb-2">Anteprima</p>
        {showPreview ? (
          <InstafameAuthorSignature
            testo={firmaTesto}
            bannerUrl={previewBannerUrl}
            compact
            light={previewLight}
          />
        ) : (
          <p className="text-xs text-gray-500 italic">Compila testo o banner per vedere l&apos;anteprima.</p>
        )}
      </div>
    </div>
  );
}
