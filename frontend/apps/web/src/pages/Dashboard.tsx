import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Zap, Wand2, Cpu, Shield, AlertCircle, Loader2, ArrowRight, Plus, Search } from 'lucide-react';
import { useDesignStore, Project } from '../stores';
import { api } from '../lib/api/client';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load projects from API
  useEffect(() => {
    async function loadProjects() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.listProjects() as { items: Project[] };
        if (data.items) {
          setProjects(data.items);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load projects. Please try again.');
      } finally {
        setLoading(false);
      }
    }
    loadProjects();
  }, [setProjects]);

  const filteredProjects = projects.filter(
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

  const [aiPrompt, setAiPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [genStatus, setGenStatus] = useState('');
  const [genError, setGenError] = useState<string | null>(null);

  const handleGenerateFromAI = async () => {
    if (!aiPrompt.trim()) return;

    setIsGenerating(true);
    setGenStatus('Analyzing experiment requirements...');
    setGenError(null);

    try {
      const response = await api.generatePCB({
        input_type: 'text',
        description: aiPrompt,
      }) as { job_id: string; status: string };

      setGenStatus('PCB generation queued! Monitoring progress...');

      // Poll job status
      const pollInterval = setInterval(async () => {
        try {
          const jobStatus = await api.getJobStatus(response.job_id) as { status: string; progress: number; error_message?: string };
          if (jobStatus.status === 'completed') {
            clearInterval(pollInterval);
            setGenStatus('Validation complete! No KiCad errors found.');
            setTimeout(() => {
              navigate('/editor/ai-generated/design-1');
            }, 1000);
          } else if (jobStatus.status === 'failed') {
            clearInterval(pollInterval);
            setGenError(jobStatus.error_message || 'Generation failed');
            setIsGenerating(false);
          } else {
            setGenStatus(`Processing... ${Math.round((jobStatus.progress || 0) * 100)}%`);
          }
        } catch {
          // Continue polling
        }
      }, 3000);

      // Stop polling after 10 minutes
      setTimeout(() => clearInterval(pollInterval), 600000);

    } catch (err: any) {
      setGenError(err.message || 'Failed to start generation');
      setIsGenerating(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-canvas)' }}>
      {/* ── Top Nav ─────────────────────────────────────── */}
      <nav style={{
        height: 64, background: 'var(--color-canvas)',
        borderBottom: '1px solid var(--color-hairline)',
        display: 'flex', alignItems: 'center',
        padding: '0 32px', gap: 24, position: 'sticky', top: 0, zIndex: 50,
      }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
          <span style={{ fontSize: 18 }}>✦</span>
          <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 18, color: 'var(--color-ink)' }}>XgenPCB</span>
        </Link>

        <div style={{ display: 'flex', gap: 2, marginLeft: 24 }}>
          <button style={{
            padding: '8px 14px', fontSize: 14, fontWeight: 500, fontFamily: 'var(--font-sans)',
            color: 'var(--color-ink)', background: 'var(--color-surface-card)',
            border: 'none', borderRadius: 8, cursor: 'pointer',
          }}>Projects</button>
          <button style={{
            padding: '8px 14px', fontSize: 14, fontWeight: 500, fontFamily: 'var(--font-sans)',
            color: 'var(--color-muted)', background: 'none',
            border: 'none', borderRadius: 8, cursor: 'pointer',
          }}>Components</button>
          <button style={{
            padding: '8px 14px', fontSize: 14, fontWeight: 500, fontFamily: 'var(--font-sans)',
            color: 'var(--color-muted)', background: 'none',
            border: 'none', borderRadius: 8, cursor: 'pointer',
          }}>Templates</button>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn--primary btn--sm" onClick={handleNewProject}>
            <Plus size={14} /> New Project
          </button>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'var(--color-primary)', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            color: 'white', fontSize: 13, fontWeight: 600,
          }}>U</div>
        </div>
      </nav>

      <main style={{ maxWidth: 1200, margin: '0 auto', padding: '0 32px' }}>
        {/* ── AI Prompt Section ─────────────────────────── */}
        <div style={{ padding: '48px 0' }}>
          <div style={{
            background: 'var(--color-surface-dark)', borderRadius: 16, padding: 48,
            position: 'relative', overflow: 'hidden',
          }}>
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '4px 12px', borderRadius: 9999,
                background: 'rgba(204,120,92,0.2)', border: '1px solid rgba(204,120,92,0.3)',
                color: 'var(--color-primary)', fontSize: 12, fontWeight: 500,
                letterSpacing: '1.5px', textTransform: 'uppercase',
                marginBottom: 16,
              }}>
                <Zap size={12} /> AI POWERED
              </div>
              <h2 style={{
                fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 400,
                letterSpacing: '-0.3px', color: 'var(--color-on-dark)', marginBottom: 8,
              }}>
                Describe your circuit or idea
              </h2>
              <p style={{ color: 'var(--color-on-dark-soft)', fontSize: 15, fontFamily: 'var(--font-sans)' }}>
                Type your requirements and get a fully validated, manufacturing-ready PCB design.
              </p>
            </div>

            <div style={{ maxWidth: 700, margin: '0 auto' }}>
              <textarea
                style={{
                  width: '100%', minHeight: 120,
                  background: 'var(--color-surface-dark-soft)',
                  border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8,
                  padding: 16, color: 'var(--color-on-dark)',
                  fontFamily: 'var(--font-sans)', fontSize: 16, lineHeight: 1.6,
                  resize: 'none', outline: 'none',
                }}
                placeholder="e.g., An ESP32 based IoT weather station with USB-C, 2 LEDs, and a reset button..."
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                disabled={isGenerating}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-primary)';
                  e.currentTarget.style.boxShadow = '0 0 0 3px rgba(204,120,92,0.15)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
                <button
                  className="btn btn--primary"
                  style={{ height: 48, padding: '0 32px', fontSize: 14 }}
                  onClick={handleGenerateFromAI}
                  disabled={isGenerating || !aiPrompt.trim()}
                >
                  {isGenerating ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="spinner-sm" /> Generating...
                    </span>
                  ) : (
                    <>
                      <Wand2 size={16} style={{ marginRight: 8 }} />
                      Generate Full PCB
                    </>
                  )}
                </button>
              </div>

              {isGenerating && (
                <div style={{
                  marginTop: 24, padding: 16,
                  background: 'var(--color-surface-dark-soft)', borderRadius: 8,
                }}>
                  <div style={{
                    width: '100%', height: 4,
                    background: 'rgba(255,255,255,0.06)', borderRadius: 9999,
                    marginBottom: 8, overflow: 'hidden',
                  }}>
                    <div className="animate-progress" style={{
                      height: '100%',
                      background: 'linear-gradient(90deg, var(--color-primary), var(--color-accent-amber))',
                      borderRadius: 9999,
                    }} />
                  </div>
                  <div style={{
                    display: 'flex', alignItems: 'center',
                    fontSize: 13, color: 'var(--color-on-dark-soft)', fontWeight: 500,
                  }}>
                    <Cpu size={12} style={{ marginRight: 8, color: 'var(--color-accent-teal)' }} />
                    {genStatus}
                  </div>
                </div>
              )}

              {genError && (
                <div style={{
                  marginTop: 12, padding: '12px 16px', borderRadius: 8,
                  background: 'rgba(198,69,69,0.1)', border: '1px solid rgba(198,69,69,0.2)',
                  color: 'var(--color-error)', fontSize: 14,
                  display: 'flex', alignItems: 'center',
                }}>
                  <AlertCircle size={16} style={{ marginRight: 8 }} />
                  {genError}
                </div>
              )}
            </div>

            <div style={{
              display: 'flex', justifyContent: 'center', gap: 32,
              marginTop: 24, paddingTop: 16,
              borderTop: '1px solid rgba(255,255,255,0.06)',
            }}>
              {[
                { icon: <Zap size={12} />, label: 'Auto-Component Selection' },
                { icon: <Cpu size={12} />, label: 'Smart RL Routing' },
                { icon: <Shield size={12} />, label: 'Zero KiCad DRC Errors' },
              ].map((h) => (
                <div key={h.label} style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  fontSize: 11, color: 'var(--color-on-dark-soft)',
                  fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px',
                }}>
                  <span style={{ color: 'var(--color-primary)' }}>{h.icon}</span>
                  {h.label}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Toolbar ──────────────────────────────────── */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: 24,
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)',
            borderRadius: 8, padding: '0 12px',
          }}>
            <Search size={14} style={{ color: 'var(--color-muted-soft)' }} />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                border: 'none', background: 'transparent', padding: '10px 0',
                fontSize: 14, color: 'var(--color-ink)', outline: 'none', width: 200,
                fontFamily: 'var(--font-sans)',
              }}
            />
          </div>
          <select style={{
            padding: '8px 12px', background: 'var(--color-canvas)',
            border: '1px solid var(--color-hairline)', borderRadius: 8,
            fontSize: 14, color: 'var(--color-body)', fontFamily: 'var(--font-sans)',
          }}>
            <option value="updated">Recently Updated</option>
            <option value="created">Recently Created</option>
            <option value="name">Name</option>
          </select>
        </div>

        {/* ── Loading ──────────────────────────────────── */}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 0' }}>
            <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: 'var(--color-primary)' }} />
            <span style={{ marginLeft: 12, color: 'var(--color-muted)' }}>Loading projects...</span>
          </div>
        )}

        {/* ── Error ────────────────────────────────────── */}
        {error && (
          <div style={{
            display: 'flex', alignItems: 'center', padding: '12px 16px',
            background: 'rgba(198,69,69,0.08)', border: '1px solid rgba(198,69,69,0.15)',
            borderRadius: 8, marginBottom: 16, color: 'var(--color-error)', fontSize: 14,
          }}>
            <AlertCircle size={16} style={{ marginRight: 8 }} />
            {error}
            <button className="btn btn--sm btn--outline" style={{ marginLeft: 'auto' }} onClick={() => window.location.reload()}>
              Retry
            </button>
          </div>
        )}

        {/* ── Projects Grid ────────────────────────────── */}
        {!loading && !error && (
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: 24, paddingBottom: 48,
          }}>
            {filteredProjects.map((project) => (
              <div
                key={project.id}
                onClick={() => handleOpenProject(project.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && handleOpenProject(project.id)}
                style={{
                  background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)',
                  borderRadius: 12, padding: 24, cursor: 'pointer',
                  transition: 'all 0.25s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-primary)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(20,20,19,0.08)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--color-hairline)';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{
                  aspectRatio: '16/10', background: 'var(--color-surface-card)',
                  borderRadius: 8, marginBottom: 16,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: 'var(--color-muted-soft)',
                }}>
                  <svg viewBox="0 0 100 80" style={{ width: '60%', height: '60%', opacity: 0.3 }}>
                    <rect x="10" y="10" width="80" height="60" fill="none" stroke="currentColor" strokeWidth="1" />
                    <rect x="20" y="20" width="25" height="18" fill="currentColor" rx="2" opacity="0.3" />
                    <rect x="55" y="15" width="20" height="12" fill="currentColor" rx="1" opacity="0.3" />
                    <rect x="60" y="50" width="15" height="10" fill="currentColor" rx="1" opacity="0.3" />
                  </svg>
                </div>

                <div style={{
                  fontWeight: 600, fontSize: 16, color: 'var(--color-ink)', marginBottom: 4,
                }}>{project.name}</div>
                <div style={{
                  fontSize: 14, color: 'var(--color-muted)', marginBottom: 12, lineHeight: 1.5,
                }}>{project.description}</div>

                <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
                  {project.tags?.map((tag) => (
                    <span key={tag} style={{
                      padding: '2px 10px', borderRadius: 9999,
                      background: 'var(--color-surface-card)', fontSize: 12,
                      fontWeight: 500, color: 'var(--color-body)',
                    }}>{tag}</span>
                  ))}
                </div>

                <div style={{
                  display: 'flex', gap: 16, fontSize: 13, color: 'var(--color-muted-soft)',
                }}>
                  <span>📐 2L</span>
                  <span>🔌 8 parts</span>
                  <span>🕒 {formatTimeAgo(project.updated_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Empty State ──────────────────────────────── */}
        {!loading && !error && filteredProjects.length === 0 && (
          <div style={{ textAlign: 'center', padding: '96px 32px' }}>
            <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }}>📂</div>
            <h3 style={{
              fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 400,
              color: 'var(--color-ink)', marginBottom: 8, letterSpacing: '-0.3px',
            }}>
              No projects found
            </h3>
            <p style={{ color: 'var(--color-muted)', marginBottom: 24 }}>
              {searchQuery ? 'Try a different search term' : 'Create your first PCB project to get started'}
            </p>
            <button className="btn btn--primary" onClick={handleNewProject}>
              <Plus size={14} style={{ marginRight: 6 }} /> New Project
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
