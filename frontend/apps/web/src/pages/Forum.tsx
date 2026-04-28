import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Zap, 
  Plus,
  Search,
  Filter,
  Grid,
  List,
  MessageCircle,
  ThumbsUp,
  Eye,
  Clock,
  ChevronRight,
  Award,
  BookOpen,
  HelpCircle,
  Wrench,
  CircuitBoard,
  Package,
  Tags,
  ChevronDown,
  MoreHorizontal
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const CATEGORIES = [
  { id: 'beginner', name: 'Beginner PCB Help', icon: HelpCircle, count: 234, color: 'blue' },
  { id: 'troubleshooting', name: 'Circuit Troubleshooting', icon: Wrench, count: 189, color: 'red' },
  { id: 'components', name: 'Component Selection', icon: CircuitBoard, count: 156, color: 'purple' },
  { id: 'layout', name: 'PCB Layout Tips', icon: Tags, count: 145, color: 'green' },
  { id: 'manufacturing', name: 'Manufacturing Problems', icon: Package, count: 98, color: 'orange' },
];

const POSTS = [
  { 
    id: 'p1', 
    title: 'How do I reduce noise in my analog circuit?', 
    author: 'Sarah K.', 
    category: 'troubleshooting',
    votes: 24,
    answers: 8,
    views: 342,
    time: '2 hours ago',
    solved: true
  },
  { 
    id: 'p2', 
    title: 'Best layer stackup for 4-layer DDR4 board?', 
    author: 'Mike T.', 
    category: 'layout',
    votes: 18,
    answers: 5,
    views: 267,
    time: '5 hours ago',
    solved: false
  },
  { 
    id: 'p3', 
    title: 'Why is my PCB heating up?', 
    author: 'Alex R.', 
    category: 'troubleshooting',
    votes: 45,
    answers: 15,
    views: 892,
    time: '1 day ago',
    solved: true
  },
  { 
    id: 'p4', 
    title: 'Alternative MOSFET for budget project?', 
    author: 'Emma W.', 
    category: 'components',
    votes: 12,
    answers: 6,
    views: 156,
    time: '2 days ago',
    solved: false
  },
];

const TOP_CONTRIBUTORS = [
  { name: 'John D.', reputation: 12500, help: 234 },
  { name: 'Sarah K.', reputation: 8900, help: 156 },
  { name: 'Mike T.', reputation: 6780, help: 98 },
];

export function Forum() {
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('list');

  const filteredPosts = POSTS.filter((post) => {
    if (activeCategory !== 'all' && post.category !== activeCategory) return false;
    if (searchQuery && !post.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-background-tertiary">
      {/* Header */}
      <header className="bg-background-secondary border-b border-border">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Community Forum</h1>
              <p className="text-slate-500">Ask questions, share knowledge, get help</p>
            </div>
            <Button className="bg-blue-600">
              <Plus className="h-4 w-4 mr-2" /> Ask Question
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="col-span-1 space-y-4">
            {/* Categories */}
            <Card className="bg-background-secondary border-border">
              <CardContent className="p-4">
                <h3 className="font-medium text-foreground mb-3">Categories</h3>
                <div className="space-y-1">
                  <button
                    onClick={() => setActiveCategory('all')}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm ${
                      activeCategory === 'all' ? 'bg-blue-50 text-blue-700' : 'text-foreground-secondary hover:bg-background-tertiary'
                    }`}
                  >
                    <span>All Categories</span>
                    <Badge variant="secondary" className="text-xs">{POSTS.length}</Badge>
                  </button>
                  {CATEGORIES.map((cat) => (
                    <button
                      key={cat.id}
                      onClick={() => setActiveCategory(cat.id)}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm ${
                        activeCategory === cat.id ? 'bg-blue-50 text-blue-700' : 'text-foreground-secondary hover:bg-background-tertiary'
                      }`}
                    >
                      <span>{cat.name}</span>
                      <Badge variant="secondary" className="text-xs">{cat.count}</Badge>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Top Contributors */}
            <Card className="bg-background-secondary border-border">
              <CardContent className="p-4">
                <h3 className="font-medium text-foreground mb-3 flex items-center gap-2">
                  <Award className="h-4 w-4 text-amber-500" /> Top Contributors
                </h3>
                <div className="space-y-3">
                  {TOP_CONTRIBUTORS.map((user, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center text-sm font-medium">
                        {user.name.charAt(0)}
                      </div>
                      <div className="flex-1">
                        <div className="font-medium text-foreground text-sm">{user.name}</div>
                        <div className="text-xs text-slate-500">{user.reputation.toLocaleString()} rep · {user.help} help</div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="col-span-3 space-y-4">
            {/* Search & Filter */}
            <div className="flex items-center justify-between">
              <div className="relative w-96">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  placeholder="Search discussions..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm">
                  <Filter className="h-4 w-4 mr-2" /> Filter
                </Button>
                <div className="flex items-center border border-border rounded-md">
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 ${viewMode === 'list' ? 'bg-slate-100' : ''}`}
                  >
                    <List className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 ${viewMode === 'grid' ? 'bg-slate-100' : ''}`}
                  >
                    <Grid className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* Posts */}
            <div className="space-y-3">
              {filteredPosts.map((post) => (
                <Card key={post.id} className="bg-background-secondary border-border hover:border-blue-300 transition-colors">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-4">
                      {/* Votes */}
                      <div className="flex flex-col items-center gap-1">
                        <button className="p-1 rounded hover:bg-background-tertiary">
                          <ThumbsUp className="h-4 w-4 text-slate-400" />
                        </button>
                        <span className="font-medium text-foreground">{post.votes}</span>
                      </div>

                      {/* Content */}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="secondary" className="text-xs">{post.category}</Badge>
                          {post.solved && (
                            <Badge variant="success" className="text-xs">Solved</Badge>
                          )}
                        </div>
                        <h3 className="font-medium text-foreground hover:text-blue-600 cursor-pointer">
                          {post.title}
                        </h3>
                        <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                          <span>{post.author}</span>
                          <span>·</span>
                          <span className="flex items-center gap-1">
                            <MessageCircle className="h-3 w-3" /> {post.answers} answers
                          </span>
                          <span>·</span>
                          <span className="flex items-center gap-1">
                            <Eye className="h-3 w-3" /> {post.views} views
                          </span>
                          <span>·</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" /> {post.time}
                          </span>
                        </div>
                      </div>

                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}