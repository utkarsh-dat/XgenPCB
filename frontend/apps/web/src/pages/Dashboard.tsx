import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDesignStore, Project } from '../stores';
import { api } from '../lib/api/client';

// Sample projects for when API is unavailable
const SAMPLE_PROJECTS: Project[] = [
  {
    id: 'proj-1',
    name: 'ESP32 IoT Sensor Board',
    description: 'WiFi-enabled environmental sensor with temperature, humidity, and air quality monitoring',
    tags: ['IoT', 'ESP32', 'Sensors'],
    visibility: 'private',
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'proj-2',
    name: 'STM32 Motor Controller',
    description: 'Dual H-bridge motor driver with CAN bus interface and current sensing',
    tags: ['Motor Control', 'STM32', 'Power'],
    visibility: 'private',
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'proj-3',
    name: 'USB-C Power Delivery Board',
    description: 'PD 3.1 compliant power supply with 5V-48V output and e-marker cable support',
    tags: ['USB-C', 'Power Delivery'],
    visibility: 'private',
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function Dashboard() {
  const navigate = useNavigate();
  const { projects, setProjects } = useDesignStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [useSampleData, setUseSampleData] = useState(true);

  // Load projects from API
  useEffect(() => {
    async function loadProjects() {
      try {
        const data = await api.listProjects() as { items: Project[] };
        if (data.items && data.items.length > 0) {
          setProjects(data.items);
          setUseSampleData(false);
        }
      } catch {
        setUseSampleData(true);
      }
    }
    loadProjects();
  }, [setProjects]);

  const displayProjects = useSampleData ? SAMPLE_PROJECTS : projects;

  const filteredProjects = displayProjects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleOpenProject = (projectId: string) => {
    navigate(`/editor/${projectId}/design-1`);
  };

  const handleNewProject = () => {
    navigate('/editor/new/design-1');
  };

  return (
    <div className="app-layout">
      <nav className="topnav">
        <div className="topnav__logo">
          <div className="topnav__logo-icon">⚡</div>
          PCB Builder
        </div>
        <div className="topnav__tabs">
          <button className="topnav__tab topnav__tab--active" id="tab-projects">Projects</button>
          <button className="topnav__tab" id="tab-components">Components</button>
          <button className="topnav__tab" id="tab-templates">Templates</button>
          <button className="topnav__tab" id="tab-community">Community</button>
        </div>
        <div className="topnav__actions">
          <button className="btn btn--primary btn--sm" id="btn-new-project" onClick={handleNewProject}>
            + New Project
          </button>
          <button className="btn btn--ghost btn--icon" id="btn-notifications" title="Notifications">🔔</button>
          <button className="btn btn--ghost btn--icon" id="btn-settings" title="Settings">⚙️</button>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: 'var(--color-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            U
          </div>
        </div>
      </nav>

      <main className="main-content">
        <div className="toolbar">
          <div className="search-box">
            <span className="search-box__icon">🔍</span>
            <input
              type="text"
              className="search-box__input"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="toolbar__actions">
            <select className="select" id="filter-sort">
              <option value="updated">Recently Updated</option>
              <option value="created">Recently Created</option>
              <option value="name">Name</option>
            </select>
          </div>
        </div>

        {useSampleData && (
          <div className="notice notice--info" style={{ marginBottom: 'var(--space-md)' }}>
            <span>ℹ️</span> Using sample data. Connect backend to load your projects.
          </div>
        )}

        <div className="projects-grid">
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              className="project-card"
              onClick={() => handleOpenProject(project.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && handleOpenProject(project.id)}
            >
              <div className="project-card__preview">
                <svg viewBox="0 0 100 80" style={{ width: '100%', height: '100%' }}>
                  <rect x="10" y="10" width="80" height="60" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3" />
                  <rect x="20" y="20" width="25" height="18" fill="rgba(100,100,100,0.3)" rx="2" />
                  <rect x="55" y="15" width="20" height="12" fill="rgba(100,100,100,0.3)" rx="1" />
                  <rect x="60" y="50" width="15" height="10" fill="rgba(100,100,100,0.3)" rx="1" />
                  <rect x="30" y="45" width="10" height="8" fill="rgba(100,100,100,0.3)" rx="1" />
                  <rect x="90" y="70" width="20" height="15" fill="rgba(100,100,100,0.3)" rx="2" />
                  <rect x="30" y="80" width="15" height="10" fill="rgba(100,100,100,0.3)" rx="1" />
                </svg>
                <span style={{ zIndex: 1, fontSize: '24px', opacity: 0.6 }}>🔧</span>
              </div>

              <div className="project-card__name">{project.name}</div>
              <div className="project-card__desc">{project.description}</div>

              <div style={{ display: 'flex', gap: 'var(--space-xs)', marginBottom: 'var(--space-md)', flexWrap: 'wrap' }}>
                {project.tags?.map((tag) => (
                  <span key={tag} className="badge badge--info">{tag}</span>
                ))}
              </div>

              <div className="project-card__meta">
                <span>📐 2L</span>
                <span>🔌 8 parts</span>
                <span>🕒 {formatTimeAgo(project.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>

        {filteredProjects.length === 0 && (
          <div className="empty-state">
            <div className="empty-state__icon">📂</div>
            <h3>No projects found</h3>
            <p>{searchQuery ? 'Try a different search term' : 'Create your first PCB project to get started'}</p>
            <button className="btn btn--primary" onClick={handleNewProject}>
              + New Project
            </button>
          </div>
        )}
      </main>
    </div>
  );
}