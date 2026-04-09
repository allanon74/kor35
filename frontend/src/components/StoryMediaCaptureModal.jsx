import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Camera, FlipHorizontal2, FolderOpen, Video, StopCircle } from 'lucide-react';

const StoryMediaCaptureModal = ({ open, onClose, onPickFile }) => {
  const archiveInputRef = useRef(null);
  const rearPhotoInputRef = useRef(null);
  const rearVideoInputRef = useRef(null);
  const frontPhotoInputRef = useRef(null);
  const frontVideoInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const streamRef = useRef(null);

  const [mode, setMode] = useState('picker'); // picker | camera
  const [facingMode, setFacingMode] = useState('environment');
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  const canUseMediaDevices = useMemo(
    () => typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia,
    []
  );

  const stopStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraReady(false);
  };

  const bootCamera = async (face = facingMode) => {
    if (!canUseMediaDevices) {
      setCameraError('Camera in-app non supportata su questo browser.');
      return;
    }
    setCameraError('');
    stopStream();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: face } },
        audio: true,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraReady(true);
    } catch (e) {
      setCameraError('Impossibile accedere alla camera/microfono.');
      setCameraReady(false);
    }
  };

  useEffect(() => {
    if (!open) {
      setMode('picker');
      setCameraError('');
      setIsRecording(false);
      setRecordingSeconds(0);
      stopStream();
      return;
    }
    return () => {
      stopStream();
    };
  }, [open]);

  useEffect(() => {
    if (!open || mode !== 'camera') return;
    bootCamera(facingMode);
  }, [open, mode, facingMode]);

  useEffect(() => {
    if (!isRecording) return;
    const id = window.setInterval(() => setRecordingSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, [isRecording]);

  const handleFilePicked = (file) => {
    if (!file) return;
    onPickFile?.(file);
    onClose?.();
  };

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const v = videoRef.current;
    const canvas = canvasRef.current;
    const w = v.videoWidth || 1080;
    const h = v.videoHeight || 1920;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(v, 0, 0, w, h);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], `story-photo-${Date.now()}.jpg`, { type: 'image/jpeg' });
        handleFilePicked(file);
      },
      'image/jpeg',
      0.9
    );
  };

  const startRecording = () => {
    if (!streamRef.current || isRecording) return;
    recordedChunksRef.current = [];
    setRecordingSeconds(0);
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : 'video/webm';
    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    mediaRecorderRef.current = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) recordedChunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(recordedChunksRef.current, { type: mimeType });
      const file = new File([blob], `story-video-${Date.now()}.webm`, { type: mimeType });
      setIsRecording(false);
      handleFilePicked(file);
    };
    recorder.start(250);
    setIsRecording(true);
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === 'inactive') return;
    recorder.stop();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/75 z-50 flex items-center justify-center p-3">
      <div className="w-full max-w-md rounded-2xl border border-amber-300/30 bg-[#17101d] p-4 space-y-3 shadow-2xl">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-amber-100">Carica media story</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-white">X</button>
        </div>

        {mode === 'picker' && (
          <>
            <div className="grid grid-cols-1 gap-2">
              <button
                type="button"
                onClick={() => archiveInputRef.current?.click?.()}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-indigo-300/30 bg-indigo-900/25 hover:bg-indigo-900/35 text-indigo-100 font-semibold px-3 py-3"
              >
                <FolderOpen size={18} /> Sfoglia archivio
              </button>
              <button
                type="button"
                onClick={() => rearPhotoInputRef.current?.click?.()}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-amber-300/30 bg-amber-900/20 hover:bg-amber-900/30 text-amber-100 font-semibold px-3 py-3"
              >
                <Camera size={18} /> Scatta foto (posteriore)
              </button>
              <button
                type="button"
                onClick={() => rearVideoInputRef.current?.click?.()}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-amber-300/30 bg-amber-900/15 hover:bg-amber-900/25 text-amber-100 font-semibold px-3 py-3"
              >
                <Video size={18} /> Registra video (posteriore)
              </button>
              <button
                type="button"
                onClick={() => frontPhotoInputRef.current?.click?.()}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-fuchsia-300/30 bg-fuchsia-900/20 hover:bg-fuchsia-900/30 text-fuchsia-100 font-semibold px-3 py-3"
              >
                <Camera size={18} /> Scatta foto (frontale)
              </button>
              <button
                type="button"
                onClick={() => frontVideoInputRef.current?.click?.()}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-fuchsia-300/30 bg-fuchsia-900/15 hover:bg-fuchsia-900/25 text-fuchsia-100 font-semibold px-3 py-3"
              >
                <Video size={18} /> Registra video (frontale)
              </button>
              <button
                type="button"
                onClick={() => setMode('camera')}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-emerald-300/30 bg-emerald-900/20 hover:bg-emerald-900/30 text-emerald-100 font-semibold px-3 py-3"
              >
                <Camera size={18} /> Apri Camera Studio (pro)
              </button>
            </div>
            <input ref={archiveInputRef} type="file" accept="image/*,video/*" className="hidden" onChange={(e) => handleFilePicked(e.target.files?.[0] || null)} />
            <input ref={rearPhotoInputRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => handleFilePicked(e.target.files?.[0] || null)} />
            <input ref={rearVideoInputRef} type="file" accept="video/*" capture="environment" className="hidden" onChange={(e) => handleFilePicked(e.target.files?.[0] || null)} />
            <input ref={frontPhotoInputRef} type="file" accept="image/*" capture="user" className="hidden" onChange={(e) => handleFilePicked(e.target.files?.[0] || null)} />
            <input ref={frontVideoInputRef} type="file" accept="video/*" capture="user" className="hidden" onChange={(e) => handleFilePicked(e.target.files?.[0] || null)} />
          </>
        )}

        {mode === 'camera' && (
          <div className="space-y-3">
            <div className="relative rounded-xl overflow-hidden border border-white/10 bg-black">
              <video ref={videoRef} className="w-full aspect-9/16 object-cover" playsInline muted={!isRecording} />
              <canvas ref={canvasRef} className="hidden" />
            </div>
            {cameraError && <div className="text-xs text-rose-300">{cameraError}</div>}
            <div className="flex items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => setFacingMode((f) => (f === 'environment' ? 'user' : 'environment'))}
                className="px-3 py-2 rounded-lg border border-white/20 bg-white/5 hover:bg-white/10 text-xs inline-flex items-center gap-2"
              >
                <FlipHorizontal2 size={14} /> Toggle camera
              </button>
              <button
                type="button"
                onClick={capturePhoto}
                disabled={!cameraReady || isRecording}
                className="px-3 py-2 rounded-lg border border-amber-300/30 bg-amber-900/25 hover:bg-amber-900/35 text-xs inline-flex items-center gap-2 disabled:opacity-60"
              >
                <Camera size={14} /> Scatta foto
              </button>
              {!isRecording ? (
                <button
                  type="button"
                  onClick={startRecording}
                  disabled={!cameraReady}
                  className="px-3 py-2 rounded-lg border border-rose-300/30 bg-rose-900/25 hover:bg-rose-900/35 text-xs inline-flex items-center gap-2 disabled:opacity-60"
                >
                  <Video size={14} /> Registra video
                </button>
              ) : (
                <button
                  type="button"
                  onClick={stopRecording}
                  className="px-3 py-2 rounded-lg border border-rose-300/40 bg-rose-900/35 hover:bg-rose-900/45 text-xs inline-flex items-center gap-2"
                >
                  <StopCircle size={14} /> Stop ({recordingSeconds}s)
                </button>
              )}
              <button
                type="button"
                onClick={() => setMode('picker')}
                className="ml-auto px-3 py-2 rounded-lg border border-gray-500/30 bg-gray-700/25 hover:bg-gray-700/35 text-xs"
              >
                Torna al picker
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StoryMediaCaptureModal;

