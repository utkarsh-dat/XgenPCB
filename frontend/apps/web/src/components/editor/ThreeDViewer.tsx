/**
 * PCB Builder - 3D Viewer Component
 * Renders PCB with components, traces, and vias in 3D
 */

import { useState, useEffect, useRef } from 'react';

interface BoardConfig {
  width_mm: number;
  height_mm: number;
  layers: number;
}

interface PlacedComponent {
  id: string;
  name: string;
  footprint: string;
  x: number;
  y: number;
  rotation: number;
  layer: string;
}

interface Track {
  start: [number, number];
  end: [number, number];
  width: number;
  layer: string;
  net?: string;
}

interface Via {
  x: number;
  y: number;
  from_layer: number;
  to_layer: number;
}

interface PCBData {
  board_config?: BoardConfig;
  placed_components?: PlacedComponent[];
  tracks?: Track[];
  vias?: Via[];
}

interface ThreeDViewerProps {
  data?: PCBData;
  backgroundColor?: string;
  showTraces?: boolean;
  showVias?: boolean;
}

const FOOTPRINT_SIZES: Record<string, { width: number; height: number }> = {
  'QFN-48': { width: 7, height: 7 },
  'QFN-32': { width: 5, height: 5 },
  'QFN-24': { width: 4, height: 4 },
  'SOIC-8': { width: 4.9, height: 3.9 },
  'SOIC-16': { width: 6.4, height: 3.9 },
  '0603': { width: 1.6, height: 0.8 },
  '0805': { width: 2.0, height: 1.25 },
  '1206': { width: 3.2, height: 1.6 },
  'USB-C': { width: 8.4, height: 2.4 },
  'Header-2x5': { width: 10.16, height: 5.08 },
  'SOT-23': { width: 3.0, height: 1.5 },
  'SOT-223': { width: 6.5, height: 3.5 },
  'TO-220': { width: 10.16, height: 4.45 },
};

function getFootprintSize(footprint: string): { width: number; height: number } {
  const fp = footprint.toUpperCase();
  for (const [key, size] of Object.entries(FOOTPRINT_SIZES)) {
    if (fp.includes(key)) return size;
  }
  return { width: 4, height: 4 };
}

