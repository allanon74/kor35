import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { normalizeScannedQrId } from '../utils/qrScan.js';

const READER_ID = 'compattatore-qr-reader';

export default function CompattatoreQrInput({
  qrId,
  personaggioId,
  onQrIdChange,
  onPersonaggioIdChange,
  disabled,
}) {
  const [cameraOn, setCameraOn] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const wedgeRef = useRef(null);
  const scannerRef = useRef(null);
  const processingRef = useRef(false);

  const applyScan = useCallback((raw) => {
    const id = normalizeScannedQrId(raw);
    if (id) onQrIdChange(id);
  }, [onQrIdChange]);

  const stopCamera = useCallback(async () => {
    const scanner = scannerRef.current;
    scannerRef.current = null;
    if (!scanner) {
      setCameraOn(false);
      return;
    }
    try {
      await scanner.stop();
    } catch (_) {
      /* già fermato */
    }
    try {
      scanner.clear();
    } catch (_) {
      /* ignore */
    }
    setCameraOn(false);
  }, []);

  const startCamera = useCallback(async () => {
    setCameraError('');
    if (scannerRef.current) return;
    try {
      const scanner = new Html5Qrcode(READER_ID);
      scannerRef.current = scanner;
      await scanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 220, height: 220 } },
        (decoded) => {
          if (processingRef.current) return;
          processingRef.current = true;
          applyScan(decoded);
          stopCamera().finally(() => {
            processingRef.current = false;
          });
        },
        () => {},
      );
      setCameraOn(true);
    } catch (e) {
      scannerRef.current = null;
      setCameraError(e?.message || 'Camera non disponibile.');
      setCameraOn(false);
    }
  }, [applyScan, stopCamera]);

  useEffect(() => () => {
    stopCamera();
  }, [stopCamera]);

  const onWedgeKeyDown = (e) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    applyScan(e.target.value);
    e.target.value = '';
  };

  return (
    <div className="comp-qr-block">
      <span className="comp-field-label">Sacrificio via QR</span>
      <p className="comp-field-hint">
        Pistola barcode / incolla URL — con ID personaggio l&apos;oggetto viene eliminato dall&apos;inventario.
      </p>

      <div className="comp-qr-wedge-row">
        <input
          ref={wedgeRef}
          type="text"
          className="comp-sci-input comp-qr-wedge"
          placeholder="Scan QR o incolla codice…"
          disabled={disabled}
          onKeyDown={onWedgeKeyDown}
          onBlur={(e) => {
            if (e.target.value.trim()) applyScan(e.target.value);
          }}
        />
        <button
          type="button"
          className="comp-btn comp-btn--scan"
          disabled={disabled}
          onClick={() => (cameraOn ? stopCamera() : startCamera())}
        >
          {cameraOn ? 'Chiudi cam' : 'Camera'}
        </button>
      </div>

      {qrId ? (
        <div className="comp-qr-captured">
          <span className="comp-qr-captured-label">QR acquisito</span>
          <code className="comp-qr-captured-id">{qrId}</code>
          <button
            type="button"
            className="comp-qr-clear"
            disabled={disabled}
            onClick={() => onQrIdChange('')}
          >
            ×
          </button>
        </div>
      ) : null}

      <div
        id={READER_ID}
        className={`comp-qr-camera ${cameraOn ? 'is-live' : ''}`}
        aria-hidden={!cameraOn}
      />

      {cameraError ? <p className="comp-inline-error">{cameraError}</p> : null}

      <label className="comp-field">
        <span className="comp-field-label">ID personaggio (elimina oggetto)</span>
        <input
          type="text"
          className="comp-sci-input"
          value={personaggioId}
          disabled={disabled}
          placeholder="Obbligatorio per consumare oggetto da QR"
          onChange={(e) => onPersonaggioIdChange(e.target.value)}
        />
      </label>
    </div>
  );
}
