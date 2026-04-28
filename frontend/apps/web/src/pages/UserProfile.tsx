import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Zap,
  Plus,
  Bell,
  Settings,
  User,
  Edit2,
  Copy,
  Share2,
  Heart,
  MessageCircle,
  Link as LinkIcon,
  MapPin,
  Mail,
  Calendar,
  Award,
  Users as FollowersIcon,
  Grid3x3,
  List,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface UserProfile {
  name: string;
  email: string;
  bio: string;
  specialty: string;
  location: string;
  website: string;
  avatar: string;
  followers: number;
  following: number;
  totalProjects: number;
  totalLikes: number;
  joinDate: string;
  verified: boolean;
  badges: string[];
}

interface UserDesign {
  id: string;
  title: string;
  description: string;
  likes: number;
  downloads: number;
  views: number;
  tags: string[];
  isPublic: boolean;
  created: string;
}

export function UserProfile() {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Mock user profile data
  const userProfile: UserProfile = {
    name: 'Alex Chen',
    email: 'alex@example.com',
    bio: 'Hardware engineer passionate about IoT and open-source electronics. Building the future of connected devices.',
    specialty: 'IoT Solutions',
    location: 'San Francisco, CA',
    website: 'https://alexchen.dev',
    avatar: 'AC',
    followers: 3421,
    following: 245,
    totalProjects: 24,
    totalLikes: 12543,
    joinDate: 'Joined March 2023',
    verified: true,
    badges: ['Early Adopter', 'Community Champion', 'Top Designer'],
  };

  const userDesigns: UserDesign[] = [
    {
      id: 'design-1',
      title: 'ESP32 IoT Sensor Board',
      description: 'WiFi-enabled sensor board with temperature and humidity monitoring',
      likes: 892,
      downloads: 456,
      views: 8932,
      tags: ['IoT', 'ESP32', 'Open-Source'],
      isPublic: true,
      created: '2 months ago',
    },
    {
      id: 'design-2',
      title: 'LoRaWAN Gateway',
      description: 'Long-range wireless gateway for IoT networks',
      likes: 654,
      downloads: 321,
      views: 5432,
      tags: ['LoRa', 'Gateway', 'Networking'],
      isPublic: true,
      created: '3 months ago',
    },
    {
      id: 'design-3',
      title: 'Environmental Monitor',
      description: 'Multi-sensor environmental monitoring device',
      likes: 423,
      downloads: 198,
      views: 3245,
      tags: ['Sensors', 'Environment', 'IoT'],
      isPublic: true,
      created: '4 months ago',
    },
    {
      id: 'design-4',
      title: 'Smart Home Hub',
      description: 'Central hub for smart home automation (Private)',
      likes: 0,
      downloads: 0,
      views: 234,
      tags: ['Smart Home', 'Hub', 'Automation'],
      isPublic: false,
      created: '1 week ago',
    },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top Navigation */}
      <header className="sticky top-0 z-50 border-b border-border bg-[#0f0f11]/95 backdrop-blur supports-[backdrop-filter]:bg-[#0f0f11]/80">
        <div className="flex h-14 items-center justify-between px-6">
          {/* Logo */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-fuchsia-600 shadow-lg shadow-violet-500/25">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-semibold text-foreground">PCB Builder</span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="text-foreground-secondary hover:bg-background-tertiary hover:text-foreground">
              <Bell className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="text-foreground-secondary hover:bg-background-tertiary hover:text-foreground">
              <Settings className="h-4 w-4" />
            </Button>
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center text-sm font-bold text-white cursor-pointer shadow-lg shadow-violet-500/25">
              {userProfile.avatar}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Profile Header */}
        <div className="relative mb-8">
          {/* Cover Background */}
          <div className="h-32 bg-gradient-to-r from-violet-600/20 to-fuchsia-600/20 rounded-xl border border-border mb-6 relative overflow-hidden">
            <svg width="100%" height="100%" className="absolute opacity-10">
              <defs>
                <pattern id="cover-pattern" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 0 0 L 40 40 M 40 0 L 0 40" stroke="currentColor" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#cover-pattern)" />
            </svg>
          </div>

          {/* Profile Info */}
          <div className="flex flex-col md:flex-row gap-6">
            {/* Avatar and Basic Info */}
            <div className="flex flex-col items-start gap-4 md:flex-row md:items-end">
              <div className="h-24 w-24 rounded-2xl bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center text-4xl font-bold text-white shadow-lg shadow-violet-500/25">
                {userProfile.avatar}
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h1 className="text-3xl font-bold text-foreground">{userProfile.name}</h1>
                  {userProfile.verified && (
                    <Badge className="bg-violet-600 text-white">✓ Verified</Badge>
                  )}
                </div>
                <p className="text-lg text-foreground-secondary mb-3">{userProfile.specialty}</p>

                {/* Badges */}
                <div className="flex flex-wrap gap-2">
                  {userProfile.badges.map(badge => (
                    <Badge key={badge} variant="secondary" className="bg-background-tertiary">
                      <Award className="h-3 w-3 mr-1" />
                      {badge}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button
                  onClick={() => setIsEditing(!isEditing)}
                  className="gap-2 bg-violet-600 hover:bg-violet-500 text-white"
                >
                  <Edit2 className="h-4 w-4" />
                  {isEditing ? 'Done' : 'Edit Profile'}
                </Button>
                <Button variant="outline" className="gap-2">
                  <Share2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Bio and Contact Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
            <div className="md:col-span-2">
              <h3 className="text-sm font-semibold text-foreground-muted mb-2">About</h3>
              {isEditing ? (
                <textarea
                  className="w-full bg-background-secondary/50 border border-border rounded-lg p-3 text-foreground placeholder:text-foreground-muted text-sm"
                  rows={3}
                  defaultValue={userProfile.bio}
                />
              ) : (
                <p className="text-foreground-secondary">{userProfile.bio}</p>
              )}
            </div>

            <div>
              <h3 className="text-sm font-semibold text-foreground-muted mb-3">Contact & Location</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 text-foreground-secondary">
                  <Mail className="h-4 w-4" />
                  {userProfile.email}
                </div>
                <div className="flex items-center gap-2 text-foreground-secondary">
                  <MapPin className="h-4 w-4" />
                  {userProfile.location}
                </div>
                <div className="flex items-center gap-2 text-foreground-secondary">
                  <LinkIcon className="h-4 w-4" />
                  <a href={userProfile.website} target="_blank" rel="noopener noreferrer" className="text-violet-400 hover:text-violet-300">
                    {userProfile.website}
                  </a>
                </div>
                <div className="flex items-center gap-2 text-foreground-secondary">
                  <Calendar className="h-4 w-4" />
                  {userProfile.joinDate}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-background-secondary/50 border-border">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{userProfile.totalProjects}</p>
              <p className="text-xs text-foreground-muted">Total Projects</p>
            </CardContent>
          </Card>
          <Card className="bg-background-secondary/50 border-border">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{userProfile.followers}</p>
              <p className="text-xs text-foreground-muted">Followers</p>
            </CardContent>
          </Card>
          <Card className="bg-background-secondary/50 border-border">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{userProfile.following}</p>
              <p className="text-xs text-foreground-muted">Following</p>
            </CardContent>
          </Card>
          <Card className="bg-background-secondary/50 border-border">
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold text-foreground">{userProfile.totalLikes}</p>
              <p className="text-xs text-foreground-muted">Total Likes</p>
            </CardContent>
          </Card>
        </div>

        {/* Designs Section */}
        <div className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-foreground">My Designs</h2>
              <p className="text-sm text-foreground-muted mt-1">
                {userDesigns.length} designs
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('grid')}
              >
                <Grid3x3 className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('list')}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {userDesigns.map(design => (
                <Card
                  key={design.id}
                  className="bg-background-secondary border-border hover:border-accent-primary/50 transition-all cursor-pointer overflow-hidden"
                >
                  <div className="h-32 bg-gradient-to-br from-background-tertiary to-background-secondary/50 relative">
                    <svg width="100%" height="100%">
                      <defs>
                        <pattern id={`grid-${design.id}`} width="20" height="20" patternUnits="userSpaceOnUse">
                          <path d="M 20 0 L 0 0 0 20" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.2" />
                        </pattern>
                      </defs>
                      <rect width="100%" height="100%" fill={`url(#grid-${design.id})`} />
                    </svg>
                    {!design.isPublic && (
                      <Badge className="absolute top-2 right-2 bg-slate-600 text-white">Private</Badge>
                    )}
                  </div>

                  <CardContent className="p-4">
                    <h3 className="font-bold text-foreground mb-1 line-clamp-2">{design.title}</h3>
                    <p className="text-xs text-foreground-muted mb-2 line-clamp-2">{design.description}</p>

                    {/* Tags */}
                    <div className="flex flex-wrap gap-1 mb-3">
                      {design.tags.map(tag => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>

                    {/* Stats */}
                    <div className="flex gap-2 text-xs text-foreground-muted mb-3 pb-3 border-t border-border pt-3">
                      <span className="flex items-center gap-1">
                        <Heart className="h-3 w-3" /> {design.likes}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageCircle className="h-3 w-3" /> {design.downloads}
                      </span>
                    </div>

                    <div className="flex gap-2">
                      <Button className="flex-1 bg-violet-600 hover:bg-violet-500 text-white" size="sm">
                        View
                      </Button>
                      <Button variant="outline" size="sm">
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {userDesigns.map(design => (
                <Card
                  key={design.id}
                  className="bg-background-secondary border-border hover:border-accent-primary/50 transition-all cursor-pointer"
                >
                  <CardContent className="p-4 flex items-start gap-4">
                    <div className="h-20 w-20 rounded-lg bg-gradient-to-br from-background-tertiary to-background-secondary/50 flex-shrink-0" />

                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-1">
                        <h3 className="font-bold text-foreground">{design.title}</h3>
                        {!design.isPublic && <Badge className="bg-slate-600 text-white">Private</Badge>}
                      </div>
                      <p className="text-sm text-foreground-muted mb-2 line-clamp-1">{design.description}</p>
                      <div className="flex flex-wrap gap-1">
                        {design.tags.map(tag => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      <div className="text-right">
                        <p className="text-sm text-foreground flex items-center gap-1">
                          <Heart className="h-4 w-4" /> {design.likes}
                        </p>
                        <p className="text-xs text-foreground-muted">{design.created}</p>
                      </div>
                      <Button className="bg-violet-600 hover:bg-violet-500 text-white" size="sm">
                        View
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
