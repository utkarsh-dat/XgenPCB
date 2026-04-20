/**
 * PCB Builder - Editor Page
 * Professional PCB editor with 2D/3D rendering using tscircuit
 */

import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { ChatInterface } from '../components/ai/ChatInterface';
import {
  PCBCanvas,
  ThreeDViewer,
  ComponentLibrary,
  LayerPanel,
  PropertyPanel,
  getComponentProperties,
} from '../components/editor';

// View modes
type ViewMode = '2d' | '3d' | 'split';

// Tool modes
type ToolMode = 'select' | 'place' | 'route' | 'measure' | 'zone' | 'draw';

const TOOLS = [
  { id: 'select', icon: '⊹', label: 'Select', shortcut: 'V' },
  { id: 'place', icon: '◻', label: 'Place', shortcut: 'P' },
  { id: 'route', icon: '╱', label: 'Route', shortcut: 'X' },
  { id: 'measure', icon: '📏', label: 'Measure', shortcut: 'M' },
  { id: 'zone', icon: '▨', label: 'Copper Zone', shortcut: 'Z' },
  { id: 'draw', icon: '✎', label: 'Draw', shortcut: 'D' },
];

const DESIGN = {
  id: 'demo',
  width: 50,
  height: 50,
  layers: 4,
  components: [
    { id: 'U1', name: 'ESP32', type: 'IC', footprint: 'QFN-48', x: 0, y: 0, rotation: 0, value: 'ESP32-WROOM' },
    { id: 'C1', name: 'C1', type: 'capacitor', footprint: '0603', x: -15, y: 10, rotation: 0, value: '10uF' },
    { id: 'C2', name: 'C2', type: 'capacitor', footprint: '0603', x: -10, y: -10, rotation: 90, value: '0.1uF' },
    { id: 'R1', name: 'R1', type: 'resistor', footprint: '0603', x: 10, y: 10, rotation: 0, value: '10K' },
    { id: 'J1', name: 'J1', type: 'connector', footprint: 'USB-C', x: -20, y: 0, rotation: 0, value: 'USB-C' },
    { id: 'LED1', name: 'LED1', type: 'LED', footprint: '0603', x: 15, y: -5, rotation: 0, value: 'Green' },
  ],
  nets: [],
};

export function Editor() {
  const navigate = useNavigate();
  const { projectId } = useParams();

  // UI State
  const [viewMode, setViewMode] = useState<ViewMode>('2d');
  const [toolMode, setToolMode] = useState<ToolMode>('select');
  const [showChat, setShowChat] = useState(true);
  const [showLayers, setShowLayers] = useState(true);
  const [showComponents, setShowComponents] = useState(true);
  const [showProperties, setShowProperties] = useState(true);
  const [activeLayer, setActiveLayer] = useState('F.Cu');
  const [selectedComponentId] = useState<string | undefined>();

  // Get selected component properties
  const selectedItem = selectedComponentId
    ? {
        id: selectedComponentId,
        type: 'component' as const,
        name: selectedComponentId,
        properties: getComponentProperties(selectedComponentId, selectedComponentId, '0805'),
      }
    : undefined;

  return (
    <div className="editor-layout">
      {/* ── Top Toolbar ────────────────────────────────────── */}
      <header className="editor-toolbar">
        <div className="toolbar-left">
          <button className="btn btn--ghost" onClick={() => navigate('/')}>
            ← Back
          </button>
          <h1 className="editor-title">
            {projectId === 'new' ? 'New Project' : `Project ${projectId}`}
          </h1>
        </div>

        <div className="toolbar-center">
          {/* View Mode Toggle */}
          <div className="view-toggle">
            <button
              className={`view-toggle-btn ${viewMode === '2d' ? 'active' : ''}`}
              onClick={() => setViewMode('2d')}
            >
              2D
            </button>
            <button
              className={`view-toggle-btn ${viewMode === '3d' ? 'active' : ''}`}
              onClick={() => setViewMode('3d')}
            >
              3D
            </button>
            <button
              className={`view-toggle-btn ${viewMode === 'split' ? 'active' : ''}`}
              onClick={() => setViewMode('split')}
            >
              Split
            </button>
          </div>

          {/* Tool Buttons */}
          <div className="tool-buttons">
            {TOOLS.map(tool => (
              <button
                key={tool.id}
                className={`tool-btn ${toolMode === tool.id ? 'active' : ''}`}
                onClick={() => setToolMode(tool.id as ToolMode)}
                title={`${tool.label} (${tool.shortcut})`}
              >
                {tool.icon}
              </button>
            ))}
          </div>
        </div>

        <div className="toolbar-right">
          <button
            className={`btn btn--ghost ${showComponents ? 'active' : ''}`}
            onClick={() => setShowComponents(!showComponents)}
            title="Components"
          >
            ☰
          </button>
          <button
            className={`btn btn--ghost ${showLayers ? 'active' : ''}`}
            onClick={() => setShowLayers(!showLayers)}
            title="Layers"
          >
            ≋
          </button>
          <button
            className={`btn btn--ghost ${showProperties ? 'active' : ''}`}
            onClick={() => setShowProperties(!showProperties)}
            title="Properties"
          >
            ⚙
          </button>
          <button
            className={`btn btn--ghost ${showChat ? 'active' : ''}`}
            onClick={() => setShowChat(!showChat)}
            title="AI Chat"
          >
            🤖
          </button>
          <button className="btn btn--primary btn--sm">
            Export
          </button>
        </div>
      </header>

      {/* ── Main Editor Area ────────────────────────────────────── */}
      <div className="editor-main">
        {/* Left Sidebar - Components */}
        {showComponents && (
          <aside className="sidebar sidebar--components">
            <div className="sidebar-header">
              <h3>Components</h3>
            </div>
            <ComponentLibrary
              onComponentSelect={(comp) => {
                console.log('Selected:', comp);
              }}
            />
          </aside>
        )}

        {/* Center - Canvas */}
        <main className="editor-canvas">
          {viewMode === '2d' && (
            <PCBCanvas
              design={DESIGN}
            />
          )}
          {viewMode === '3d' && (
            <ThreeDViewer />
          )}
          {viewMode === 'split' && (
            <div className="split-view">
              <PCBCanvas
                design={DESIGN}
              />
              <ThreeDViewer />
            </div>
          )}
        </main>

        {/* Right Sidebar */}
        <aside className="sidebar sidebar--right">
          {/* Layers Panel */}
          {showLayers && (
            <div className="sidebar-section">
              <LayerPanel
                activeLayer={activeLayer}
                onActiveLayerChange={setActiveLayer}
              />
            </div>
          )}

          {/* Properties Panel */}
          {showProperties && (
            <div className="sidebar-section">
              <PropertyPanel selectedItem={selectedItem} />
            </div>
          )}
        </aside>

        {/* AI Chat Panel */}
        {showChat && (
          <div className="chat-panel">
            <ChatInterface designId={projectId || 'new'} />
          </div>
        )}
      </div>
    </div>
  );
}

export default Editor;