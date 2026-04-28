import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Zap, Layout, FileText, Clock, ChevronRight, Grid, List, FolderOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const TEMPLATES = [
  { id: 't1', name: 'Arduino Uno R3', category: 'Microcontroller', downloads: 5200, rating: 4.8, layers: 2 },
  { id: 't2', name: 'ESP32 WiFi Board', category: 'Wireless', downloads: 3400, rating: 4.7, layers: 2 },
  { id: 't3', name: 'Raspberry Pi Pico HAT', category: 'SBC', downloads: 2800, rating: 4.9, layers: 2 },
  { id: 't4', name: 'USB-C PD Controller', category: 'Power', downloads: 1500, rating: 4.6, layers: 4 },
  { id: 't5', name: 'BLE Beacon', category: 'Wireless', downloads: 1200, rating: 4.7, layers: 2 },
  { id: 't6', name: 'Motor Driver Board', category: 'Motor Control', downloads: 890, rating: 4.5, layers: 4 },
  { id: 't7', name: '4-Layer DDR4 Board', category: 'High-Speed', downloads: 567, rating: 4.8, layers: 4 },
  { id: 't8', name: 'LED Matrix Driver', category: 'LED', downloads: 450, rating: 4.4, layers: 2 },
  { id: 't9', name: 'Audio Amplifier', category: 'Audio', downloads: 890, rating: 4.6, layers: 2 },
];

const CATEGORIES = ['All', 'Microcontroller', 'Wireless', 'Power', 'Motor Control', 'LED', 'Audio', 'High-Speed', 'SBC'];

export function Templates() {
  const [activeCategory, setActiveCategory] = useState('All');
  const [viewMode, setViewMode] = useState('grid');

  const filteredTemplates = TEMPLATES.filter((t) => {
    if (activeCategory !== 'All' && t.category !== activeCategory) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-background-tertiary">
      <header className="bg-background-secondary border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Templates</h1>
              <p className="text-slate-500">Start with proven PCB designs</p>
            </div>
            <Button className="bg-blue-600">
              <Layout className="h-4 w-4 mr-2" /> Create Template
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex gap-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
                  activeCategory === cat ? 'bg-blue-100 text-blue-700' : 'text-foreground-secondary hover:bg-slate-100'
                }`}
              >
                {cat}
              </button>
            ))}
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

        <div className={viewMode === 'grid' ? 'grid grid-cols-3 gap-4' : 'space-y-3'}>
          {filteredTemplates.map((template) => (
            <Card key={template.id} className="bg-background-secondary border-border">
              <CardContent className="p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-green-50">
                    <Layout className="h-5 w-5 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-foreground">{template.name}</h3>
                    <p className="text-xs text-slate-500">{template.category}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between text-sm text-slate-500 mb-3">
                  <span>{template.downloads.toLocaleString()} downloads</span>
                  <span>★ {template.rating}</span>
                </div>
                <div className="flex items-center justify-between">
                  <Badge variant="secondary">{template.layers} layers</Badge>
                  <Button size="sm">Use Template</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}