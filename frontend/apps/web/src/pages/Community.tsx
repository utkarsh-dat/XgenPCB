import { Link } from 'react-router-dom';
import { 
  Zap, 
  Layout,
  Package,
  FileText,
  HelpCircle,
  CircuitBoard,
  Users,
  BookOpen,
  Trophy,
  ChevronRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

const SECTIONS = [
  { 
    id: 'forum', 
    name: 'Discussion Forum', 
    description: 'Ask questions, get answers',
    icon: HelpCircle,
    count: '5,234 posts',
    color: 'blue'
  },
  { 
    id: 'design-review', 
    name: 'Design Review', 
    description: 'Get expert feedback',
    icon: CircuitBoard,
    count: '1,234 reviews',
    color: 'green'
  },
  { 
    id: 'project-sharing', 
    name: 'Project Sharing', 
    description: 'Share your designs',
    icon: FileText,
    count: '3,456 projects',
    color: 'purple'
  },
  { 
    id: 'tutorials', 
    name: 'Tutorials', 
    description: 'Learn PCB design',
    icon: BookOpen,
    count: '45 tutorials',
    color: 'orange'
  },
  { 
    id: 'challenges', 
    name: 'Challenges', 
    description: 'Weekly competitions',
    icon: Trophy,
    count: 'Active challenge',
    color: 'amber'
  },
  { 
    id: 'templates', 
    name: 'Template Gallery', 
    description: 'Pre-made designs',
    icon: Layout,
    count: '850 templates',
    color: 'cyan'
  },
];

export function Community() {
  return (
    <div className="min-h-screen bg-background-tertiary">
      <header className="bg-background-secondary border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Community</h1>
              <p className="text-slate-500">Connect, learn, and share with engineers worldwide</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline">Join Discord</Button>
              <Button className="bg-blue-600">Join Community</Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-3 gap-4">
          {SECTIONS.map((section) => (
            <Link key={section.id} to={`/${section.id}`}>
              <Card className="bg-background-secondary border-border hover:border-blue-300 transition-all h-full">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-lg bg-${section.color}-50`}>
                      <section.icon className={`h-6 w-6 text-${section.color}-600`} />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-medium text-foreground">{section.name}</h3>
                      <p className="text-sm text-slate-500">{section.description}</p>
                      <p className="text-xs text-slate-400 mt-1">{section.count}</p>
                    </div>
                    <ChevronRight className="h-5 w-5 text-slate-300" />
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