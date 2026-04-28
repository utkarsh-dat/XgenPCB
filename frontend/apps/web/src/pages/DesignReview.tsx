import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Zap,
  Plus,
  Bell,
  Settings,
  Upload,
  Layers,
  Eye,
  MessageCircle,
  ThumbsUp,
  Download,
  Share2,
  MoreHorizontal,
  Filter,
  Search,
  Clock,
  User,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const DESIGN_REVIEWS = [
  {
    id: '1',
    title: 'USB-C Power Delivery Board - PCB Layout Review',
    author: 'Alice Engineer',
    avatar: 'AE',
    created_at: '3 hours ago',
    views: 234,
    comments: 12,
    upvotes: 45,
    layers: 4,
    components: 89,
    status: 'in-review', // 'in-review', 'needs-work', 'approved'
    feedback: {
      trace_width: { status: 'needs-work', message: 'USB traces could be wider' },
      via_placement: { status: 'good', message: 'Good via placement' },
      ground_plane: { status: 'needs-work', message: 'Add more vias to ground plane' },
      thermal: { status: 'warning', message: 'Check thermal dissipation near power IC' },
    },
    image_url: 'from-blue-500 to-cyan-500',
    description: 'Reviewing my PD board design before sending to manufacturing. Would appreciate feedback on layout!',
  },
  {
    id: '2',
    title: '10 GHz RF PCB - Signal Integrity Check',
    author: 'Bob RF Designer',
    avatar: 'BR',
    created_at: '1 day ago',
    views: 1203,
    comments: 34,
    upvotes: 156,
    layers: 8,
    components: 234,
    status: 'approved',
    feedback: {
      trace_width: { status: 'good', message: 'Excellent trace widths' },
      via_placement: { status: 'good', message: 'Via placement optimized well' },
      ground_plane: { status: 'good', message: 'Solid ground plane design' },
      thermal: { status: 'good', message: 'Thermal management looks good' },
    },
    image_url: 'from-purple-500 to-pink-500',
    description: 'High-frequency design ready for production. Community approved!',
  },
  {
    id: '3',
    title: 'IoT Gateway - First PCB Design',
    author: 'Charlie Maker',
    avatar: 'CM',
    created_at: '2 days ago',
    views: 456,
    comments: 18,
    upvotes: 67,
    layers: 4,
    components: 62,
    status: 'needs-work',
    feedback: {
      trace_width: { status: 'needs-work', message: 'Power traces too thin' },
      via_placement: { status: 'warning', message: 'Some vias could be optimized' },
      ground_plane: { status: 'needs-work', message: 'More ground vias needed' },
      thermal: { status: 'warning', message: 'Module may run hot' },
    },
    image_url: 'from-green-500 to-emerald-500',
    description: 'My first PCB design for an IoT gateway. Any suggestions for improvement?',
  },
];

const FEEDBACK_AREAS = ['trace_width', 'via_placement', 'ground_plane', 'thermal', 'routing', 'shielding'];

