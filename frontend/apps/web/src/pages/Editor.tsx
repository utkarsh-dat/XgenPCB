import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useUIStore, useDesignStore, useAIStore } from '../stores';
import { ChatInterface } from '../components/ai/ChatInterface';

const LAYERS = [
  { id: 'F.Cu', name: 'Front Copper', color: '#e8222e', visible: true },
  { id: 'B.Cu', name: 'Back Copper', color: '#2744e8', visible: true },
  { id: 'F.SilkS', name: 'Front Silk', color: '#f0f000', visible: true },
  { id: 'B.SilkS', name: 'Back Silk', color: '#8800ee', visible: true },
  { id: 'Edge.Cuts', name: 'Board Edge', color: '#eeee00', visible: true },
  { id: 'F.Mask', name: 'Front Mask', color: '#840084', visible: false },
  { id: 'B.Mask', name: 'Back Mask', color: '#840084', visible: false },
];

const TOOLS = [
  { id: 'select', icon: '⊹', label: 'Select (V)', key: 'v' },
  { id: 'place', icon: '◻', label: 'Place Component (P)', key: 'p' },
  { id: 'route', icon: '╱', label: 'Route Track (X)', key: 'x' },
  { id: 'measure', icon: '📏', label: 'Measure (M)', key: 'm' },
  { id: 'zone', icon: '▨', label: 'Copper Zone (Z)', key: 'z' },
];

const SAMPLE_COMPONENTS = [
  { id: 'c1', name: 'U1', footprint: 'ESP32-WROOM', x: 200, y: 150, w: 60, h: 40, rotation: 0, layer: 'F.Cu', value: 'ESP32' },
  { id: 'c2', name: 'U2', footprint: 'AMS1117-3.3', x: 100, y: 100, w: 25, h: 15, rotation: 0, layer: 'F.Cu', value: '3.3V LDO' },
  { id: 'c3', name: 'C1', footprint: '0805', x: 140, y: 100, w: 10, h: 6, rotation: 0, layer: 'F.Cu', value: '100nF' },
  { id: 'c4', name: 'C2', footprint: '0805', x: 140, y: 120, w: 10, h: 6, rotation: 0, layer: 'F.Cu', value: '10uF' },
  { id: 'c5', name: 'R1', footprint: '0402', x: 280, y: 130, w: 8, h: 4, rotation: 90, layer: 'F.Cu', value: '10K' },
  { id: 'c6', name: 'R2', footprint: '0402', x: 280, y: 145, w: 8, h: 4, rotation: 90, layer: 'F.Cu', value: '4.7K' },
  { id: 'c7', name: 'J1', footprint: 'USB-C', x: 50, y: 150, w: 20, h: 30, rotation: 0, layer: 'F.Cu', value: 'USB-C' },
  { id: 'c8', name: 'LED1', footprint: '0603', x: 300, y: 100, w: 8, h: 5, rotation: 0, layer: 'F.Cu', value: 'Green' },
];

const SAMPLE_TRACKS = [
  { x1: 120, y1: 107, x2: 140, y2: 107, layer: 'F.Cu', width: 2 },
  { x1: 150, y1: 107, x2: 190, y2: 107, layer: 'F.Cu', width: 2 },
  { x1: 190, y1: 107, x2: 190, y2: 150, layer: 'F.Cu', width: 2 },
  { x1: 70, y1: 150, x2: 100, y2: 108, layer: 'F.Cu', width: 3 },
  { x1: 260, y1: 150, x2: 280, y2: 132, layer: 'F.Cu', width: 1.5 },
  { x1: 260, y1: 160, x2: 280, y2: 147, layer: 'F.Cu', width: 1.5 },
  { x1: 300, y1: 105, x2: 300, y2: 130, layer: 'F.Cu', width: 1 },
  { x1: 100, y1: 120, x2: 140, y2: 120, layer: 'B.Cu', width: 2 },
];

const SAMPLE_VIAS = [
  { x: 100, y: 120, r: 4 },
  { x: 190, y: 140, r: 4 },
];

