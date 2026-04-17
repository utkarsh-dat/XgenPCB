import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDesignStore } from '../stores';

const SAMPLE_PROJECTS = [
  {
    id: 'proj-1',
    name: 'ESP32 IoT Sensor Board',
    description: 'WiFi-enabled environmental sensor with temperature, humidity, and air quality monitoring',
    tags: ['IoT', 'ESP32', 'Sensors'],
    updated_at: '2 hours ago',
    layers: 2,
    components: 24,
  },
  {
    id: 'proj-2',
    name: 'STM32 Motor Controller',
    description: 'Dual H-bridge motor driver with CAN bus interface and current sensing',
    tags: ['Motor Control', 'STM32', 'Power'],
    updated_at: '1 day ago',
    layers: 4,
    components: 67,
  },
  {
    id: 'proj-3',
    name: 'USB-C Power Delivery Board',
    description: 'PD 3.1 compliant power supply with 5V-48V output and e-marker cable support',
    tags: ['USB-C', 'Power Delivery'],
    updated_at: '3 days ago',
    layers: 4,
    components: 42,
  },
];

export function Dashboard() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const filteredProjects = SAMPLE_PROJECTS.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleOpenProject = (projectId: string) => {
    navigate(`/editor/${projectId}/design-1`);
  };

  const handleNewProject = () => {
    navigate('/editor/new/design-1');
  };

  return (
    <div className="app-layout">
      {/* Top Navigation */}
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
          <button className="btn btn--ghost btn--icon" id="btn-notifications" title="Notifications">
            🔔
          </button>
          <button className="btn btn--ghost btn--icon" id="btn-settings" title="Settings">
            ⚙️
          </button>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: 'var(--gradient-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
              fontWeight: 700,
              color: 'white',
              cursor: 'pointer',
            }}
            id="btn-avatar"
          >
            U
          </div>
        </div>
      </nav>

      {/* Dashboard Content */}
      <div className="dashboard">
        <div className="dashboard__hero">
          <h1 className="dashboard__title">Design. Build. Ship.</h1>
          <p className="dashboard__subtitle">
            AI-powered PCB design platform with real-time DRC, automated routing,
            and instant fabrication quotes from top manufacturers.
          </p>
          <div style={{ display: 'flex', gap: 'var(--space-md)', justifyContent: 'center', marginTop: 'var(--space-lg)' }}>
            <input
              className="input"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ maxWidth: 400 }}
              id="search-projects"
            />
          </div>
        </div>

        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-lg)' }}>
            <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 600 }}>Recent Projects</h2>
            <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
              <span className="badge badge--info">{SAMPLE_PROJECTS.length} projects</span>
            </div>
          </div>

          <div className="dashboard__grid">
            {/* New Project Card */}
            <div className="project-card project-card--new" onClick={handleNewProject} id="card-new-project">
              <span className="plus-icon">+</span>
              <span style={{ fontWeight: 500 }}>Create New Project</span>
              <span style={{ fontSize: 'var(--font-size-xs)' }}>Start from scratch or use a template</span>
            </div>

            {/* Project Cards */}
            {filteredProjects.map((project) => (
              <div
                key={project.id}
                className="project-card"
                onClick={() => handleOpenProject(project.id)}
                id={`card-${project.id}`}
              >
                {/* PCB Preview Thumbnail */}
                <div
                  style={{
                    width: '100%',
                    height: 120,
                    background: `linear-gradient(135deg, ${
                      project.layers <= 2
                        ? 'rgba(26, 95, 42, 0.3), rgba(26, 95, 42, 0.1)'
                        : 'rgba(0, 102, 51, 0.3), rgba(0, 60, 30, 0.1)'
                    })`,
                    borderRadius: 'var(--radius-md)',
                    marginBottom: 'var(--space-md)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  {/* Fake PCB traces */}
                  <svg width="100%" height="100%" style={{ position: 'absolute', opacity: 0.4 }}>
                    <line x1="20" y1="30" x2="120" y2="30" stroke="var(--pcb-copper)" strokeWidth="2" />
                    <line x1="50" y1="20" x2="50" y2="80" stroke="var(--pcb-copper)" strokeWidth="1.5" />
                    <line x1="80" y1="40" x2="160" y2="40" stroke="var(--pcb-copper)" strokeWidth="2" />
                    <line x1="30" y1="60" x2="140" y2="60" stroke="var(--pcb-copper)" strokeWidth="1" />
                    <circle cx="50" cy="30" r="3" fill="var(--pcb-copper)" />
                    <circle cx="120" cy="30" r="3" fill="var(--pcb-copper)" />
                    <circle cx="80" cy="60" r="4" fill="var(--pcb-copper)" />
                    <rect x="90" y="70" width="20" height="15" fill="rgba(100,100,100,0.3)" rx="2" />
                    <rect x="30" y="80" width="15" height="10" fill="rgba(100,100,100,0.3)" rx="1" />
                  </svg>
                  <span style={{ zIndex: 1, fontSize: '24px', opacity: 0.6 }}>🔧</span>
                </div>

                <div className="project-card__name">{project.name}</div>
                <div className="project-card__desc">{project.description}</div>

                <div style={{ display: 'flex', gap: 'var(--space-xs)', marginBottom: 'var(--space-md)', flexWrap: 'wrap' }}>
                  {project.tags.map((tag) => (
                    <span key={tag} className="badge badge--info">{tag}</span>
                  ))}
                </div>

                <div className="project-card__meta">
                  <span>📐 {project.layers}L</span>
                  <span>🔌 {project.components} parts</span>
                  <span>🕒 {project.updated_at}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