export function DesignReview() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [showFilters, setShowFilters] = useState(false);

  const filteredReviews = DESIGN_REVIEWS.filter(review => {
    const matchesSearch = searchQuery === '' || 
      review.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = selectedStatus === 'all' || review.status === selectedStatus;
    return matchesSearch && matchesStatus;
  });

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'approved':
        return { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: 'Approved', icon: CheckCircle };
      case 'needs-work':
        return { bg: 'bg-red-500/20', text: 'text-red-400', label: 'Needs Work', icon: AlertCircle };
      case 'in-review':
        return { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'In Review', icon: AlertCircle };
      default:
        return { bg: 'bg-background-tertiary0/20', text: 'text-slate-400', label: 'Unknown', icon: AlertCircle };
    }
  };

  const getFeedbackColor = (status: string) => {
    switch(status) {
      case 'good':
        return 'text-emerald-400';
      case 'warning':
        return 'text-amber-400';
      case 'needs-work':
        return 'text-red-400';
      default:
        return 'text-slate-400';
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 border-b border-border bg-[#0f0f11]/95 backdrop-blur">
        <div className="max-w-7xl mx-auto px-6 flex h-14 items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-fuchsia-600">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-semibold">PCB Builder</span>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1">
            {['Projects', 'Components', 'Templates', 'Design Reviews', 'Community'].map((tab, i) => (
              <button
                key={tab}
                onClick={() => {
                  if (tab === 'Projects') {
                    navigate('/');
                  } else if (tab === 'Community') {
                    navigate('/community');
                  }
                }}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  (i === 3)
                    ? 'bg-background-tertiary text-foreground'
                    : 'text-foreground-secondary hover:text-foreground hover:bg-background-tertiary/50'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <Button className="gap-2 bg-violet-600 hover:bg-violet-500 text-white">
              <Upload className="h-4 w-4" />
              Submit Design
            </Button>
            <Button variant="ghost" size="icon">
              <Bell className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Hero */}
        <div className="mb-12">
          <h1 className="text-4xl font-bold mb-4">Design Reviews</h1>
          <p className="text-lg text-foreground-secondary max-w-2xl">
            Upload your PCB designs for community feedback on layout, routing, ground planes, and thermal management.
          </p>
        </div>

        {/* Search and Filter */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-muted" />
              <Input
                placeholder="Search designs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-background-secondary/50"
              />
            </div>
            <Button
              variant={showFilters ? "default" : "outline"}
              onClick={() => setShowFilters(!showFilters)}
              className="gap-2"
            >
              <Filter className="h-4 w-4" />
              Status
            </Button>
          </div>

          {showFilters && (
            <div className="bg-background-secondary/50 border border-border rounded-xl p-4 mb-4 flex flex-wrap gap-2">
              {['all', 'in-review', 'needs-work', 'approved'].map(status => (
                <button
                  key={status}
                  onClick={() => setSelectedStatus(status)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-colors capitalize ${
                    selectedStatus === status
                      ? 'bg-violet-600 text-white'
                      : 'bg-background-tertiary text-foreground-secondary hover:text-foreground'
                  }`}
                >
                  {status === 'all' ? 'All Reviews' : status.replace('-', ' ')}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Design Reviews Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {filteredReviews.map(review => {
            const statusInfo = getStatusColor(review.status);
            const StatusIcon = statusInfo.icon;

            return (
              <Card
                key={review.id}
                className="bg-background-secondary border-border hover:border-accent-primary/50 transition-all cursor-pointer overflow-hidden flex flex-col group"
                onClick={() => navigate(`/design-review/${review.id}`)}
              >
                {/* Design Preview */}
                <div className={`h-40 bg-gradient-to-br ${review.image_url} relative overflow-hidden`}>
                  <svg width="100%" height="100%" className="absolute opacity-20">
                    <defs>
                      <pattern id={`grid-${review.id}`} width="20" height="20" patternUnits="userSpaceOnUse">
                        <path d="M 20 0 L 0 0 0 20" fill="none" stroke="white" strokeWidth="0.5" />
                      </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill={`url(#grid-${review.id})`} />
                  </svg>

                  {/* Status Badge */}
                  <div className="absolute top-2 right-2">
                    <Badge className={`${statusInfo.bg} ${statusInfo.text} border-0`}>
                      <StatusIcon className="h-3 w-3 mr-1" />
                      {statusInfo.label}
                    </Badge>
                  </div>

                  {/* Layer/Component Info */}
                  <div className="absolute bottom-2 left-2 space-y-1 text-xs text-white drop-shadow">
                    <div className="flex items-center gap-1">
                      <Layers className="h-3 w-3" />
                      {review.layers}L Board
                    </div>
                  </div>
                </div>

                <CardContent className="p-5 flex-1 flex flex-col">
                  {/* Title */}
                  <h3 className="font-bold text-foreground mb-2 line-clamp-2 group-hover:text-violet-400 transition-colors">
                    {review.title}
                  </h3>

                  {/* Description */}
                  <p className="text-sm text-foreground-muted mb-4 line-clamp-2 flex-1">
                    {review.description}
                  </p>

                  {/* Feedback Summary */}
                  <div className="mb-4 space-y-1.5 text-xs">
                    {Object.entries(review.feedback).slice(0, 3).map(([key, feedback]: any) => (
                      <div key={key} className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${
                          feedback.status === 'good' ? 'bg-emerald-400' : 
                          feedback.status === 'warning' ? 'bg-amber-400' : 
                          'bg-red-400'
                        }`} />
                        <span className="text-foreground-muted capitalize">
                          {key.replace('_', ' ')}: {feedback.status}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Author & Stats */}
                  <div className="border-t border-border pt-3 mb-3">
                    <div className="flex items-center gap-2 mb-3 text-xs">
                      <div className="h-6 w-6 rounded-full bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center text-xs font-bold text-white">
                        {review.avatar}
                      </div>
                      <div className="flex-1">
                        <p className="text-foreground-secondary">{review.author}</p>
                        <p className="text-foreground-muted text-xs">{review.created_at}</p>
                      </div>
                    </div>

                    {/* Engagement Stats */}
                    <div className="flex items-center justify-between text-xs text-foreground-muted">
                      <div className="flex items-center gap-2">
                        <Eye className="h-3 w-3" />
                        <span>{review.views}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <MessageCircle className="h-3 w-3" />
                        <span>{review.comments}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <ThumbsUp className="h-3 w-3" />
                        <span>{review.upvotes}</span>
                      </div>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <Button className="flex-1 bg-violet-600 hover:bg-violet-500 text-white" size="sm">
                      <MessageCircle className="h-3.5 w-3.5 mr-1" />
                      Give Feedback
                    </Button>
                    <Button variant="outline" size="sm" className="gap-1">
                      <Download className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {filteredReviews.length === 0 && (
          <div className="text-center py-12">
            <Upload className="h-12 w-12 text-foreground-muted mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No designs found</h3>
            <p className="text-foreground-muted mb-6">Be the first to submit your PCB design for review</p>
            <Button className="gap-2 bg-violet-600 hover:bg-violet-500 text-white">
              <Upload className="h-4 w-4" />
              Submit Your Design
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
