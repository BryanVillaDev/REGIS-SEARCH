import { useEffect, useRef } from "react";

/**
 * Lluvia de codigo estilo Matrix dibujada sobre un canvas a pantalla completa.
 * Se monta una sola vez detras de todo el contenido (z-index negativo via CSS).
 */
export function MatrixRain() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) {
      return;
    }
    const ctx = cv.getContext("2d");
    if (!ctx) {
      return;
    }
    const canvas: HTMLCanvasElement = cv;
    const g: CanvasRenderingContext2D = ctx;

    const glyphs = "01ABCDEF#*<>$@";
    const fontSize = 16;
    let width = 0;
    let height = 0;
    let drops: number[] = [];

    function resize() {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      const columns = Math.floor(width / fontSize);
      drops = new Array(columns).fill(0).map(() => Math.floor(Math.random() * -50));
    }
    resize();

    function paint() {
      // Estela: fade negro semitransparente sobre el frame anterior.
      g.fillStyle = "rgba(0, 6, 0, 0.09)";
      g.fillRect(0, 0, width, height);

      g.fillStyle = "#00ff41";
      g.font = `${fontSize}px 'Share Tech Mono', monospace`;

      for (let i = 0; i < drops.length; i++) {
        const char = glyphs[Math.floor(Math.random() * glyphs.length)];
        const y = drops[i] * fontSize;
        g.fillText(char, i * fontSize, y);
        if (y > height && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i] += 1;
      }
    }

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.addEventListener("resize", resize);

    if (reduceMotion) {
      // Un solo frame estatico, sin animacion.
      g.fillStyle = "#000600";
      g.fillRect(0, 0, width, height);
      paint();
      return () => window.removeEventListener("resize", resize);
    }

    let raf = 0;
    let last = 0;
    const interval = 55; // ms entre frames -> caida sutil

    function loop(now: number) {
      raf = requestAnimationFrame(loop);
      if (now - last < interval) {
        return;
      }
      last = now;
      paint();
    }
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="matrix-rain" aria-hidden="true" />;
}
