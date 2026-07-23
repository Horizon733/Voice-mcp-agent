import { useEffect, useRef } from "react";

function drawGrid(ctx, width, height) {
  ctx.save();
  ctx.strokeStyle = "rgba(255, 196, 107, 0.12)";
  ctx.lineWidth = 1;

  for (let x = 0; x < width; x += 20) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  for (let y = 0; y < height; y += 20) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  ctx.restore();
}

function drawWave(ctx, width, height, time, config) {
  const { amplitude, frequency, speed, phase, color, thickness } = config;

  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = thickness;

  for (let x = 0; x <= width; x += 1) {
    const n = x / width;
    const y =
      height * 0.5 +
      Math.sin(n * frequency + time * speed + phase) * amplitude +
      Math.sin(n * (frequency * 0.52) - time * speed * 0.7) * amplitude * 0.35;

    if (x === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }

  ctx.stroke();
}

export default function AnalogWavesPanel() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return undefined;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return undefined;
    }

    let raf = 0;

    const render = (t) => {
      const cssWidth = canvas.clientWidth;
      const cssHeight = canvas.clientHeight;
      const dpr = window.devicePixelRatio || 1;

      if (canvas.width !== Math.floor(cssWidth * dpr) || canvas.height !== Math.floor(cssHeight * dpr)) {
        canvas.width = Math.floor(cssWidth * dpr);
        canvas.height = Math.floor(cssHeight * dpr);
      }

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cssWidth, cssHeight);

      drawGrid(ctx, cssWidth, cssHeight);

      const time = t * 0.001;
      drawWave(ctx, cssWidth, cssHeight, time, {
        amplitude: 16,
        frequency: 16,
        speed: 1.5,
        phase: 0,
        color: "rgba(255, 225, 158, 0.86)",
        thickness: 1.8
      });
      drawWave(ctx, cssWidth, cssHeight, time, {
        amplitude: 10,
        frequency: 22,
        speed: 2.1,
        phase: 1.8,
        color: "rgba(255, 179, 84, 0.9)",
        thickness: 1.2
      });
      drawWave(ctx, cssWidth, cssHeight, time, {
        amplitude: 22,
        frequency: 10,
        speed: 1.1,
        phase: 2.6,
        color: "rgba(255, 146, 52, 0.5)",
        thickness: 1
      });

      raf = window.requestAnimationFrame(render);
    };

    raf = window.requestAnimationFrame(render);

    return () => {
      window.cancelAnimationFrame(raf);
    };
  }, []);

  return <canvas ref={canvasRef} className="waves-canvas" />;
}
