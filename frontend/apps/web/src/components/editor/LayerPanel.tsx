/**
 * PCB Builder - Layer Panel
 * Controls for PCB layers visibility and settings
 */

import { useState } from 'react';

export interface Layer {
  id: string;
  name: string;
  type: 'copper' | 'silk' | 'mask' | 'paste' | 'assy' | 'edge';
  color?: string;
  visible: boolean;
  locked: boolean;
}

const DEFAULT_LAYERS: Layer[] = [
  // Copper layers
  { id: 'F.Cu', name: 'Front Copper', type: 'copper', color: '#e8222e', visible: true, locked: false },
  { id: 'B.Cu', name: 'Back Copper', type: 'copper', color: '#2744e8', visible: true, locked: false },
  { id: 'In1.Cu', name: 'Inner Copper 1', type: 'copper', color: '#06b6d4', visible: false, locked: false },
  { id: 'In2.Cu', name: 'Inner Copper 2', type: 'copper', color: '#8b5cf6', visible: false, locked: false },

  // Silkscreen
  { id: 'F.SilkS', name: 'Front Silkscreen', type: 'silk', color: '#f0f000', visible: true, locked: false },
  { id: 'B.SilkS', name: 'Back Silkscreen', type: 'silk', color: '#8800ee', visible: true, locked: false },

  // Solder mask
  { id: 'F.Mask', name: 'Front Solder Mask', type: 'mask', color: '#006633', visible: false, locked: false },
  { id: 'B.Mask', name: 'Back Solder Mask', type: 'mask', color: '#840084', visible: false, locked: false },

  // Paste
  { id: 'F.Paste', name: 'Front Paste', type: 'paste', color: '#c0c0c0', visible: false, locked: false },
  { id: 'B.Paste', name: 'Back Paste', type: 'paste', color: '#808080', visible: false, locked: false },

  // Assembly
  { id: 'F.Adhesive', name: 'Front Adhesive', type: 'assy', color: '#ff6600', visible: false, locked: false },
  { id: 'B.Adhesive', name: 'Back Adhesive', type: 'assy', color: '#ff9933', visible: false, locked: false },
  { id: 'F.CrtYd', name: 'Front Courtyard', type: 'assy', color: '#00ff00', visible: false, locked: false },
  { id: 'B.CrtYd', name: 'Back Courtyard', type: 'assy', color: '#00cc00', visible: false, locked: false },

  // Edge
  { id: 'Edge.Cuts', name: 'Board Edge', type: 'edge', color: '#eeee00', visible: true, locked: true },
  { id: 'Margin', name: 'Margin', type: 'edge', color: '#ff0000', visible: false, locked: false },
  { id: 'Drafts', name: 'Drafts', type: 'edge', color: '#0000ff', visible: false, locked: false },
];

interface LayerPanelProps {
  layers?: Layer[];
  onLayerChange?: (layers: Layer[]) => void;
  activeLayer?: string;
  onActiveLayerChange?: (layerId: string) => void;
}

export function LayerPanel({
  layers = DEFAULT_LAYERS,
  onLayerChange,
  activeLayer = 'F.Cu',
  onActiveLayerChange,
}: LayerPanelProps) {
  const [localLayers, setLocalLayers] = useState(layers);

  const toggleVisibility = (layerId: string) => {
    const updated = localLayers.map(l =>
      l.id === layerId ? { ...l, visible: !l.visible } : l
    );
    setLocalLayers(updated);
    onLayerChange?.(updated);
  };

  const toggleLock = (layerId: string) => {
    const updated = localLayers.map(l =>
      l.id === layerId ? { ...l, locked: !l.locked } : l
    );
    setLocalLayers(updated);
    onLayerChange?.(updated);
  };

  const copperLayers = localLayers.filter(l => l.type === 'copper');
  const otherLayers = localLayers.filter(l => l.type !== 'copper');

  return (
    <div className="layer-panel">
      {/* Active Layer Selector */}
      <div className="active-layer-selector">
        <label>Active Layer</label>
        <select
          value={activeLayer}
          onChange={(e) => onActiveLayerChange?.(e.target.value)}
          className="layer-select"
        >
          {localLayers.map(layer => (
            <option key={layer.id} value={layer.id}>
              {layer.name}
            </option>
          ))}
        </select>
      </div>

      {/* Copper Layers */}
      <div className="layer-group">
        <div className="layer-group-header">
          <span>Copper Layers</span>
          <span className="layer-count">{copperLayers.filter(l => l.visible).length}/{copperLayers.length}</span>
        </div>
        {copperLayers.map(layer => (
          <LayerRow
            key={layer.id}
            layer={layer}
            isActive={layer.id === activeLayer}
            onToggleVisibility={() => toggleVisibility(layer.id)}
            onToggleLock={() => toggleLock(layer.id)}
            onSelect={() => onActiveLayerChange?.(layer.id)}
          />
        ))}
      </div>

      {/* Other Layers */}
      <div className="layer-group">
        <div className="layer-group-header">
          <span>Other Layers</span>
          <span className="layer-count">{otherLayers.filter(l => l.visible).length}/{otherLayers.length}</span>
        </div>
        {otherLayers.map(layer => (
          <LayerRow
            key={layer.id}
            layer={layer}
            isActive={layer.id === activeLayer}
            onToggleVisibility={() => toggleVisibility(layer.id)}
            onToggleLock={() => toggleLock(layer.id)}
            onSelect={() => onActiveLayerChange?.(layer.id)}
          />
        ))}
      </div>
    </div>
  );
}

interface LayerRowProps {
  layer: Layer;
  isActive: boolean;
  onToggleVisibility: () => void;
  onToggleLock: () => void;
  onSelect: () => void;
}

function LayerRow({
  layer,
  isActive,
  onToggleVisibility,
  onToggleLock,
  onSelect,
}: LayerRowProps) {
  return (
    <div
      className={`layer-row ${isActive ? 'active' : ''} ${layer.locked ? 'locked' : ''}`}
      onClick={onSelect}
    >
      {/* Visibility toggle */}
      <button
        className={`layer-toggle ${layer.visible ? 'visible' : ''}`}
        onClick={(e) => {
          e.stopPropagation();
          onToggleVisibility();
        }}
        title={layer.visible ? 'Hide layer' : 'Show layer'}
      >
        {layer.visible ? '👁' : '○'}
      </button>

      {/* Color indicator */}
      <div
        className="layer-color"
        style={{ backgroundColor: layer.color }}
      />

      {/* Layer name */}
      <span className="layer-name">{layer.name}</span>

      {/* Lock toggle */}
      <button
        className={`layer-lock ${layer.locked ? 'locked' : ''}`}
        onClick={(e) => {
          e.stopPropagation();
          onToggleLock();
        }}
        title={layer.locked ? 'Unlock layer' : 'Lock layer'}
      >
        {layer.locked ? '🔒' : '🔓'}
      </button>
    </div>
  );
}

export { DEFAULT_LAYERS };
export default LayerPanel;