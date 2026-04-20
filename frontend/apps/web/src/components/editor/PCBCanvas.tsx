/**
 * PCB Builder - Simple Canvas Component
 * Professional PCB rendering without heavy dependencies
 */

import { useRef, useEffect, useState } from 'react';

interface PCBComponent {
  id: string;
  name: string;
  x: number;
  y: number;
  rotation: number;
  footprint: string;
}

interface PCBCanvasProps {
  design?: {
    id: string;
    width: number;
    height: number;
    components: PCBComponent[];
  };
}

const COLORS = {
  board: '#1a5f2a',
  copper: '#b87333',
  silkscreen: '#ffffff',
  trace: '#e8a849',
  via: '#c0c0c0',
  background: '#0a0e17',
  grid: '#1a2332',
};

export function PCBCanvas({ design }: PCBCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom] = useState(3);

  const defaultComponents: PCBComponent[] = [
    { id: 'U1', name: 'ESP32', x: 150, y: 150, rotation: 0, footprint: 'QFN-48' },
    { id: 'C1', name: 'C1', x: 100, y: 100, rotation: 0, footprint: '0603' },
    { id: 'C2', name: 'C2', x: 100, y: 120, rotation: 90, footprint: '0603' },
    { id: 'R1', name: 'R1', x: 200, y: 100, rotation: 0, footprint: '0603' },
    { id: 'J1', name: 'J1', x: 50, y: 150, rotation: 0, footprint: 'USB-C' },
    { id: 'LED1', name: 'LED1', x: 250, y: 100, rotation: 0, footprint: '0603' },
  ];

  const components = design?.components || defaultComponents;

  const draw = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = COLORS.background;
    ctx.fillRect(0, 0, width, height);

    const offsetX = width / 2;
    const offsetY = height / 2;

    ctx.save();
    ctx.translate(offsetX, offsetY);
    ctx.scale(zoom, zoom);

    // Grid
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 0.3;
    for (let x = -300; x <= 300; x += 25) {
      ctx.beginPath();
      ctx.moveTo(x, -300);
      ctx.lineTo(x, 300);
      ctx.stroke();
    }
    for (let y = -300; y <= 300; y += 25) {
      ctx.beginPath();
      ctx.moveTo(-300, y);
      ctx.lineTo(300, y);
      ctx.stroke();
    }

    // Board
    const boardW = (design?.width || 50) * zoom * 4;
    const boardH = (design?.height || 50) * zoom * 4;
    ctx.fillStyle = COLORS.board;
    ctx.strokeStyle = '#2a7f3a';
    ctx.lineWidth = 1;
    ctx.fillRect(-boardW / 2, -boardH / 2, boardW, boardH);
    ctx.strokeRect(-boardW / 2, -boardH / 2, boardW, boardH);

    // Components
    for (const comp of components) {
      const isIC = comp.footprint === 'QFN-48';
      const size = isIC ? 20 : 12;
      const heightMult = isIC ? 0.6 : 0.5;

      ctx.fillStyle = '#222';
      ctx.strokeStyle = COLORS.copper;
      ctx.lineWidth = 1;
      ctx.fillRect(comp.x - size / 2, comp.y - size * heightMult, size, size * heightMult * 2);
      ctx.strokeRect(comp.x - size / 2, comp.y - size * heightMult, size, size * heightMult * 2);

      // Pins for IC
      if (isIC) {
        ctx.fillStyle = COLORS.copper;
        ctx.fillRect(comp.x - size / 2, comp.y - size * heightMult - 2, 2, 2);
        ctx.fillRect(comp.x - size / 2 + 4, comp.y - size * heightMult - 2, 2, 2);
        ctx.fillRect(comp.x + size / 2 - 4, comp.y - size * heightMult - 2, 2, 2);
        ctx.fillRect(comp.x + size / 2 - 2, comp.y - size * heightMult - 2, 2, 2);
      }

      ctx.fillStyle = COLORS.silkscreen;
      ctx.font = '10px Inter';
      ctx.textAlign = 'center';
      ctx.fillText(comp.name, comp.x, comp.y + 4);
    }

    // Traces
    ctx.strokeStyle = COLORS.trace;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(50, 150);
    ctx.lineTo(100, 108);
    ctx.lineTo(130, 108);
    ctx.lineTo(130, 150);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(150, 180);
    ctx.lineTo(150, 150);
    ctx.lineTo(200, 132);
    ctx.stroke();

    // Via
    ctx.fillStyle = COLORS.via;
    ctx.beginPath();
    ctx.arc(100, 120, 4, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const resize = () => {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      draw();
    };

    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  useEffect(() => {
    draw();
  }, [design, components, zoom]);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
  };

  return (
    <div ref={containerRef} className="pcb-canvas" onWheel={handleWheel}>
      <canvas ref={canvasRef} style={{ display: 'block' }} />
      <div style={{
        position: 'absolute',
        bottom: 16,
        left: 16,
        padding: '8px 12px',
        background: 'rgba(15, 23, 42, 0.9)',
        borderRadius: 8,
        color: '#94a3b8',
        fontSize: 12,
      }}>
        {zoom.toFixed(1)}x
      </div>
    </div>
  );
}

export default PCBCanvas;