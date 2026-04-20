/**
 * PCB Builder - Component Library Panel
 * Live search from JLCPCB/LCSC with fallback
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '../../lib/api/client';

export interface ComponentDefinition {
  id: string;
  mpn: string;
  manufacturer: string;
  description: string;
  category: string;
  package: string;
  price_1?: number;
  price_100?: number;
  price_1000?: number;
  stock: number;
  library_type: string;
  footprint?: string;
  source: string;
}

const CATEGORIES = [
  { id: 'ic', name: 'ICs' },
  { id: 'resistor', name: 'Resistors' },
  { id: 'capacitor', name: 'Capacitors' },
  { id: 'inductor', name: 'Inductors' },
  { id: 'diode', name: 'Diodes' },
  { id: 'transistor', name: 'Transistors' },
  { id: 'connector', name: 'Connectors' },
  { id: 'crystal', name: 'Crystals' },
  { id: 'led', name: 'LEDs' },
];

interface ComponentLibraryProps {
  onDragStart?: (component: ComponentDefinition) => void;
  onComponentSelect?: (component: ComponentDefinition) => void;
}

// Debounce helper
function debounce<T extends (...args: Parameters<T>) => void>(fn: T, delay: number) {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

export function ComponentLibrary({
  onDragStart,
  onComponentSelect,
}: ComponentLibraryProps) {
  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [components, setComponents] = useState<ComponentDefinition[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<string>('fallback');

  // Search handler with debounce
  const handleSearch = useCallback(
    debounce(async (query: string) => {
      if (!query.trim()) {
        setComponents([]);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await (api as any).request('/components/search', {
          method: 'POST',
          body: JSON.stringify({
            q: query,
            limit: 20,
            in_stock_only: false,
          }),
        }) as {
          items: ComponentDefinition[];
          source: string;
          total: number;
        };

        setComponents(response.items || []);
        setSource(response.source || 'fallback');
      } catch (err) {
        console.error('Component search failed:', err);
        setError('Search unavailable');
        setComponents([]);
      } finally {
        setIsLoading(false);
      }
    }, 300),
    []
  );

  // Trigger search on query change
  useEffect(() => {
    handleSearch(searchQuery);
  }, [searchQuery, handleSearch]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const handleDragStart = (e: React.DragEvent, component: ComponentDefinition) => {
    e.dataTransfer.setData('component', JSON.stringify(component));
    onDragStart?.(component);
  };

  const formatPrice = (price?: number) => {
    if (price === undefined || price === 0) return '-';
    return `$${price.toFixed(4)}`;
  };

  const formatStock = (stock: number) => {
    if (stock === 0) return 'Out of stock';
    if (stock < 100) return `${stock} left`;
    if (stock < 1000) return `${stock} in stock`;
    return `${(stock / 1000).toFixed(1)}K stock`;
  };

  const getStockClass = (stock: number) => {
    if (stock === 0) return 'stock--out';
    if (stock < 100) return 'stock--low';
    return 'stock--ok';
  };

  return (
    <div className="component-library">
      {/* Search Input */}
      <div className="search-input-wrapper">
        <input
          type="text"
          className="search-input"
          placeholder="Search components (e.g., ESP32, 0805, 10K)..."
          value={searchQuery}
          onChange={handleInputChange}
        />
        {isLoading && <span className="search-spinner">⏳</span>}
      </div>

      {/* Source indicator */}
      <div className="source-indicator">
        <span className={`source-badge source-badge--${source}`}>
          {source === 'jlcpcb' && '📦 JLCPCB'}
          {source === 'lcsc' && '📦 LCSC'}
          {source === 'fallback' && '📦 Local'}
        </span>
      </div>

      {/* Category Tabs */}
      <div className="category-tabs">
        <button className="category-tab active">All</button>
        {CATEGORIES.map(cat => (
          <button key={cat.id} className="category-tab">{cat.name}</button>
        ))}
      </div>

      {/* Results */}
      <div className="components-grid">
        {error && (
          <div className="error-message">{error}</div>
        )}

        {!isLoading && components.length === 0 && searchQuery && (
          <div className="empty-results">
            No components found. Try a different search.
          </div>
        )}

        {components.map(comp => (
          <div
            key={comp.id}
            className="component-item"
            draggable
            onDragStart={(e) => handleDragStart(e, comp)}
            onClick={() => onComponentSelect?.(comp)}
            title={comp.description}
          >
            {/* Stock badge */}
            <div className={`stock-badge ${getStockClass(comp.stock)}`}>
              {formatStock(comp.stock)}
            </div>

            <div className="component-icon">
              {comp.category.includes('IC') && '🔲'}
              {comp.category.includes('resist') && '◧'}
              {comp.category.includes('capac') && '◈'}
              {comp.category.includes('connector') && '◯'}
              {comp.category.includes('crystal') && '◇'}
              {comp.category.includes('led') && '◉'}
              {!comp.category && '◻'}
            </div>

            <div className="component-info">
              <div className="component-mpn">{comp.mpn}</div>
              <div className="component-pkg">{comp.package}</div>
              <div className="component-price">
                {formatPrice(comp.price_1)} / {formatPrice(comp.price_100)}
              </div>
            </div>

            {/* Library type badge */}
            {comp.library_type && (
              <div className={`library-badge library-badge--${comp.library_type}`}>
                {comp.library_type}
              </div>
            )}
          </div>
        ))}

        {!isLoading && components.length === 0 && !searchQuery && (
          <div className="search-placeholder">
            <p>🔍 Search for components</p>
            <p className="hint">Try: ESP32, STM32, 0805, 10K, USB-C</p>
          </div>
        )}
      </div>

      {/* Keyboard shortcuts hint */}
      <div className="keyboard-hint">
        Press <kbd>/</kbd> to search
      </div>
    </div>
  );
}

// Styles would be in editor.css - adding minimal inline styles for structure
export default ComponentLibrary;