import React, { useRef, useState, useEffect } from 'react';
import { Camera, RefreshCw, Image as ImageIcon, X } from 'lucide-react';
import { compressImage, isValidImageType, COMPRESS_PRESETS } from '@/utils/imageCompress';

const OVERLAYS = {
  oval: { viewBox: '0 0 300 380', path: 'M150 30 C 70 30 40 110 40 190 C 40 270 70 350 150 350 C 230 350 260 270 260 190 C 260 110 230 30 150 30 Z' },
  rect: { viewBox: '0 0 300 190', path: 'M20 20 H280 V170 H20 Z' },
};

export default function CameraCapture({
  label,
  hint,
  facingMode = 'user',
  value,
  previewUrl,
  onChange,
  required = false,
  testId,
  preset = 'selfie',
  overlay = 'oval',
}) {
  const galleryInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [processing, setProcessing] = useState(false);

  const hasGetUserMedia = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;

  useEffect(() => {
    return () => {
      stopStream();
      // previewUrl é gerenciado pelo pai (URL.revokeObjectURL no unmount)
    };
  }, []);

  useEffect(() => {
    if (!cameraOpen) return;
    let cancelled = false;
    (async () => {
      try {
        setCameraError('');
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => {});
        }
      } catch (e) {
        setCameraError('Não foi possível abrir a câmera ao vivo. Use a galeria ou tire uma foto.');
      }
    })();
    return () => { cancelled = true; stopStream(); };
  }, [cameraOpen, facingMode]);

  const stopStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  const handleFile = async (file) => {
    if (!file) return;
    if (!isValidImageType(file)) {
      alert('Use uma imagem JPG, PNG ou WEBP.');
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      alert('Imagem muito grande (máx. 12MB).');
      return;
    }
    setProcessing(true);
    try {
      const presetCfg = COMPRESS_PRESETS[preset] || COMPRESS_PRESETS.selfie;
      const compressed = await compressImage(file, presetCfg);
      onChange(compressed);
    } catch (e) {
      alert('Não foi possível processar a imagem.');
    } finally {
      setProcessing(false);
      // reset inputs para permitir re-selecionar o mesmo arquivo
      if (galleryInputRef.current) galleryInputRef.current.value = '';
      if (cameraInputRef.current) cameraInputRef.current.value = '';
    }
  };

  const onInputChange = (e) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  const captureFromVideo = async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    // espelhar selfie
    if (facingMode === 'user') {
      ctx.translate(w, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, w, h);
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      setCameraOpen(false);
      stopStream();
      setProcessing(true);
      try {
        const file = new File([blob], 'camera.jpg', { type: 'image/jpeg' });
        const presetCfg = COMPRESS_PRESETS[preset] || COMPRESS_PRESETS.selfie;
        const compressed = await compressImage(file, presetCfg);
        onChange(compressed);
      } finally {
        setProcessing(false);
      }
    }, 'image/jpeg', 0.92);
  };

  const overlayDef = OVERLAYS[overlay] || OVERLAYS.oval;

  const abrirCamera = () => {
    if (hasGetUserMedia) {
      setCameraOpen(true);
    } else {
      cameraInputRef.current?.click();
    }
  };

  const abrirGaleria = () => {
    galleryInputRef.current?.click();
  };

  return (
    <div className="rounded-xl border border-border bg-card p-3" data-testid={testId}>
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-sm font-medium text-foreground">{label} {required && <span className="text-red-500">*</span>}</p>
          {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
        </div>
        {value && (
          <button type="button" onClick={() => onChange(null)} className="text-xs text-muted-foreground hover:text-red-500 inline-flex items-center gap-1" data-testid={`${testId}-remover`}>
            <X className="w-3.5 h-3.5" /> Remover
          </button>
        )}
      </div>

      {previewUrl ? (
        <div className="relative rounded-lg overflow-hidden bg-muted border border-border">
          <img src={previewUrl} alt={label} className="w-full h-48 object-cover" data-testid={`${testId}-preview`} />
          <div className="absolute bottom-2 right-2 flex gap-2">
            <button type="button" onClick={() => onChange(null)} className="px-3 py-1.5 rounded-lg bg-black/60 text-white text-xs font-medium backdrop-blur inline-flex items-center gap-1.5" data-testid={`${testId}-refazer`}>
              <RefreshCw className="w-3.5 h-3.5" /> Refazer
            </button>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border-2 border-dashed border-border bg-muted/30 p-4 flex flex-col items-center justify-center gap-3 min-h-[140px]">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
            <Camera className="w-5 h-5 text-primary" />
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <button type="button" onClick={abrirCamera} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity" data-testid={`${testId}-btn-camera`}>
              <Camera className="w-4 h-4" /> Tirar foto
            </button>
            <button type="button" onClick={abrirGaleria} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-card border border-border text-foreground text-sm font-medium hover:bg-muted/60 transition-colors" data-testid={`${testId}-btn-galeria`}>
              <ImageIcon className="w-4 h-4 text-primary" /> Escolher da Galeria
            </button>
          </div>
          <p className="text-[11px] text-muted-foreground text-center">JPG, PNG ou WEBP · até 12MB (comprimida automaticamente)</p>
        </div>
      )}

      {processing && <p className="text-xs text-primary font-medium animate-pulse mt-2">Processando e otimizando imagem…</p>}

      {/* Input de Galeria: SEM atributo capture para abrir o seletor de arquivos/galeria */}
      <input
        ref={galleryInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/jpg"
        className="hidden"
        onChange={onInputChange}
        data-testid={`${testId}-gallery-input`}
      />

      {/* Input de Câmera (fallback quando getUserMedia indisponível): COM capture */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/jpg"
        capture={facingMode === 'user' ? 'user' : 'environment'}
        className="hidden"
        onChange={onInputChange}
        data-testid={`${testId}-camera-input`}
      />

      {/* Modal câmera ao vivo */}
      {cameraOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 flex flex-col items-center justify-center p-4" data-testid={`${testId}-camera-modal`}>
          <div className="relative w-full max-w-md bg-black rounded-2xl overflow-hidden shadow-2xl">
            <video ref={videoRef} autoPlay playsInline muted className={`w-full h-[380px] object-cover ${facingMode === 'user' ? 'scale-x-[-1]' : ''}`} data-testid={`${testId}-video`} />
            {/* overlay guia */}
            <svg viewBox={overlayDef.viewBox} className="absolute inset-0 w-full h-full pointer-events-none" preserveAspectRatio="xMidYMid meet">
              <path d={overlayDef.path} fill="none" stroke="rgba(255,255,255,0.9)" strokeWidth="2" strokeDasharray="8 6" />
            </svg>
            <canvas ref={canvasRef} className="hidden" />
            {cameraError && <p className="absolute bottom-20 left-0 right-0 text-center text-xs text-amber-300 px-4">{cameraError}</p>}
            <div className="absolute bottom-0 left-0 right-0 p-4 flex items-center justify-between gap-3 bg-gradient-to-t from-black/80 to-transparent">
              <button type="button" onClick={() => { setCameraOpen(false); stopStream(); }} className="px-4 py-2 rounded-lg bg-white/20 text-white text-sm hover:bg-white/30" data-testid={`${testId}-camera-cancelar`}>Cancelar</button>
              <button type="button" onClick={captureFromVideo} className="w-14 h-14 rounded-full bg-white border-4 border-emerald-500/50 shadow-lg active:scale-95 transition-transform" aria-label="Capturar foto" data-testid={`${testId}-camera-capturar`} />
              <button type="button" onClick={() => { setCameraOpen(false); stopStream(); abrirGaleria(); }} className="px-4 py-2 rounded-lg bg-white/20 text-white text-sm hover:bg-white/30" data-testid={`${testId}-camera-galeria`}>Galeria</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