export function ThreeDViewer({
  data,
  backgroundColor = '#0a0e17',
  showTraces = true,
  showVias = true,
}: ThreeDViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [rotation, setRotation] = useState({ x: -30, y: 45 });
  const [zoom, setZoom] = useState(1);

  const boardConfig = data?.board_config || { width_mm: 100, height_mm: 80, layers: 2 };
  const components = data?.placed_components || [];
  const tracks = data?.tracks || [];
  const vias = data?.vias || [];

  useEffect(() => {
    let isDragging = false;
    let lastX = 0;
    let lastY = 0;

    const container = containerRef.current;
    if (!container) return;

    const handleMouseDown = (e: MouseEvent) => {
      isDragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - lastX;
      const deltaY = e.clientY - lastY;
      setRotation(r => ({ x: r.x + deltaY * 0.5, y: r.y + deltaX * 0.5 }));
      lastX = e.clientX;
      lastY = e.clientY;
    };

    const handleMouseUp = () => {
      isDragging = false;
    };

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      setZoom(z => Math.max(0.5, Math.min(3, z - e.deltaY * 0.001)));
    };

    container.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    container.addEventListener('wheel', handleWheel);

    return () => {
      container.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      container.removeEventListener('wheel', handleWheel);
    };
  }, []);

  const scale = 1.5 * zoom;
  const boardWidth = boardConfig.width_mm * scale;
  const boardHeight = boardConfig.height_mm * scale;

  const boardStyle = {
    width: boardWidth,
    height: boardHeight,
    background: 'linear-gradient(135deg, #1a472a 0%, #0d3318 100%)',
    border: '2px solid #3a7f4a',
    transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
    transformStyle: 'preserve-3d' as const,
  };

  const getComponentStyle = (comp: PlacedComponent) => {
    const sizes = getFootprintSize(comp.footprint);
    const isIC = comp.footprint.includes('QFN') || comp.footprint.includes('SOIC');
    return {
      position: 'absolute' as const,
      left: comp.x * scale + boardWidth / 2 - sizes.width * scale / 2,
      top: comp.y * scale + boardHeight / 2 - sizes.height * scale / 2,
      width: sizes.width * scale,
      height: sizes.height * scale,
      background: isIC ? '#2a2a2a' : '#1a1a1a',
      border: '1px solid #b87333',
      borderRadius: isIC ? 2 : 1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: Math.max(6, 8 * scale),
      color: '#ccc',
      transform: `rotate(${comp.rotation}deg)`,
    };
  };

  const renderTrace = (track: Track, index: number) => {
    if (!showTraces) return null;
    if (!track.start || !track.end) return null;

    const x1 = track.start[0] * scale;
    const y1 = track.start[1] * scale;
    const x2 = track.end[0] * scale;
    const y2 = track.end[1] * scale;

    if (x1 === x2 && y1 === y2) return null;

    const length = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
    const angle = Math.atan2(y2 - y1, x2 - x1) * (180 / Math.PI);
    const width = (track.width || 0.25) * scale;

    const onTop = track.layer?.startsWith('F');

    return (
      <div
        key={`track-${index}`}
        style={{
          position: 'absolute',
          left: x1 + boardWidth / 2,
          top: y1 + boardHeight / 2,
          width: length,
          height: width,
          background: '#c87533',
          transformOrigin: '0 50%',
          transform: `rotate(${angle}deg)`,
          transformStyle: 'preserve-3d',
          zIndex: onTop ? 1 : 0,
          boxShadow: '0 0 1px rgba(200,117,51,0.5)',
        }}
      />
    );
  };

  const renderVia = (via: Via, index: number) => {
    if (!showVias) return null;

    return (
      <div
        key={`via-${index}`}
        style={{
          position: 'absolute',
          left: via.x * scale + boardWidth / 2 - 3 * scale,
          top: via.y * scale + boardHeight / 2 - 3 * scale,
          width: 6 * scale,
          height: 6 * scale,
          background: 'radial-gradient(circle, #d4af37 30%, #8b7355 100%)',
          borderRadius: '50%',
          boxShadow: '0 0 2px rgba(212,175,55,0.5)',
        }}
        title={`Via @ (${via.x}, ${via.y}) L${via.from_layer}→L${via.to_layer}`}
      />
    );
  };

  return (
    <div 
      ref={containerRef} 
      className="three-d-viewer"
      style={{ 
        width: '100%', 
        height: '100%', 
        background: backgroundColor,
        perspective: '800px',
        overflow: 'hidden',
        cursor: 'grab',
        position: 'relative',
      }}
    >
      {/* PCB Board with traces */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: `translate(-50%, -50%)`,
      }}>
        {/* Traces layer */}
        <div style={{
          position: 'absolute',
          width: boardWidth,
          height: boardHeight,
          left: -boardWidth / 2,
          top: -boardHeight / 2,
        }}>
          {tracks.map((track, i) => renderTrace(track, i))}
        </div>

        {/* Main board */}
        <div style={boardStyle}>
          {/* Components */}
          {components.map(comp => (
            <div key={comp.id} style={getComponentStyle(comp)}>
              {comp.name}
            </div>
          ))}

          {/* Vias overlay */}
          <div style={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            left: 0,
            top: 0,
            pointerEvents: 'none',
          }}>
            {vias.map((via, i) => renderVia(via, i))}
          </div>
        </div>
      </div>

      {/* 3D Controls */}
      <div style={{
        position: 'absolute',
        bottom: 16,
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        gap: 8,
        padding: '8px 16px',
        background: 'rgba(15, 23, 42, 0.9)',
        borderRadius: 8,
        backdropFilter: 'blur(10px)',
      }}>
        <button 
          className="btn btn--ghost btn--sm" 
          title="Reset" 
          onClick={() => setRotation({ x: -30, y: 45 })}
        >
          ↺
        </button>
        <button 
          className="btn btn--ghost btn--sm" 
          title="Top" 
          onClick={() => setRotation({ x: 0, y: 0 })}
        >
          ⊤
        </button>
        <button 
          className="btn btn--ghost btn--sm" 
          title="Front" 
          onClick={() => setRotation({ x: -90, y: 0 })}
        >
          ▣
        </button>
        <button 
          className="btn btn--ghost btn--sm" 
          title="Iso" 
          onClick={() => setRotation({ x: -30, y: 45 })}
        >
          ⬡
        </button>
        <button
          className="btn btn--ghost btn--sm"
          title="Zoom +"
          onClick={() => setZoom(z => Math.min(3, z + 0.2))}
        >
          +
        </button>
        <button
          className="btn btn--ghost btn--sm"
          title="Zoom -"
          onClick={() => setZoom(z => Math.max(0.5, z - 0.2))}
        >
          −
        </button>
      </div>

      {/* Info panel */}
      <div style={{
        position: 'absolute',
        top: 16,
        left: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      }}>
        <div style={{ color: '#64748b', fontSize: 12 }}>
          {boardConfig.width_mm}×{boardConfig.height_mm}mm, {boardConfig.layers}L
        </div>
        <div style={{ color: '#475569', fontSize: 10 }}>
          {components.length} components, {tracks.length} traces, {vias.length} vias
        </div>
        <div style={{ color: '#64748b', fontSize: 11, marginTop: 4 }}>
          Drag to rotate • Scroll to zoom
        </div>
      </div>
    </div>
  );
}

export default ThreeDViewer;