import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ImagePlus, Loader2, Trash2, X, ZoomIn } from 'lucide-react';
import { resolveMediaUrl, staffPatchPersonaggio } from '../api';
import { compressCostumeImageFile } from '../utils/costumeImage';

function ImageLightbox({ src, alt, onClose }) {
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [onClose]);

  if (!src) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center bg-black/95 p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={alt || 'Anteprima foto'}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute top-3 right-3 z-10 rounded-full bg-black/60 p-2 text-white hover:bg-black/80"
        aria-label="Chiudi anteprima"
      >
        <X className="h-6 w-6" />
      </button>
      <button
        type="button"
        onClick={onClose}
        className="flex h-full w-full max-h-[92vh] max-w-[96vw] items-center justify-center focus:outline-none"
        aria-label="Chiudi anteprima"
      >
        <img
          src={src}
          alt={alt || ''}
          className="max-h-[92vh] max-w-[96vw] object-contain select-none"
          draggable={false}
        />
      </button>
    </div>,
    document.body,
  );
}

function CostumePhotoSlot({
  label,
  fieldName,
  clearFlagName,
  remoteUrl,
  personaggioId,
  onLogout,
  onUpdated,
  disabled,
}) {
  const inputId = useId();
  const inputRef = useRef(null);
  const [localPreview, setLocalPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [lightboxOpen, setLightboxOpen] = useState(false);

  const previewSrc = localPreview || (remoteUrl ? resolveMediaUrl(remoteUrl) : null);

  useEffect(() => {
    setLocalPreview(null);
  }, [remoteUrl, personaggioId]);

  const uploadFile = async (file) => {
    if (!personaggioId || !file) return;
    setUploading(true);
    setError('');
    try {
      const prepared = await compressCostumeImageFile(file);
      const preview = URL.createObjectURL(prepared);
      setLocalPreview(preview);
      const fd = new FormData();
      fd.append(fieldName, prepared);
      const updated = await staffPatchPersonaggio(personaggioId, fd, onLogout);
      onUpdated?.({
        foto_trucco_url: updated.foto_trucco_url,
        foto_outfit_url: updated.foto_outfit_url,
      });
    } catch (e) {
      setLocalPreview(null);
      setError(e.message || 'Errore caricamento foto');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const handleRemove = async () => {
    if (!personaggioId || disabled || uploading) return;
    if (!previewSrc && !remoteUrl) return;
    setUploading(true);
    setError('');
    try {
      const fd = new FormData();
      fd.append(clearFlagName, '1');
      const updated = await staffPatchPersonaggio(personaggioId, fd, onLogout);
      setLocalPreview(null);
      onUpdated?.({
        foto_trucco_url: updated.foto_trucco_url,
        foto_outfit_url: updated.foto_outfit_url,
      });
    } catch (e) {
      setError(e.message || 'Errore rimozione foto');
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) void uploadFile(file);
  };

  return (
    <div className="space-y-2">
      <label htmlFor={inputId} className="text-xs text-gray-400 block">
        {label}
      </label>
      <div className="relative rounded-lg border border-gray-700 bg-gray-900/60 overflow-hidden">
        {previewSrc ? (
          <button
            type="button"
            onClick={() => setLightboxOpen(true)}
            className="group relative block w-full aspect-[3/4] focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500/60"
            title="Clicca per ingrandire"
          >
            <img src={previewSrc} alt={label} className="h-full w-full object-cover" />
            <span className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/35 transition-colors">
              <ZoomIn className="text-white opacity-0 group-hover:opacity-100 drop-shadow" size={28} />
            </span>
          </button>
        ) : (
          <label
            htmlFor={inputId}
            className={`flex aspect-[3/4] cursor-pointer flex-col items-center justify-center gap-2 text-gray-500 hover:text-gray-300 hover:bg-gray-800/50 transition-colors ${disabled || uploading ? 'opacity-50 pointer-events-none' : ''}`}
          >
            <ImagePlus size={28} />
            <span className="text-xs">Carica foto</span>
          </label>
        )}
        {uploading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <Loader2 className="animate-spin text-teal-300" size={28} />
          </div>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept="image/*"
          className="hidden"
          disabled={disabled || uploading || !personaggioId}
          onChange={handleFileChange}
        />
        {previewSrc && (
          <button
            type="button"
            disabled={disabled || uploading}
            onClick={() => inputRef.current?.click()}
            className="text-xs px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-50"
          >
            Sostituisci
          </button>
        )}
        {(previewSrc || remoteUrl) && (
          <button
            type="button"
            disabled={disabled || uploading}
            onClick={() => void handleRemove()}
            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-900/40 text-red-200 hover:bg-red-900/60 disabled:opacity-50"
          >
            <Trash2 size={12} />
            Rimuovi
          </button>
        )}
      </div>
      {error && <p className="text-xs text-red-300">{error}</p>}
      {lightboxOpen && previewSrc && (
        <ImageLightbox src={previewSrc} alt={label} onClose={() => setLightboxOpen(false)} />
      )}
    </div>
  );
}

/**
 * Foto trucco e outfit — visibili/modificabili solo dallo staff, sotto gli appunti costume.
 */
export default function StaffCostumePhotosSection({
  personaggioId,
  fotoTruccoUrl = null,
  fotoOutfitUrl = null,
  onLogout,
  onUpdated,
  disabled = false,
  className = '',
}) {
  const handleUpdated = useCallback(
    (urls) => {
      onUpdated?.(urls);
    },
    [onUpdated],
  );

  if (!personaggioId) {
    return (
      <p className={`text-xs text-gray-500 ${className}`}>
        Salva il personaggio per poter caricare le foto costume.
      </p>
    );
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <p className="text-[11px] text-gray-500">
        Reference visibili solo allo staff. Clic sulla miniatura per ingrandire a tutto schermo.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <CostumePhotoSlot
          label="Foto trucco"
          fieldName="foto_trucco"
          clearFlagName="clear_foto_trucco"
          remoteUrl={fotoTruccoUrl}
          personaggioId={personaggioId}
          onLogout={onLogout}
          onUpdated={handleUpdated}
          disabled={disabled}
        />
        <CostumePhotoSlot
          label="Foto outfit"
          fieldName="foto_outfit"
          clearFlagName="clear_foto_outfit"
          remoteUrl={fotoOutfitUrl}
          personaggioId={personaggioId}
          onLogout={onLogout}
          onUpdated={handleUpdated}
          disabled={disabled}
        />
      </div>
    </div>
  );
}
