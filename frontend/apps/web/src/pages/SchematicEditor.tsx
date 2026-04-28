import { useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft,
  Save,
  Download,
  Share2,
  Settings,
  Layers,
  Grid3X3,
  ZoomIn,
  ZoomOut,
  Undo,
  Redo,
  Trash2,
  Copy,
  Move,
  RotateCw,
  FlipHorizontal,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Search,
  Plus,
  ChevronRight,
  ChevronDown,
  PanelLeft,
  PanelRight,
  Layers as LayersIcon,
  BookOpen,
  Wifi,
  Cpu,
  Component,
  CircuitBoard,
  FileText,
  SaveAll,
  Play,
  RefreshCw,
  Shield,
  Eye,
  EyeOff,
  Lock,
  Unlock,
  MousePointer,
  PenTool,
  Minus,
  Circle,
  Square,
  Type,
  ArrowRight,
  MinusCircle,
  PlusCircle,
  Bookmark,
  Clock,
  MoreHorizontal,
  Layout,
  Box,
  Package,
  FileDown,
  Upload,
  Send,
  MessageSquare,
  History,
  Users,
  Star,
  ThumbsUp,
  MessageCircle,
  Eye as EyeIcon,
  Flag,
  ChevronLeft,
  FolderOpen,
  Filter,
  List,
  Grid,
  PlusSquare,
  File
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const SYMBOLS = [
  { id: 's1', name: 'ESP32-WROOM', type: 'MCU', library: 'Microchip', pins: 38 },
  { id: 's2', name: 'AMS1117-3.3', type: 'Regulator', library: 'Power', pins: 3 },
  { id: 's3', name: 'USB-C', type: 'Connector', library: 'Connectors', pins: 24 },
  { id: 's4', name: 'Capacitor 100nF', type: 'Capacitor', library: 'Passives', pins: 2 },
  { id: 's5', name: 'Resistor 10K', type: 'Resistor', library: 'Passives', pins: 2 },
  { id: 's6', name: 'LED', type: 'LED', library: 'Opto', pins: 2 },
  { id: 's7', name: 'Crystal 16MHz', type: 'Crystal', library: 'Timing', pins: 2 },
  { id: 's8', name: 'NMOS', type: 'Transistor', library: 'Semiconductors', pins: 3 },
];

const ERC_ERRORS = [
  { id: 1, severity: 'error', message: 'Net GND has no connections', component: 'C1', sheet: 1 },
  { id: 2, severity: 'warning', message: 'Pin type mismatch: Input connected to Output', component: 'U1', sheet: 1 },
  { id: 3, severity: 'info', message: 'Unused pin: GPIO0', component: 'ESP32', sheet: 1 },
];

const ERC_WARNINGS = [
  { id: 4, severity: 'warning', message: 'Multiple drivers on net: VCC', components: ['U1', 'U2'], sheet: 1 },
];

const NETS = [
  { id: 'n1', name: 'GND', color: '#000000', connections: 12 },
  { id: 'n2', name: 'VCC', color: '#FF0000', connections: 8 },
  { id: 'n3', name: 'Net-_U1_1', color: '#0066FF', connections: 3 },
  { id: 'n4', name: 'Net-_U1_2', color: '#00FF00', connections: 2 },
  { id: 'n5', name: 'Net-_C1_1', color: '#FF6600', connections: 2 },
];

const SHEETS = [
  { id: 1, name: 'Main', components: 8 },
  { id: 2, name: 'Power', components: 4 },
  { id: 3, name: 'Connectors', components: 3 },
];

export function SchematicEditor() {
  const navigate = useNavigate();
  const { projectId, designId } = useParams();
  const [activeTool, setActiveTool] = useState('select');
  const [showERC, setShowERC] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<typeof SYMBOLS[0] | null>(null);
  const [zoom, setZoom] = useState(100);
  const [gridVisible, setGridVisible] = useState(true);
  const [leftPanel, setLeftPanel] = useState<'symbols' | 'nets' | 'sheets'>('symbols');
  const [rightPanel, setRightPanel] = useState<'properties' | 'erc' | 'chat'>('properties');

  const handleRunERC = () => {
    setShowERC(true);
  };

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      {/* Top Toolbar */}
      <header className="h-12 bg-background border-b border-border flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="h-6 w-px bg-slate-200" />
          <span className="font-medium text-foreground">ESP32 IoT Sensor - Schematic</span>
          <Badge variant="secondary" className="ml-2">Unsaved</Badge>
        </div>

        <div className="flex items-center gap-1">
          {/* Edit Tools */}
          <div className="flex items-center gap-0.5 bg-slate-100 rounded-md p-0.5 mr-2">
            {[
              { id: 'select', icon: MousePointer, label: 'Select' },
              { id: 'place', icon: PlusCircle, label: 'Place' },
              { id: 'wire', icon: MinusCircle, label: 'Wire' },
              { id: 'net', icon: Minus, label: 'Net Label' },
              { id: 'bus', icon: Square, label: 'Bus' },
              { id: 'text', icon: Type, label: 'Text' },
            ].map((tool) => (
              <button
                key={tool.id}
                onClick={() => setActiveTool(tool.id)}
                className={`p-1.5 rounded ${
                  activeTool === tool.id
                    ? 'bg-background shadow text-blue-600'
                    : 'text-foreground-secondary hover:bg-slate-200'
                }`}
                title={tool.label}
              >
                <tool.icon className="h-4 w-4" />
              </button>
            ))}
          </div>

          <div className="h-6 w-px bg-slate-200 mx-2" />

          {/* Actions */}
          <Button variant="ghost" size="sm" title="Undo">
            <Undo className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" title="Redo">
            <Redo className="h-4 w-4" />
          </Button>

          <div className="h-6 w-px bg-slate-200 mx-2" />

          <Button variant="ghost" size="sm" title="Run ERC" onClick={handleRunERC}>
            <Zap className="h-4 w-4 mr-1" />
            Run ERC
          </Button>

          <Button variant="ghost" size="sm" title="Save">
            <Save className="h-4 w-4" />
          </Button>

          <Button variant="ghost" size="sm" title="Export">
            <Download className="h-4 w-4" />
          </Button>

          <div className="h-6 w-px bg-slate-200 mx-2" />

          <Button variant="ghost" size="icon" title="Settings">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel */}
        <div className="w-64 bg-background border-r border-border flex flex-col shrink-0">
          {/* Panel Tabs */}
          <div className="flex border-b border-border">
            {[
              { id: 'symbols', icon: CircuitBoard, label: 'Symbols' },
              { id: 'nets', icon: Wifi, label: 'Nets' },
              { id: 'sheets', icon: FileText, label: 'Sheets' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setLeftPanel(tab.id as any)}
                className={`flex-1 py-2 text-xs font-medium flex flex-col items-center gap-1 ${
                  leftPanel === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-y-auto">
            {leftPanel === 'symbols' && (
              <div className="p-3 space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input placeholder="Search symbols..." className="pl-9 h-8 text-sm" />
                </div>
                <div className="space-y-1">
                  {SYMBOLS.map((symbol) => (
                    <button
                      key={symbol.id}
                      onClick={() => setSelectedSymbol(symbol)}
                      className="w-full p-2 text-left rounded-md hover:bg-background-tertiary border border-transparent hover:border-border transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <CircuitBoard className="h-4 w-4 text-slate-400" />
                        <span className="text-sm font-medium text-slate-700">{symbol.name}</span>
                      </div>
                      <div className="text-xs text-slate-400 mt-1 ml-6">
                        {symbol.type} · {symbol.pins} pins
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {leftPanel === 'nets' && (
              <div className="p-3">
                <div className="space-y-1">
                  {NETS.map((net) => (
                    <div key={net.id} className="flex items-center gap-2 p-2 rounded-md hover:bg-background-tertiary">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: net.color }} />
                      <span className="text-sm text-slate-700 flex-1">{net.name}</span>
                      <span className="text-xs text-slate-400">{net.connections}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {leftPanel === 'sheets' && (
              <div className="p-3">
                <div className="space-y-1">
                  {SHEETS.map((sheet) => (
                    <button
                      key={sheet.id}
                      className="w-full flex items-center gap-2 p-2 rounded-md hover:bg-background-tertiary"
                    >
                      <FileText className="h-4 w-4 text-slate-400" />
                      <span className="text-sm text-slate-700 flex-1">{sheet.name}</span>
                      <span className="text-xs text-slate-400">{sheet.components}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Main Canvas Area */}
        <div className="flex-1 flex flex-col">
          {/* Canvas Toolbar */}
          <div className="h-10 bg-background-tertiary border-b border-border flex items-center justify-between px-4">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setZoom(Math.max(25, zoom - 25))}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="text-sm text-foreground-secondary w-12 text-center">{zoom}%</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setZoom(Math.min(400, zoom + 25))}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
              <div className="h-4 w-px bg-slate-200 mx-2" />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setGridVisible(!gridVisible)}
                className={gridVisible ? 'text-blue-600' : ''}
              >
                <Grid3X3 className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">Sheet: Main</span>
              <span className="text-sm text-slate-400">|</span>
              <span className="text-sm text-slate-500">Grid: 0.1 inch</span>
            </div>
          </div>

          {/* Canvas */}
          <div className="flex-1 bg-slate-200 overflow-auto relative" style={{
            backgroundImage: gridVisible ? 'radial-gradient(circle, #cbd5e1 1px, transparent 1px)' : 'none',
            backgroundSize: '20px 20px'
          }}>
            {/* Schematic Content */}
            <div className="p-8 min-h-full" style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top left' }}>
              <svg width="1200" height="800" className="bg-background shadow-lg">
                {/* Grid lines */}
                <defs>
                  <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
                    <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#f1f5f9" strokeWidth="0.5" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />

                {/* Components */}
                <g transform="translate(100, 100)">
                  {/* ESP32 Symbol */}
                  <rect x="0" y="0" width="120" height="180" fill="white" stroke="#3b82f6" strokeWidth="2" rx="4" />
                  <text x="60" y="20" textAnchor="middle" className="text-sm font-semibold" fill="#1e293b">ESP32-WROOM</text>
                  <text x="60" y="160" textAnchor="middle" className="text-xs" fill="#64748b">U1</text>
                  {/* Pins */}
                  {[...Array(10)].map((_, i) => (
                    <g key={`l${i}`} transform={`translate(0, ${30 + i * 12})`}>
                      <line x1="0" y1="0" x2="15" y2="0" stroke="#64748b" strokeWidth="1" />
                      <text x="12" y="4" className="text-xs" fill="#64748b">{i + 1}</text>
                    </g>
                  ))}
                  {[...Array(10)].map((_, i) => (
                    <g key={`r${i}`} transform={`translate(120, ${30 + i * 12})`}>
                      <line x1="0" y1="0" x2="-15" y2="0" stroke="#64748b" strokeWidth="1" />
                      <text x="-12" y="4" className="text-xs" fill="#64748b">{i + 21}</text>
                    </g>
                  ))}
                </g>

                <g transform="translate(300, 100)">
                  {/* Capacitor */}
                  <line x1="0" y1="40" x2="30" y2="20" stroke="#1e293b" strokeWidth="2" />
                  <line x1="30" y1="20" x2="30" y2="60" stroke="#1e293b" strokeWidth="2" />
                  <line x1="30" y1="20" x2="60" y2="40" stroke="#1e293b" strokeWidth="2" />
                  <line x1="0" y1="40" x2="60" y2="40" stroke="#64748b" strokeWidth="1" strokeDasharray="4" />
                  <text x="30" y="85" textAnchor="middle" className="text-xs" fill="#64748b">C1</text>
                  <text x="30" y="100" textAnchor="middle" className="text-xs" fill="#64748b">100nF</text>
                </g>

                {/* Wires */}
                <line x1="115" y1="130" x2="160" y2="130" stroke="#1e293b" strokeWidth="2" />
                <line x1="220" y1="130" x2="300" y2="140" stroke="#1e293b" strokeWidth="2" />
                <circle cx="115" cy="130" r="3" fill="#1e293b" />
                <circle cx="220" cy="130" r="3" fill="#1e293b" />

                {/* Net Labels */}
                <g transform="translate(200, 110)">
                  <text className="text-xs font-medium" fill="#ef4444">GND</text>
                </g>
              </svg>
            </div>
          </div>
        </div>

        {/* Right Panel */}
        <div className="w-72 bg-background border-l border-border flex flex-col shrink-0">
          {/* Panel Tabs */}
          <div className="flex border-b border-border">
            {[
              { id: 'properties', icon: Settings, label: 'Properties' },
              { id: 'erc', icon: AlertTriangle, label: 'ERC' },
              { id: 'chat', icon: MessageSquare, label: 'AI' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setRightPanel(tab.id as any)}
                className={`flex-1 py-2 text-xs font-medium flex flex-col items-center gap-1 ${
                  rightPanel === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-y-auto">
            {rightPanel === 'properties' && (
              <div className="p-3 space-y-4">
                {selectedSymbol ? (
                  <>
                    <div>
                      <label className="text-xs font-medium text-slate-500 uppercase">Reference</label>
                      <Input value={selectedSymbol.name} className="mt-1" readOnly />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-500 uppercase">Value</label>
                      <Input value="" placeholder="Enter value..." className="mt-1" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-500 uppercase">Footprint</label>
                      <Input value="" placeholder="Select footprint..." className="mt-1" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-500 uppercase">Library</label>
                      <Input value={selectedSymbol.library} className="mt-1" readOnly />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-slate-500 uppercase">Pins</label>
                      <div className="text-sm text-slate-700 mt-1">{selectedSymbol.pins}</div>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-8 text-slate-400">
                    <CircuitBoard className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Select a component to view properties</p>
                  </div>
                )}
              </div>
            )}

            {rightPanel === 'erc' && (
              <div className="p-3">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-foreground">ERC Results</h3>
                  <Button size="sm" variant="outline" onClick={handleRunERC}>
                    <RefreshCw className="h-3 w-3 mr-1" /> Run
                  </Button>
                </div>
                {showERC ? (
                  <div className="space-y-2">
                    {ERC_ERRORS.map((error) => (
                      <div key={error.id} className="flex items-start gap-2 p-2 rounded bg-red-50 border border-red-100">
                        <XCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm text-red-700">{error.message}</p>
                          <p className="text-xs text-red-500">{error.component}</p>
                        </div>
                      </div>
                    ))}
                    {ERC_WARNINGS.map((warning) => (
                      <div key={warning.id} className="flex items-start gap-2 p-2 rounded bg-amber-50 border border-amber-100">
                        <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm text-amber-700">{warning.message}</p>
                        </div>
                      </div>
                    ))}
                    <div className="flex items-center gap-2 p-2 rounded bg-green-50 border border-green-100">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm text-green-700">No errors found</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-slate-400">
                    <AlertTriangle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Run ERC to check for errors</p>
                  </div>
                )}
              </div>
            )}

            {rightPanel === 'chat' && (
              <div className="flex flex-col h-full">
                <div className="flex-1 p-3 overflow-y-auto">
                  <div className="space-y-3">
                    <div className="flex gap-2">
                      <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                        <Zap className="h-3 w-3 text-blue-600" />
                      </div>
                      <div className="bg-slate-100 rounded-lg p-2 text-sm">
                        Hi! I can help you design your schematic. Try commands like:
                        <ul className="mt-2 space-y-1 text-xs text-foreground-secondary">
                          <li>• "Add a capacitor near U1"</li>
                          <li>• "Connect net VCC to pin 5"</li>
                          <li>• "Check my design"</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="p-3 border-t border-border">
                  <div className="flex gap-2">
                    <Input placeholder="Ask AI to help..." className="flex-1" />
                    <Button size="icon">
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div className="h-6 bg-slate-100 border-t border-border flex items-center justify-between px-4 text-xs text-slate-500">
        <div className="flex items-center gap-4">
          <span>Ready</span>
          <span>4 nets</span>
          <span>8 components</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Grid: 0.1 inch</span>
          <span>Units: Imperial</span>
          <span>Zoom: {zoom}%</span>
        </div>
      </div>
    </div>
  );
}