import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Zap, 
  Users, 
  FolderOpen, 
  BarChart3, 
  Settings,
  Search,
  Plus,
  MoreHorizontal,
  ChevronRight,
  ChevronDown,
  Shield,
  Mail,
  CreditCard,
  Key,
  Bell,
  LogOut,
  User,
  Eye,
  Download,
  Trash2,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const ALL_USERS = [
  { id: 'u1', name: 'John Doe', email: 'john@example.com', plan: 'pro', active: true, joined: '2026-01-15', projects: 12 },
  { id: 'u2', name: 'Sarah Kim', email: 'sarah@example.com', plan: 'team', active: true, joined: '2026-01-10', projects: 24 },
  { id: 'u3', name: 'Mike Chen', email: 'mike@example.com', plan: 'free', active: false, joined: '2025-12-20', projects: 3 },
  { id: 'u4', name: 'Alex Rivera', email: 'alex@example.com', plan: 'pro', active: true, joined: '2026-01-08', projects: 8 },
  { id: 'u5', name: 'Emma Wilson', email: 'emma@example.com', plan: 'free', active: true, joined: '2026-01-05', projects: 5 },
];

const ALL_PROJECTS = [
  { id: 'p1', name: 'ESP32 IoT Sensor', user: 'John Doe', status: 'active', layers: 2, components: 24, updated: '2 hours ago' },
  { id: 'p2', name: 'STM32 Motor Controller', user: 'Sarah Kim', status: 'active', layers: 4, components: 67, updated: '1 day ago' },
  { id: 'p3', name: 'USB-C Power Delivery', user: 'Mike Chen', status: 'inactive', layers: 4, components: 42, updated: '3 days ago' },
];

const STATS = [
  { label: 'Total Users', value: '10,234', change: '+12%', icon: Users },
  { label: 'Active Users', value: '8,567', change: '+8%', icon: User },
  { label: 'Total Projects', value: '45,678', change: '+15%', icon: FolderOpen },
  { label: 'Revenue', value: '$45.2K', change: '+25%', icon: CreditCard },
];

const TABS = [
  { id: 'users', label: 'Users', icon: Users },
  { id: 'projects', label: 'Projects', icon: FolderOpen },
  { id: 'reports', label: 'Reports', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function AdminPanel() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('users');
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="min-h-screen bg-background-tertiary">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background-secondary border-b border-border">
        <div className="flex items-center justify-between px-6 h-16">
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
                <Zap className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-semibold text-foreground">PCB Builder</span>
            </Link>
            <span className="text-slate-400">/</span>
            <span className="font-medium text-slate-700">Admin</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm">
              <Mail className="h-4 w-4 mr-2" /> Email All
            </Button>
            <Button variant="outline" size="sm">
              <Bell className="h-4 w-4" />
            </Button>
            <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center text-sm font-medium">
              A
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-background-secondary border-r border-border min-h-screen p-4">
          <div className="space-y-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-foreground-secondary hover:bg-background-tertiary'
                }`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </button>
            ))}
          </div>

          <div className="mt-8 pt-8 border-t border-border">
            <div className="text-xs font-medium text-slate-400 uppercase mb-3">Quick Stats</div>
            <div className="space-y-2">
              {STATS.slice(0, 2).map((stat) => (
                <div key={stat.label} className="flex items-center justify-between text-sm">
                  <span className="text-foreground-secondary">{stat.label}</span>
                  <span className="font-medium text-foreground">{stat.value}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-4 gap-4 mb-8">
            {STATS.map((stat) => (
              <Card key={stat.label} className="bg-background-secondary border-border">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <stat.icon className="h-5 w-5 text-slate-400" />
                    <Badge variant="success" className="text-xs">{stat.change}</Badge>
                  </div>
                  <div className="text-2xl font-semibold text-foreground">{stat.value}</div>
                  <div className="text-sm text-slate-500">{stat.label}</div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Content */}
          {activeTab === 'users' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="relative w-80">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input
                    placeholder="Search users..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Button className="bg-blue-600">
                  <Plus className="h-4 w-4 mr-2" /> Add User
                </Button>
              </div>

              <Card className="bg-background-secondary border-border">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">User</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Plan</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Projects</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Joined</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Status</th>
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {ALL_USERS.map((user) => (
                      <tr key={user.id} className="border-b border-slate-100">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center text-sm font-medium">
                              {user.name.charAt(0)}
                            </div>
                            <div>
                              <div className="font-medium text-foreground">{user.name}</div>
                              <div className="text-xs text-slate-500">{user.email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={user.plan === 'pro' ? 'default' : user.plan === 'team' ? 'info' : 'secondary'}>
                            {user.plan}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-sm text-foreground-secondary">{user.projects}</td>
                        <td className="px-4 py-3 text-sm text-foreground-secondary">{user.joined}</td>
                        <td className="px-4 py-3">
                          {user.active ? (
                            <Badge variant="success" className="text-xs">Active</Badge>
                          ) : (
                            <Badge variant="secondary" className="text-xs">Inactive</Badge>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          )}

          {activeTab === 'projects' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="relative w-80">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input placeholder="Search projects..." className="pl-10" />
                </div>
              </div>

              <Card className="bg-background-secondary border-border">
                <table className="w-full">
                  <thead className="border-b border-border">
                    <tr>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Project</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Owner</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Layers</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Components</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Updated</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ALL_PROJECTS.map((project) => (
                      <tr key={project.id} className="border-b border-slate-100">
                        <td className="px-4 py-3 font-medium text-foreground">{project.name}</td>
                        <td className="px-4 py-3 text-sm text-foreground-secondary">{project.user}</td>
                        <td className="px-4 py-3 text-sm text-foreground-secondary">{project.layers}</td>
                        <td className="px-4 py-3 text-sm text-foreground-secondary">{project.components}</td>
                        <td className="px-4 py-3 text-sm text-foreground-secondary">{project.updated}</td>
                        <td className="px-4 py-3">
                          <Badge variant={project.status === 'active' ? 'success' : 'secondary'}>
                            {project.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          )}

          {activeTab === 'reports' && (
            <Card className="bg-background-secondary border-border">
              <CardContent className="p-8 text-center">
                <BarChart3 className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="font-medium text-foreground mb-2">Reports Coming Soon</h3>
                <p className="text-slate-500">Analytics and reporting features are under development.</p>
              </CardContent>
            </Card>
          )}

          {activeTab === 'settings' && (
            <Card className="bg-background-secondary border-border">
              <CardContent className="p-8 text-center">
                <Settings className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                <h3 className="font-medium text-foreground mb-2">Settings Coming Soon</h3>
                <p className="text-slate-500">Admin settings and configuration are under development.</p>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </div>
  );
}