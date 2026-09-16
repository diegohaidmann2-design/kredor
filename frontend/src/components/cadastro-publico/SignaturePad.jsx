import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Eraser, Check, Maximize2, X, CheckCircle2, RotateCcw } from 'lucide-react';

export default function SignaturePad({ value, onChange, testId = 'signature-pad' }) {
  const canvasRef = useRef(null);
  const wrapperRef = useRef(null);
  const fsCanvasRef = useRef(null);
  const fsWrapperRef = useRef(null);

  const drawingRef = useRef(false);
  const hasDrawnRef = useRef(false);
  const lastRef = useRef({ x: 0, y: 0 });

  const [empty, setEmpty] = useState(!value);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [fsHasDrawn, setFsHasDrawn] = useState(false);

  // Renderiza a imagem do `value` no canvas inline sempre que `value` mudar
  const desenharValorNoCanvas = useCallback((dataUrl) => {
    const canvas = canvasRef.current;
    const wrapper = wrapperRef.current;
    if (!canvas || !wrapper) return;
    const ctx = canvas.getContext('2d');
    const rect = wrapper.getBoundingClientRect();
    if (rect.width <= 0) return;

    if (!dataUrl) {
      ctx.clearRect(0, 0, rect.width, 160);
      setEmpty(true);
      return;
    }

    const img = new Image();
    img.onload = () => {
      ctx.clearRect(0, 0, rect.width, 160);
      const scale = Math.min(rect.width / img.width, 140 / img.height, 1);
      const drawW = img.width * scale;
      const drawH = img.height * scale;
      const offsetX = (rect.width - drawW) / 2;
      const offsetY = (160 - drawH) / 2;
      ctx.drawImage(img, offsetX, offsetY, drawW, drawH);
      setEmpty(false);
    };
    img.src = dataUrl;
  }, []);

  // Redimensiona e ajusta DPI do canvas inline
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const wrapper = wrapperRef.current;
    if (!canvas || !wrapper) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = wrapper.getBoundingClientRect();
    if (rect.width <= 0) return;

    const w = Math.round(rect.width * dpr);
    const h = Math.round(160 * dpr);

    canvas.width = w;
    canvas.height = h;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '160px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2.4;

    if (value) {
      desenharValorNoCanvas(value);
    }
  }, [value, desenharValorNoCanvas]);

  // Redimensiona o canvas em Tela Cheia
  const resizeFsCanvas = useCallback(() => {
    const canvas = fsCanvasRef.current;
    const wrapper = fsWrapperRef.current;
    if (!canvas || !wrapper) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = wrapper.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    const w = Math.round(rect.width * dpr);
    const h = Math.round(rect.height * dpr);

    canvas.width = w;
    canvas.height = h;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 3.2;

    if (value) {
      const img = new Image();
      img.onload = () => {
        const scale = Math.min((rect.width * 0.9) / img.width, (rect.height * 0.8) / img.height, 1);
        const drawW = img.width * scale;
        const drawH = img.height * scale;
        const offsetX = (rect.width - drawW) / 2;
        const offsetY = (rect.height - drawH) / 2;
        ctx.drawImage(img, offsetX, offsetY, drawW, drawH);
      };
      img.src = value;
      setFsHasDrawn(true);
    }
  }, [value]);

  useEffect(() => {
    resizeCanvas();
    const ro = new ResizeObserver(resizeCanvas);
    if (wrapperRef.current) ro.observe(wrapperRef.current);
    return () => ro.disconnect();
  }, [resizeCanvas]);

  useEffect(() => {
    if (value) {
      desenharValorNoCanvas(value);
    } else {
      setEmpty(true);
    }
  }, [value, desenharValorNoCanvas]);

  useEffect(() => {
    if (!isFullScreen) return;
    const t = setTimeout(() => {
      resizeFsCanvas();
    }, 60);
    const ro = new ResizeObserver(resizeFsCanvas);
    if (fsWrapperRef.current) ro.observe(fsWrapperRef.current);
    return () => {
      clearTimeout(t);
      ro.disconnect();
    };
  }, [isFullScreen, resizeFsCanvas]);

  const getPos = (e, canvas) => {
    const rect = canvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return { x: clientX - rect.left, y: clientY - rect.top };
  };

  // Handlers para o canvas normal (inline)
  const startInline = (e) => {
    e.preventDefault();
    drawingRef.current = true;
    lastRef.current = getPos(e, canvasRef.current);
  };
  const moveInline = (e) => {
    if (!drawingRef.current) return;
    e.preventDefault();
    const pos = getPos(e, canvasRef.current);
    const ctx = canvasRef.current.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(lastRef.current.x, lastRef.current.y);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
    lastRef.current = pos;
    hasDrawnRef.current = true;
    if (empty) setEmpty(false);
  };
  const endInline = () => {
    if (!drawingRef.current) return;
    drawingRef.current = false;
    if (hasDrawnRef.current) {
      const dataUrl = canvasRef.current.toDataURL('image/png');
      onChange(dataUrl);
    }
  };

  const clearInline = () => {
    const canvas = canvasRef.current;
    if (!canvas || !wrapperRef.current) return;
    const rect = wrapperRef.current.getBoundingClientRect();
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, rect.width, 160);
    hasDrawnRef.current = false;
    setEmpty(true);
    onChange(null);
  };

  // Handlers para o canvas em Tela Cheia
  const startFs = (e) => {
    e.preventDefault();
    drawingRef.current = true;
    lastRef.current = getPos(e, fsCanvasRef.current);
  };
  const moveFs = (e) => {
    if (!drawingRef.current) return;
    e.preventDefault();
    const pos = getPos(e, fsCanvasRef.current);
    const ctx = fsCanvasRef.current.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(lastRef.current.x, lastRef.current.y);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
    lastRef.current = pos;
    setFsHasDrawn(true);
  };
  const endFs = () => {
    if (!drawingRef.current) return;
    drawingRef.current = false;
  };

  const clearFs = () => {
    const canvas = fsCanvasRef.current;
    if (!canvas || !fsWrapperRef.current) return;
    const rect = fsWrapperRef.current.getBoundingClientRect();
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, rect.width, rect.height);
    setFsHasDrawn(false);
  };

  const confirmarFs = () => {
    if (!fsCanvasRef.current) return;
    if (fsHasDrawn) {
      const dataUrl = fsCanvasRef.current.toDataURL('image/png');
      onChange(dataUrl);
      setEmpty(false);
      hasDrawnRef.current = true;
      desenharValorNoCanvas(dataUrl);
    }
    setIsFullScreen(false);
  };

  const abrirFullScreen = () => {
    setFsHasDrawn(!empty);
    setIsFullScreen(true);
  };

  return (
    <div className="rounded-xl border border-border bg-card p-3" data-testid={testId}>
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-sm font-medium text-foreground">Assinatura Digital</p>
          <p className="text-xs text-muted-foreground">Desenhe sua assinatura com o dedo ou mouse</p>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={abrirFullScreen}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 text-xs font-semibold transition-colors"
            data-testid={`${testId}-tela-cheia`}
            title="Abrir em Tela Cheia para desenhar melhor"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            <span>Tela cheia</span>
          </button>
          <button
            type="button"
            onClick={clearInline}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-muted text-foreground text-xs font-medium hover:bg-muted/70 transition-colors"
            data-testid={`${testId}-limpar`}
          >
            <Eraser className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Limpar</span>
          </button>
        </div>
      </div>

      <div
        ref={wrapperRef}
        className="relative rounded-lg border border-border bg-white overflow-hidden touch-none select-none shadow-inner"
        style={{ height: 160 }}
        data-testid={`${testId}-wrapper`}
      >
        <canvas
          ref={canvasRef}
          className="block touch-none cursor-crosshair"
          onMouseDown={startInline}
          onMouseMove={moveInline}
          onMouseUp={endInline}
          onMouseLeave={endInline}
          onTouchStart={startInline}
          onTouchMove={moveInline}
          onTouchEnd={endInline}
          data-testid={`${testId}-canvas`}
        />
        {/* Linha guia de assinatura */}
        <div className="absolute bottom-6 left-6 right-6 border-b border-dashed border-slate-300 pointer-events-none flex justify-between text-[10px] text-slate-400">
          <span>Assine sobre a linha</span>
          <span>✕</span>
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between">
        {!empty ? (
          <p className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
            <Check className="w-3.5 h-3.5" /> Assinatura capturada
          </p>
        ) : (
          <p className="text-[11px] text-muted-foreground">Toque e arraste para assinar</p>
        )}
        <button
          type="button"
          onClick={abrirFullScreen}
          className="text-xs text-primary hover:underline font-medium inline-flex items-center gap-1"
        >
          <Maximize2 className="w-3 h-3" /> Assinar em tela cheia
        </button>
      </div>

      {/* MODAL FULLSCREEN DE ASSINATURA */}
      {isFullScreen && (
        <div className="fixed inset-0 z-50 bg-background flex flex-col p-3 sm:p-6" data-testid={`${testId}-fs-modal`}>
          {/* Header do modal */}
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div>
              <h2 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
                ✍️ Assinatura em Tela Cheia
              </h2>
              <p className="text-xs text-muted-foreground">
                Gire o celular na horizontal se preferir mais espaço.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsFullScreen(false)}
              className="p-2 rounded-lg bg-muted text-muted-foreground hover:text-foreground"
              data-testid={`${testId}-fs-fechar`}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Área do Canvas Fullscreen */}
          <div
            ref={fsWrapperRef}
            className="flex-1 my-3 relative rounded-xl border-2 border-dashed border-primary/40 bg-white overflow-hidden touch-none select-none shadow-sm"
          >
            <canvas
              ref={fsCanvasRef}
              className="w-full h-full block touch-none cursor-crosshair"
              onMouseDown={startFs}
              onMouseMove={moveFs}
              onMouseUp={endFs}
              onMouseLeave={endFs}
              onTouchStart={startFs}
              onTouchMove={moveFs}
              onTouchEnd={endFs}
              data-testid={`${testId}-fs-canvas`}
            />
            {/* Guia visual */}
            <div className="absolute bottom-12 left-8 right-8 border-b-2 border-dashed border-slate-300 pointer-events-none flex justify-between items-center text-xs text-slate-400">
              <span>Assine com o dedo ou caneta sobre a linha</span>
              <span className="font-bold text-sm">✕</span>
            </div>
          </div>

          {/* Footer com botões de ação */}
          <div className="flex items-center justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={clearFs}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-muted text-foreground text-sm font-medium hover:bg-muted/80 transition-colors"
              data-testid={`${testId}-fs-limpar`}
            >
              <RotateCcw className="w-4 h-4" /> Limpar
            </button>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setIsFullScreen(false)}
                className="px-4 py-2.5 rounded-lg border border-border text-muted-foreground text-sm font-medium hover:bg-muted/50 transition-colors"
                data-testid={`${testId}-fs-cancelar`}
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={confirmarFs}
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-bold shadow-md hover:opacity-90 transition-opacity"
                data-testid={`${testId}-fs-confirmar`}
              >
                <CheckCircle2 className="w-4 h-4" /> Concluir Assinatura
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
