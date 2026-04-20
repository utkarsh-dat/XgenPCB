/**
 * PCB Builder - Properties Panel
 * Shows properties of selected component/trace/net
 */

import { useState, useEffect } from 'react';

export interface Property {
  key: string;
  label: string;
  value: string | number;
  type: 'string' | 'number' | 'select' | 'boolean';
  options?: string[];
  unit?: string;
  editable?: boolean;
}

interface PropertyPanelProps {
  selectedItem?: {
    id: string;
    type: 'component' | 'trace' | 'net' | 'via' | 'zone';
    name: string;
    properties: Property[];
  };
  onPropertyChange?: (key: string, value: string | number) => void;
}

export function PropertyPanel({
  selectedItem,
  onPropertyChange,
}: PropertyPanelProps) {
  const [properties, setProperties] = useState<Property[]>([]);

  useEffect(() => {
    if (selectedItem) {
      setProperties(selectedItem.properties);
    } else {
      setProperties([]);
    }
  }, [selectedItem]);

  const handleChange = (key: string, value: string | number) => {
    const updated = properties.map(p =>
      p.key === key ? { ...p, value } : p
    );
    setProperties(updated);
    onPropertyChange?.(key, value);
  };

  if (!selectedItem) {
    return (
      <div className="property-panel">
        <div className="panel-empty">
          <p>Select an element to view its properties</p>
        </div>
      </div>
    );
  }

  return (
    <div className="property-panel">
      {/* Header */}
      <div className="property-header">
        <span className="property-type">{selectedItem.type}</span>
        <span className="property-name">{selectedItem.name}</span>
      </div>

      {/* Properties */}
      <div className="property-list">
        {properties.map(prop => (
          <div key={prop.key} className="property-row">
            <label className="property-label">{prop.label}</label>
            
            {prop.type === 'select' && prop.options ? (
              <select
                value={prop.value as string}
                onChange={(e) => handleChange(prop.key, e.target.value)}
                className="property-input"
                disabled={!prop.editable}
              >
                {prop.options.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            ) : prop.type === 'number' ? (
              <div className="property-number">
                <input
                  type="number"
                  value={prop.value as number}
                  onChange={(e) => handleChange(prop.key, parseFloat(e.target.value))}
                  className="property-input"
                  disabled={!prop.editable}
                />
                {prop.unit && <span className="property-unit">{prop.unit}</span>}
              </div>
            ) : (
              <input
                type="text"
                value={prop.value as string}
                onChange={(e) => handleChange(prop.key, e.target.value)}
                className="property-input"
                disabled={!prop.editable}
              />
            )}
          </div>
        ))}
      </div>

      {properties.length === 0 && (
        <div className="panel-empty">
          <p>No properties available</p>
        </div>
      )}
    </div>
  );
}

// Demo component for component properties
export function getComponentProperties(_id: string, name: string, footprint: string): Property[] {
  return [
    { key: 'name', label: 'Name', value: name, type: 'string', editable: false },
    { key: 'footprint', label: 'Footprint', value: footprint, type: 'string', editable: true, options: ['0603', '0805', 'QFN-48', 'SOT-223'] },
    { key: 'x', label: 'X Position', value: 0, type: 'number', unit: 'mm', editable: true },
    { key: 'y', label: 'Y Position', value: 0, type: 'number', unit: 'mm', editable: true },
    { key: 'rotation', label: 'Rotation', value: 0, type: 'number', unit: '°', editable: true },
    { key: 'layer', label: 'Layer', value: 'F.Cu', type: 'select', options: ['F.Cu', 'B.Cu'], editable: true },
    { key: 'value', label: 'Value', value: '', type: 'string', editable: true },
    { key: 'manufacturer', label: 'Manufacturer', value: '', type: 'string', editable: true },
    { key: 'mpn', label: 'MPN', value: '', type: 'string', editable: true },
  ];
}

// Demo for trace properties  
export function getTraceProperties(_id: string, net: string): Property[] {
  return [
    { key: 'net', label: 'Net', value: net, type: 'string', editable: false },
    { key: 'width', label: 'Width', value: 0.254, type: 'number', unit: 'mm', editable: true },
    { key: 'layer', label: 'Layer', value: 'F.Cu', type: 'select', options: ['F.Cu', 'B.Cu', 'In1.Cu', 'In2.Cu'], editable: true },
    { key: 'net_class', label: 'Net Class', value: 'default', type: 'select', options: ['default', 'power', 'high_speed'], editable: true },
  ];
}

export default PropertyPanel;