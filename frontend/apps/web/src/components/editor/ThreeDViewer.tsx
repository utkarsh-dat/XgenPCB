/**
 * PCB Builder - 3D Viewer Component
 * Simple 3D-like preview using CSS transforms
 */

import { useState, useEffect, useRef } from 'react';

interface ThreeDViewerProps {
  backgroundColor?: string;
}

interface Component {
  id: string;
  name: string;
  x: number;
  y: number;
  footprint: string;
}

export function ThreeDViewer({ backgroundColor = '#0a0e17' }: ThreeDViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [rotation, setRotation] = useState({ x: -30, y: 45 });

  const components: Component[] = [
    { id: 'U1', name: 'ESP32', x: 0, y: 0, footprint: 'QFN-48' },
    { id: 'C1', name: 'C1', x: -15, y: 10, footprint: '0603' },
    { id: 'C2', name: 'C2', x: -10, y: -10, footprint: '0603' },
    { id: 'R1', name: 'R1', x: 10, y: 10, footprint: '0603' },
    { id: 'J1', name: 'J1', x: -20, y: 0, footprint: 'USB-C' },
    { id: 'LED1', name: 'LED1', x: 15, y: -5, footprint: '0603' },
  ];

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

    container.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      container.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const boardStyle = {
    width: 160,
    height: 120,
    background: 'linear-gradient(135deg, #1a5f2a 0%, #0d3d18 100%)',
    border: '2px solid #2a7f3a',
    transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
    transformStyle: 'preserve-3d' as const,
  };

  const getComponentStyle = (comp: Component) => {
    const isIC = comp.footprint.includes('QFN');
    const width = isIC ? 25 : 12;
    const height = isIC ? 18 : 10;
    return {
      position: 'absolute' as const,
      left: comp.x + 80,
      top: comp.y + 60,
      width,
      height,
      background: isIC ? '#333' : '#222',
      border: '1px solid #b87333',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 8,
      color: '#fff',
    };
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
      }}
    >
      {/* PCB Board */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: `translate(-50%, -50%) ${boardStyle.transformStyle || ''}`,
      }}>
        <div style={boardStyle}>
          {/* Components */}
          {components.map(comp => (
            <div key={comp.id} style={getComponentStyle(comp)}>
              {comp.name}
            </div>
          ))}
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
        <button className="btn btn--ghost btn--sm" title="Reset" onClick={() => setRotation({ x: -30, y: 45 })}>
          ↺
        </button>
        <button className="btn btn--ghost btn--sm" title="Top" onClick={() => setRotation({ x: 0, y: 0 })}>
          ⊤
        </button>
        <button className="btn btn--ghost btn--sm" title="Front" onClick={() => setRotation({ x: -90, y: 0 })}>
          ▣
        </button>
        <button className="btn btn--ghost btn--sm" title="Iso" onClick={() => setRotation({ x: -30, y: 45 })}>
          ⬡
        </button>
      </div>

      {/* Instructions */}
      <div style={{
        position: 'absolute',
        top: 16,
        left: 16,
        color: '#64748b',
        fontSize: 12,
      }}>
        Drag to rotate • Scroll to zoom
      </div>
    </div>
  );
}

export default ThreeDViewer;