export function Editor() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const canvasRef = useRef<SVGSVGElement>(null);

  const { editorMode, setEditorMode, toolMode, setToolMode, showChat, toggleChat, showProperties, zoom, setZoom } = useUIStore();
  const [layerVisibility, setLayerVisibility] = useState<Record<string, boolean>>(
    Object.fromEntries(LAYERS.map((l) => [l.id, l.visible]))
  );
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [drcResults, setDrcResults] = useState<{ passed: boolean; count: number } | null>(null);

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const svg = canvasRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / zoom).toFixed(1);
    const y = ((e.clientY - rect.top) / zoom).toFixed(1);
    setMousePos({ x: parseFloat(x), y: parseFloat(y) });
  }, [zoom]);

  const toggleLayer = (layerId: string) => {
    setLayerVisibility((prev) => ({ ...prev, [layerId]: !prev[layerId] }));
  };

  const runQuickDRC = () => {
    // Simulate DRC
    setTimeout(() => {
      setDrcResults({ passed: true, count: 0 });
      setTimeout(() => setDrcResults(null), 3000);
    }, 500);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      const tool = TOOLS.find((t) => t.key === e.key.toLowerCase());
      if (tool) setToolMode(tool.id as typeof toolMode);
      if (e.key === '+' || e.key === '=') setZoom(Math.min(zoom * 1.2, 5));
      if (e.key === '-') setZoom(Math.max(zoom / 1.2, 0.2));
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [zoom, setToolMode, setZoom]);

  return (
    <div className="app-layout">
      {/* ── Top Nav ────────────────────────────────────────── */}
      <nav className="topnav">
        <div className="topnav__logo" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <div className="topnav__logo-icon">⚡</div>
          PCB Builder
        </div>

        <div className="topnav__tabs">
          {(['schematic', 'pcb', '3d'] as const).map((mode) => (
            <button
              key={mode}
              className={`topnav__tab ${editorMode === mode ? 'topnav__tab--active' : ''}`}
              onClick={() => setEditorMode(mode)}
              id={`tab-${mode}`}
            >
              {mode === 'schematic' ? '📋 Schematic' : mode === 'pcb' ? '🔧 PCB Layout' : '📦 3D View'}
            </button>
          ))}
        </div>

        <div className="topnav__actions">
          {drcResults && (
            <span className={`badge ${drcResults.passed ? 'badge--success' : 'badge--danger'}`}>
              {drcResults.passed ? '✓ DRC Passed' : `✗ ${drcResults.count} violations`}
            </span>
          )}
          <button className="btn btn--secondary btn--sm" onClick={runQuickDRC} id="btn-drc">▶ DRC</button>
          <button className="btn btn--secondary btn--sm" id="btn-gerber">📦 Export</button>
          <button className="btn btn--primary btn--sm" id="btn-fab-quote">💰 Get Quote</button>
          <button className={`btn btn--ghost btn--icon`} onClick={toggleChat} id="btn-toggle-chat" title="AI Chat">
            🤖
          </button>
        </div>
      </nav>

      {/* ── Main Area ─────────────────────────────────────── */}
      <div className="app-main">
        {/* ── Sidebar: Layers & Components ──────────────── */}
        <div className="sidebar">
          <div className="sidebar__header">Explorer</div>
          <div className="sidebar__content">
            {/* Layers */}
            <div className="sidebar__section">
              <div className="sidebar__section-title">Layers</div>
              {LAYERS.map((layer) => (
                <div
                  key={layer.id}
                  className="sidebar__item"
                  onClick={() => toggleLayer(layer.id)}
                  style={{ opacity: layerVisibility[layer.id] ? 1 : 0.4 }}
                >
                  <span style={{
                    width: 12, height: 12, borderRadius: 3,
                    background: layer.color, display: 'inline-block', flexShrink: 0,
                  }} />
                  <span style={{ flex: 1 }}>{layer.name}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                    {layerVisibility[layer.id] ? '👁' : ''}
                  </span>
                </div>
              ))}
            </div>

            {/* Components */}
            <div className="sidebar__section">
              <div className="sidebar__section-title">Components ({SAMPLE_COMPONENTS.length})</div>
              {SAMPLE_COMPONENTS.map((comp) => (
                <div
                  key={comp.id}
                  className={`sidebar__item ${selectedComponent === comp.id ? 'sidebar__item--active' : ''}`}
                  onClick={() => setSelectedComponent(comp.id)}
                >
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, minWidth: 36 }}>{comp.name}</span>
                  <span style={{ flex: 1, fontSize: 12, color: 'var(--text-muted)' }}>{comp.value}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{comp.footprint}</span>
                </div>
              ))}
            </div>

            {/* Nets */}
            <div className="sidebar__section">
              <div className="sidebar__section-title">Nets (6)</div>
              {['VCC', 'GND', '3V3', 'SDA', 'SCL', 'TX'].map((net) => (
                <div key={net} className="sidebar__item">
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{net}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Canvas ────────────────────────────────────── */}
        <div className="canvas-area">
          {/* Toolbar */}
          <div className="canvas-area__toolbar">
            {TOOLS.map((tool, i) => (
              <button
                key={tool.id}
                className={`tool-btn ${toolMode === tool.id ? 'tool-btn--active' : ''}`}
                onClick={() => setToolMode(tool.id as typeof toolMode)}
                title={tool.label}
                id={`tool-${tool.id}`}
              >
                {tool.icon}
              </button>
            ))}
            <div className="tool-btn__divider" />
            <button className="tool-btn" onClick={() => setZoom(Math.min(zoom * 1.25, 5))} title="Zoom In">+</button>
            <button className="tool-btn" onClick={() => setZoom(Math.max(zoom / 1.25, 0.2))} title="Zoom Out">−</button>
            <button className="tool-btn" onClick={() => setZoom(1)} title="Reset Zoom">⊡</button>
          </div>

          {/* SVG Canvas */}
          <svg
            ref={canvasRef}
            width="100%"
            height="100%"
            onMouseMove={handleMouseMove}
            style={{ cursor: toolMode === 'select' ? 'default' : toolMode === 'route' ? 'crosshair' : 'cell' }}
          >
            <g transform={`scale(${zoom})`}>
              {/* Board outline */}
              <rect x="30" y="60" width="320" height="180" rx="4"
                fill="var(--pcb-board)" fillOpacity="0.15"
                stroke="var(--pcb-board)" strokeWidth="1.5" strokeDasharray="4 2" />

              {/* Grid */}
              <defs>
                <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
                  <circle cx="0" cy="0" r="0.5" fill="rgba(148,163,184,0.15)" />
                </pattern>
              </defs>
              <rect x="30" y="60" width="320" height="180" fill="url(#grid)" />

              {/* Tracks - Back Copper */}
              {layerVisibility['B.Cu'] && SAMPLE_TRACKS.filter((t) => t.layer === 'B.Cu').map((t, i) => (
                <line key={`bt-${i}`} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2}
                  stroke="#2744e8" strokeWidth={t.width} strokeLinecap="round" opacity={0.7} />
              ))}

              {/* Tracks - Front Copper */}
              {layerVisibility['F.Cu'] && SAMPLE_TRACKS.filter((t) => t.layer === 'F.Cu').map((t, i) => (
                <line key={`ft-${i}`} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2}
                  stroke="var(--pcb-copper)" strokeWidth={t.width} strokeLinecap="round" opacity={0.85} />
              ))}

              {/* Vias */}
              {SAMPLE_VIAS.map((v, i) => (
                <g key={`via-${i}`}>
                  <circle cx={v.x} cy={v.y} r={v.r + 1} fill="none" stroke="var(--pcb-copper)" strokeWidth="1" />
                  <circle cx={v.x} cy={v.y} r={v.r} fill="var(--bg-primary)" />
                  <circle cx={v.x} cy={v.y} r={v.r - 1.5} fill="var(--pcb-copper)" opacity="0.6" />
                </g>
              ))}

              {/* Components */}
              {layerVisibility['F.Cu'] && SAMPLE_COMPONENTS.map((comp) => (
                <g key={comp.id}
                  transform={`translate(${comp.x - comp.w / 2}, ${comp.y - comp.h / 2}) rotate(${comp.rotation}, ${comp.w / 2}, ${comp.h / 2})`}
                  onClick={() => setSelectedComponent(comp.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <rect width={comp.w} height={comp.h} rx="2"
                    fill={selectedComponent === comp.id ? 'rgba(99,102,241,0.25)' : 'rgba(100,100,100,0.2)'}
                    stroke={selectedComponent === comp.id ? 'var(--accent-primary)' : 'rgba(148,163,184,0.3)'}
                    strokeWidth={selectedComponent === comp.id ? 1.5 : 0.8} />
                  {/* Pads */}
                  <rect x="0" y={comp.h / 2 - 2} width="3" height="4" fill="var(--pcb-copper)" rx="0.5" />
                  <rect x={comp.w - 3} y={comp.h / 2 - 2} width="3" height="4" fill="var(--pcb-copper)" rx="0.5" />
                  {/* Silkscreen ref */}
                  {layerVisibility['F.SilkS'] && (
                    <text x={comp.w / 2} y={comp.h / 2 + 3} textAnchor="middle"
                      fill="var(--pcb-silkscreen)" fontSize="7" fontFamily="var(--font-mono)" opacity="0.8">
                      {comp.name}
                    </text>
                  )}
                </g>
              ))}
            </g>
          </svg>
        </div>

        {/* ── Properties Panel ─────────────────────────── */}
        {showProperties && (
          <div className="properties">
            <div className="properties__header">
              <span>{selectedComponent ? 'Component Properties' : 'Board Properties'}</span>
            </div>
            <div className="properties__content">
              {selectedComponent ? (
                <>
                  {(() => {
                    const comp = SAMPLE_COMPONENTS.find((c) => c.id === selectedComponent);
                    if (!comp) return null;
                    return (
                      <>
                        <div className="property-group">
                          <div className="property-group__title">Identity</div>
                          <div className="property-row"><span className="property-row__label">Reference</span><span className="property-row__value">{comp.name}</span></div>
                          <div className="property-row"><span className="property-row__label">Value</span><span className="property-row__value">{comp.value}</span></div>
                          <div className="property-row"><span className="property-row__label">Footprint</span><span className="property-row__value">{comp.footprint}</span></div>
                        </div>
                        <div className="property-group">
                          <div className="property-group__title">Position</div>
                          <div className="property-row"><span className="property-row__label">X</span><span className="property-row__value">{comp.x} mm</span></div>
                          <div className="property-row"><span className="property-row__label">Y</span><span className="property-row__value">{comp.y} mm</span></div>
                          <div className="property-row"><span className="property-row__label">Rotation</span><span className="property-row__value">{comp.rotation}°</span></div>
                          <div className="property-row"><span className="property-row__label">Layer</span><span className="property-row__value">{comp.layer}</span></div>
                        </div>
                      </>
                    );
                  })()}
                </>
              ) : (
                <>
                  <div className="property-group">
                    <div className="property-group__title">Board Config</div>
                    <div className="property-row"><span className="property-row__label">Width</span><span className="property-row__value">100 mm</span></div>
                    <div className="property-row"><span className="property-row__label">Height</span><span className="property-row__value">80 mm</span></div>
                    <div className="property-row"><span className="property-row__label">Layers</span><span className="property-row__value">2</span></div>
                    <div className="property-row"><span className="property-row__label">Thickness</span><span className="property-row__value">1.6 mm</span></div>
                    <div className="property-row"><span className="property-row__label">Material</span><span className="property-row__value">FR4</span></div>
                    <div className="property-row"><span className="property-row__label">Finish</span><span className="property-row__value">HASL</span></div>
                  </div>
                  <div className="property-group">
                    <div className="property-group__title">Design Rules</div>
                    <div className="property-row"><span className="property-row__label">Min Trace</span><span className="property-row__value">0.15 mm</span></div>
                    <div className="property-row"><span className="property-row__label">Min Space</span><span className="property-row__value">0.15 mm</span></div>
                    <div className="property-row"><span className="property-row__label">Min Via</span><span className="property-row__value">0.3 mm</span></div>
                    <div className="property-row"><span className="property-row__label">Copper</span><span className="property-row__value">1 oz</span></div>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* ── AI Chat ──────────────────────────────────── */}
        {showChat && <ChatInterface designId={projectId || 'demo'} />}
      </div>

      {/* ── Status Bar ────────────────────────────────── */}
      <div className="statusbar">
        <div className="statusbar__item"><span className="statusbar__dot" /> Connected</div>
        <div className="statusbar__item">📐 {mousePos.x}, {mousePos.y} mm</div>
        <div className="statusbar__item">Grid: 0.5mm</div>
        <div className="statusbar__item">Snap: ON</div>
        <div className="statusbar__item">🔍 {(zoom * 100).toFixed(0)}%</div>
        <div className="statusbar__item" style={{ marginLeft: 'auto' }}>
          <kbd>V</kbd> Select &nbsp; <kbd>X</kbd> Route &nbsp; <kbd>P</kbd> Place
        </div>
      </div>
    </div>
  );
}
