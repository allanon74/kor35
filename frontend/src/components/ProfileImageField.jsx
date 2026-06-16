import React, { useEffect, useId, useRef, useState } from 'react';
import { RotateCcw, RotateCw } from 'lucide-react';
import { normalizeRotationDegrees } from '../utils/profileImage';

export default function ProfileImageField({
  file = null,
  remoteUrl = null,
  rotation = 0,
  onFileChange,
  onRotationChange,
  label = 'Foto profilo',
  hint = '',
  fallbackLetter = '?',
  previewClassName = 'h-20 w-20',
  accentClass = 'file:bg-indigo-700',
  rotateButtonClass = 'bg-gray-800 hover:bg-gray-700 border-gray-600 text-gray-200',
}) {
  const inputRef = useRef(null);
  const inputId = useId();
  const [localPreview, setLocalPreview] = useState(null);

  useEffect(() => {
    if (!file) {
      setLocalPreview(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setLocalPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const previewSrc = localPreview || remoteUrl || null;
  const hasImage = Boolean(previewSrc);
  const normalizedRotation = normalizeRotationDegrees(rotation);

  const rotate = (delta) => {
    if (!onRotationChange) return;
    onRotationChange(normalizeRotationDegrees(normalizedRotation + delta));
  };

  const handleFileChange = (e) => {
    const nextFile = e.target.files?.[0] || null;
    onFileChange?.(nextFile);
    onRotationChange?.(0);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div>
      {label ? <label className="text-xs text-gray-400 uppercase">{label}</label> : null}
      <div className="mt-2 flex flex-wrap items-center gap-4">
        <div
          className={`${previewClassName} rounded-full border border-gray-600 bg-gray-900 overflow-hidden flex items-center justify-center shrink-0`}
        >
          {previewSrc ? (
            <img
              src={previewSrc}
              alt=""
              className="h-full w-full object-cover transition-transform duration-200"
              style={{ transform: `rotate(${normalizedRotation}deg)` }}
            />
          ) : (
            <span className="text-2xl font-black text-indigo-300">
              {String(fallbackLetter || '?').charAt(0).toUpperCase()}
            </span>
          )}
        </div>
        <div className="space-y-2 min-w-0">
          <input
            ref={inputRef}
            id={inputId}
            type="file"
            accept="image/*"
            className={`text-sm text-gray-300 file:mr-2 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-white ${accentClass}`}
            onChange={handleFileChange}
          />
          {hasImage && onRotationChange ? (
            <div className="flex items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => rotate(-90)}
                className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold border ${rotateButtonClass}`}
                title="Ruota a sinistra"
              >
                <RotateCcw size={14} />
                Sinistra
              </button>
              <button
                type="button"
                onClick={() => rotate(90)}
                className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold border ${rotateButtonClass}`}
                title="Ruota a destra"
              >
                <RotateCw size={14} />
                Destra
              </button>
              {normalizedRotation !== 0 ? (
                <span className="text-[11px] text-gray-500">{normalizedRotation}°</span>
              ) : null}
            </div>
          ) : null}
          {hint ? <p className="text-[11px] text-gray-500">{hint}</p> : null}
        </div>
      </div>
    </div>
  );
}
