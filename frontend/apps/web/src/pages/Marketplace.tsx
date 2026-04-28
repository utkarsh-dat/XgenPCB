import { Link } from 'react-router-dom';
import { 
  Zap, 
  Package, 
  Layout, 
  Users,
  Wrench,
  CheckCircle,
  Star,
  Search,
  ChevronRight,
  Filter,
  Grid,
  List
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useState } from 'react';

const CATEGORIES = [
  { id: 'components', name: 'Components', icon: Package, count: 12500 },
  { id: 'templates', name: 'Templates', icon: Layout, count: 850 },
  { id: 'services', name: 'Services', icon: Wrench, count: 120 },
];

const POPULAR_COMPONENTS = [
  { id: 'c1', name: 'ESP32-WROOM-32E', price: '$3.50', supplier: 'DigiKey', stock: 'In stock', rating: 4.8, reviews: 234 },
  { id: 'c2', name: 'STM32F103C8T6', price: '$2.80', supplier: 'Mouser', stock: 'In stock', rating: 4.9, reviews: 189 },
  { id: 'c3', name: 'AMS1117-3.3', price: '$0.25', supplier: 'LCSC', stock: 'In stock', rating: 4.7, reviews: 567 },
  { id: 'c4', name: 'USB-C Connector', price: '$0.85', supplier: 'DigiKey', stock: 'Low stock', rating: 4.6, reviews: 123 },
  { id: 'c5', name: 'LM7805', price: '$0.45', supplier: 'LCSC', stock: 'In stock', rating: 4.8, reviews: 890 },
  { id: 'c6', name: 'NE555', price: '$0.15', supplier: 'LCSC', stock: 'In stock', rating: 4.9, reviews: 1234 },
];

const TEMPLATES = [
  { id: 't1', name: 'Arduino Uno R3 Shield', price: '$9.99', downloads: 5200, rating: 4.8, author: 'PCB Builder' },
  { id: 't2', name: 'ESP32 WiFi Board', price: '$14.99', downloads: 3400, rating: 4.7, author: 'ElectroLab' },
  { id: 't3', name: 'Raspberry Pi Pico HAT', price: '$12.99', downloads: 2800, rating: 4.9, author: 'MakerKit' },
  { id: 't4', name: 'USB-C PD Controller', price: '$19.99', downloads: 1500, rating: 4.6, author: 'PowerDesign' },
  { id: 't5', name: 'BLE Beacon Module', price: '$11.99', downloads: 1200, rating: 4.7, author: 'WirelessPro' },
  { id: 't6', name: 'Motor Driver Board', price: '$24.99', downloads: 890, rating: 4.5, author: 'MotorWorks' },
];

const SERVICES = [
  { id: 's1', name: 'PCB Fabrication', provider: 'JLCPCB', rating: 4.8, price: '$2/board', minQty: 5 },
  { id: 's2', name: 'PCB Assembly', provider: 'PCBWay', rating: 4.7, price: '$10/board', minQty: 1 },
  { id: 's3', name: 'Design Review', provider: 'ExpertPCB', rating: 4.9, price: '$50/review', minQty: 1 },
  { id: 's4', name: 'Custom Parts', provider: 'Digikey', rating: 4.8, price: 'Varies', minQty: 1 },
];

export function Marketplace() {
  const [activeCategory, setActiveCategory] = useState('components');
  const [viewMode, setViewMode] = useState('grid');

  return (
    <div className="min-h-screen bg-background-tertiary">
      {/* Header */}
      <header className="bg-background-secondary border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Marketplace</h1>
              <p className="text-slate-500">Components, templates, and services</p>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline">Sell</Button>
              <Button className="bg-blue-600">Cart (0)</Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Categories */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {CATEGORIES.map((cat) => (
            <Card 
              key={cat.id} 
              className={`cursor-pointer transition-all ${activeCategory === cat.id ? 'border-blue-500 shadow-md' : 'hover:border-slate-300'}`}
              onClick={() => setActiveCategory(cat.id)}
            >
              <CardContent className="p-4 flex items-center gap-4">
                <div className={`p-3 rounded-lg ${activeCategory === cat.id ? 'bg-blue-100' : 'bg-slate-100'}`}>
                  <cat.icon className={`h-6 w-6 ${activeCategory === cat.id ? 'text-blue-600' : 'text-foreground-secondary'}`} />
                </div>
                <div>
                  <h3 className="font-medium text-foreground">{cat.name}</h3>
                  <p className="text-sm text-slate-500">{cat.count.toLocaleString()} items</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Search & Filter */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="relative w-80">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input 
                type="text" 
                placeholder={`Search ${activeCategory}...`}
                className="w-full pl-10 pr-4 py-2 border border-border rounded-lg"
              />
            </div>
            <Button variant="outline">
              <Filter className="h-4 w-4 mr-2" /> Filters
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Button variant={viewMode === 'grid' ? 'secondary' : 'ghost'} size="icon" onClick={() => setViewMode('grid')}>
              <Grid className="h-4 w-4" />
            </Button>
            <Button variant={viewMode === 'list' ? 'secondary' : 'ghost'} size="icon" onClick={() => setViewMode('list')}>
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Content */}
        {activeCategory === 'components' && (
          <div className={viewMode === 'grid' ? 'grid grid-cols-3 gap-4' : 'space-y-3'}>
            {POPULAR_COMPONENTS.map((item) => (
              <Card key={item.id} className="bg-background-secondary border-border">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="font-medium text-foreground">{item.name}</div>
                    <Badge variant="success" className="text-xs">{item.stock}</Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm text-slate-500 mb-3">
                    <span>{item.supplier}</span>
                    <div className="flex items-center gap-1">
                      <Star className="h-3 w-3 text-amber-400" />
                      {item.rating} ({item.reviews})
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">{item.price}</span>
                    <Button size="sm">Add to BOM</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {activeCategory === 'templates' && (
          <div className={viewMode === 'grid' ? 'grid grid-cols-3 gap-4' : 'space-y-3'}>
            {TEMPLATES.map((item) => (
              <Card key={item.id} className="bg-background-secondary border-border">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex gap-2">
                      <Layout className="h-5 w-5 text-slate-400" />
                      <div className="font-medium text-foreground">{item.name}</div>
                    </div>
                    <Badge variant="secondary" className="text-xs">Template</Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm text-slate-500 mb-3">
                    <span>by {item.author}</span>
                    <div className="flex items-center gap-1">
                      <Star className="h-3 w-3 text-amber-400" />
                      {item.rating} · {item.downloads.toLocaleString()} downloads
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">{item.price}</span>
                    <Button size="sm" variant="outline">Buy</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {activeCategory === 'services' && (
          <div className={viewMode === 'grid' ? 'grid grid-cols-2 gap-4' : 'space-y-3'}>
            {SERVICES.map((item) => (
              <Card key={item.id} className="bg-background-secondary border-border">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="font-medium text-foreground">{item.name}</div>
                    <div className="flex items-center gap-1">
                      <Star className="h-4 w-4 text-amber-400" />
                      <span className="font-medium">{item.rating}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-sm text-slate-500 mb-3">
                    <span>{item.provider}</span>
                    <span>Min qty: {item.minQty}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">{item.price}</span>
                    <Button size="sm">Order</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}