import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Zap, Play, BookOpen, Clock, CheckCircle, ChevronRight, Search, Filter, Grid, List } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const TUTORIALS = [
  { id: 't1', title: 'PCB Design Basics', category: 'Beginner', difficulty: 'Easy', duration: '30 min', steps: 8, completed: 2340 },
  { id: 't2', title: 'Understanding Layer Stackup', category: 'Intermediate', difficulty: 'Medium', duration: '45 min', steps: 12, completed: 1890 },
  { id: 't3', title: 'Routing Rules & Best Practices', category: 'Advanced', difficulty: 'Hard', duration: '60 min', steps: 15, completed: 980 },
  { id: 't4', title: 'Grounding Techniques', category: 'Intermediate', difficulty: 'Medium', duration: '40 min', steps: 10, completed: 1560 },
  { id: 't5', title: 'High-Speed Design', category: 'Advanced', difficulty: 'Hard', duration: '90 min', steps: 20, completed: 450 },
  { id: 't6', title: 'SMT Soldering Guide', category: 'Beginner', difficulty: 'Easy', duration: '25 min', steps: 6, completed: 3200 },
];

const CATEGORIES = ['All', 'Beginner', 'Intermediate', 'Advanced'];

const DIFFICULTY_COLORS = {
  'Easy': 'green',
  'Medium': 'amber',
  'Hard': 'red',
};

export function TutorialView() {
  const [activeCategory, setActiveCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredTutorials = TUTORIALS.filter((t) => {
    if (activeCategory !== 'All' && t.category !== activeCategory) return false;
    if (searchQuery && !t.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-background-tertiary">
      <header className="bg-background-secondary border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Learning Center</h1>
              <p className="text-slate-500">Master PCB design with guided tutorials</p>
            </div>
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
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  activeCategory === cat ? 'bg-blue-100 text-blue-700' : 'text-foreground-secondary hover:bg-slate-100'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search tutorials..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-border rounded-lg"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {filteredTutorials.map((tutorial) => (
            <Link key={tutorial.id} to={`/tutorials/${tutorial.id}`}>
              <Card className="bg-background-secondary border-border hover:border-blue-300 transition-all h-full">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Badge variant="secondary">{tutorial.category}</Badge>
                    <Badge variant={DIFFICULTY_COLORS[tutorial.difficulty as keyof typeof DIFFICULTY_COLORS] as any}>
                      {tutorial.difficulty}
                    </Badge>
                  </div>
                  <h3 className="font-medium text-foreground mb-2">{tutorial.title}</h3>
                  <div className="flex items-center gap-4 text-sm text-slate-500">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {tutorial.duration}
                    </span>
                    <span>{tutorial.steps} steps</span>
                  </div>
                  <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-sm text-slate-500">
                      {tutorial.completed.toLocaleString()} completed
                    </span>
                    <Button size="sm" variant="outline">
                      <Play className="h-3 w-3 mr-1" /> Start
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}