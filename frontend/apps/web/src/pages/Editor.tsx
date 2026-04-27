/**
 * PCB Builder - Editor Page
 * Professional PCB editor with 2D/3D rendering
 */

import { useState, useEffect } from 'react';
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
import { apiClient } from '../lib/api/client';

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

interface ComponentData {
  id: string;
  name: string;
  footprint: string;
  x: number;
  y: number;
  rotation: number;
  layer?: string;
}

interface PCBDesign {
  id: string;
  width_mm: number;
  height_mm: number;
  layers: number;
  components?: ComponentData[];
}

export function Editor() {
  const navigate = useNavigate();
  const { projectId, designId } = useParams();

  // UI State
  const [viewMode, setViewMode] = useState<ViewMode>('2d');
  const [toolMode, setToolMode] = useState<ToolMode>('select');
  const [showChat, setShowChat] = useState(true);
  const [showLayers, setShowLayers] = useState(true);
  const [showComponents, setShowComponents] = useState(true);
  const [showProperties, setShowProperties] = useState(true);
  const [activeLayer, setActiveLayer] = useState('F.Cu');
  const [selectedComponentId] = useState<string | undefined>();
  
  // Design data from API
  const [design, setDesign] = useState<PCBDesign | null>(null);
  const [pcbLayout, setPcbLayout] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Load design on mount
  useEffect(() => {
    if (designId) {
      loadDesign(designId);
    }
  }, [designId]);

  const loadDesign = async (id: string) => {
    setLoading(true);
    try {
      const res = await apiClient.get(`/api/v1/designs/${id}`);
      if (res.data) {
        setDesign({
          id: res.data.id,
          width_mm: res.data.board_config?.width_mm || 100,
          height_mm: res.data.board_config?.height_mm || 80,
          layers: res.data.board_config?.layers || 2,
        });
        setPcbLayout(res.data.pcb_layout);
      }
    } catch (err) {
      console.error('Failed to load design:', err);
    } finally {
      setLoading(false);
    }
  };

  // Get selected component properties
  const selectedItem = selectedComponentId
    ? {
        id: selectedComponentId,
        type: 'component' as const,
        name: selectedComponentId,
        properties: getComponentProperties(selectedComponentId, selectedComponentId, '0805'),
      }
    : undefined;

  // Build data for ThreeDViewer
  const viewerData = {
    board_config: design ? {
      width_mm: design.width_mm,
      height_mm: design.height_mm,
      layers: design.layers,
    } : undefined,
    placed_components: pcbLayout?.placed_components || [],
    tracks: pcbLayout?.tracks || [],
    vias: pcbLayout?.vias || [],
  };

  // Demo design when no design loaded
  const demoDesign: PCBDesign = {
    id: 'demo',
    width_mm: 50,
    height_mm: 50,
    layers: 4,
    components: [
      { id: 'U1', name: 'ESP32', footprint: 'QFN-48', x: 0, y: 0, rotation: 0 },
      { id: 'C1', name: 'C1', footprint: '0603', x: -15, y: 10, rotation: 0 },
      { id: 'C2', name: 'C2', footprint: '0603', x: -10, y: -10, rotation: 90 },
      { id: 'R1', name: 'R1', footprint: '0603', x: 10, y: 10, rotation: 0 },
      { id: 'J1', name: 'J1', footprint: 'USB-C', x: -20, y: 0, rotation: 0 },
      { id: 'LED1', name: 'LED1', footprint: '0603', x: 15, y: -5, rotation: 0 },
    ],
  };

  const displayDesign = design || demoDesign;

  return (
    <div className="editor-layout">
      {/* ── Top Toolbar ────────────────────────────────────── */}
      <header className="editor-toolbar">
        <div className="toolbar-left">
          <button className="btn btn--ghost" onClick={() => navigate('/')}>
            ← Back
          </button>
          <h1 className="editor-title">
            {loading ? 'Loading...' : 
             designId === 'new' ? 'New Project' : 
             design ? `PCB ${design.width_mm}×${design.height_mm}mm` : 
             `Project ${projectId}`}
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
              design={displayDesign}
            />
          )}
          {viewMode === '3d' && (
            <ThreeDViewer data={viewerData} />
          )}
          {viewMode === 'split' && (
            <div className="split-view">
              <PCBCanvas
                design={displayDesign}
              />
              <ThreeDViewer data={viewerData} />
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
            <ChatInterface designId={designId || 'new'} />
          </div>
        )}
      </div>
    </div>
  );
}

export default Editor;