import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Zap,
  Layers,
  Cpu,
  Shield,
  Clock,
  Users,
  ArrowRight,
  CheckCircle2,
  Menu,
  X,
  Terminal,
  Sparkles,
  Box,
  FileOutput,
} from 'lucide-react';

const FEATURES = [
  {
    icon: Sparkles,
    title: 'Prompt-to-PCB',
    description: 'Describe your circuit in plain English. Our 6-stage AI pipeline converts intent into a fully validated, manufacturable board.',
  },
  {
    icon: Layers,
    title: 'Multi-Layer Intelligence',
    description: 'Up to 16-layer boards with automatic impedance-controlled stackup and IPC-compliant design rules.',
  },
  {
    icon: Cpu,
    title: 'Smart Component Selection',
    description: 'Access 30K+ footprints with real-time JLCPCB and LCSC pricing, stock levels, and datasheet links.',
  },
  {
    icon: Shield,
    title: 'Physics-Aware Validation',
    description: 'DRC, DFM, and signal integrity analysis against IPC Class 1/2/3 standards — zero errors before export.',
  },
  {
    icon: Clock,
    title: 'Instant Manufacturing',
    description: 'One-click Gerber export with instant quotes from JLCPCB, PCBWay, and more. Ship boards same-week.',
  },
  {
    icon: Users,
    title: 'Team Collaboration',
    description: 'Real-time multiplayer editing, version history snapshots, and team workspaces with SSO support.',
  },
];

const PIPELINE_STAGES = [
  { num: '0', name: 'Intent Parser', desc: 'NLP → structured requirements' },
  { num: '1', name: 'Schematic Agent', desc: 'Requirements → netlist + ERC' },
  { num: '2', name: 'Placement Agent', desc: 'Netlist → optimal component layout' },
  { num: '3', name: 'Routing Agent', desc: 'Layout → RL-powered trace routing' },
  { num: '4', name: 'Validation Agent', desc: 'DRC + DFM + signal integrity' },
  { num: '5', name: 'Output Agent', desc: 'KiCad + Gerber + BOM + quotes' },
];

const PRICING_TIERS = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'For learning and hobby projects',
    features: ['3 projects', '2-layer boards', '10 AI generations/month', '100MB storage', 'Community support'],
    cta: 'Start Free',
    featured: false,
  },
  {
    name: 'Pro',
    price: '$29',
    period: '/month',
    description: 'For engineers shipping production boards',
    features: ['Unlimited projects', '6-layer boards', '100 AI generations/month', '1GB storage', 'Priority support', 'Team collaboration (2 seats)', 'All export formats'],
    cta: 'Start Building',
    featured: true,
  },
  {
    name: 'Team',
    price: '$99',
    period: '/month',
    description: 'For teams and organizations',
    features: ['Everything in Pro', '16-layer boards', 'Unlimited AI generations', '10GB storage', '20 team seats', 'SSO & SAML', 'Custom part libraries'],
    cta: 'Contact Sales',
    featured: false,
  },
];

const STATS = [
  { value: '10,000+', label: 'Engineers' },
  { value: '50,000+', label: 'Designs Generated' },
  { value: '<5 min', label: 'Avg Generation Time' },
  { value: '99.9%', label: 'Uptime' },
];

export function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-canvas)' }}>
      {/* ── Top Nav ──────────────────────────────────────── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        height: 64, background: 'var(--color-canvas)',
        borderBottom: '1px solid var(--color-hairline)',
        display: 'flex', alignItems: 'center',
        padding: '0 32px', justifyContent: 'space-between',
      }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
          <span style={{ fontSize: 20 }}>✦</span>
          <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 18, color: 'var(--color-ink)', letterSpacing: '-0.01em' }}>XgenPCB</span>
        </Link>

        <div style={{ display: 'flex', alignItems: 'center', gap: 32 }} className="desktop-nav">
          <Link to="/dashboard" style={{ fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 500, color: 'var(--color-muted)', textDecoration: 'none' }}>Dashboard</Link>
          <Link to="/pricing" style={{ fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 500, color: 'var(--color-muted)', textDecoration: 'none' }}>Pricing</Link>
          <Link to="/templates" style={{ fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 500, color: 'var(--color-muted)', textDecoration: 'none' }}>Templates</Link>
          <Link to="/community" style={{ fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 500, color: 'var(--color-muted)', textDecoration: 'none' }}>Community</Link>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }} className="desktop-nav">
          <Link to="/dashboard" style={{ fontFamily: 'var(--font-sans)', fontSize: 14, fontWeight: 500, color: 'var(--color-ink)', textDecoration: 'none' }}>Sign in</Link>
          <button className="btn btn--primary" onClick={() => navigate('/dashboard')}>
            Try XgenPCB <ArrowRight style={{ width: 14, height: 14, marginLeft: 6 }} />
          </button>
        </div>

        <button
          style={{ display: 'none', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink)' }}
          className="mobile-menu-btn"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </nav>

      {/* ── Hero Band ───────────────────────────────────── */}
      <section style={{ padding: '96px 32px', background: 'var(--color-canvas)' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64, alignItems: 'center' }}>
          {/* Left: Copy */}
          <div>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '4px 12px', borderRadius: 9999,
              background: 'rgba(204,120,92,0.1)', color: 'var(--color-primary)',
              fontSize: 12, fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase',
              marginBottom: 24,
            }}>
              <Sparkles size={12} /> PUBLIC BETA
            </div>

            <h1 style={{
              fontFamily: 'var(--font-display)', fontSize: 64, fontWeight: 400,
              lineHeight: 1.05, letterSpacing: '-1.5px', color: 'var(--color-ink)',
              marginBottom: 24,
            }}>
              Prompt to PCB,<br />fully autonomous
            </h1>

            <p style={{
              fontFamily: 'var(--font-sans)', fontSize: 18, fontWeight: 400,
              lineHeight: 1.5, color: 'var(--color-body)', marginBottom: 32, maxWidth: 480,
            }}>
              Describe your circuit in plain English. XgenPCB's 6-stage AI pipeline generates a
              physics-validated, manufacturing-ready board in minutes — not days.
            </p>

            <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
              <button className="btn btn--primary btn--lg" onClick={() => navigate('/dashboard')}>
                Start Building Free <ArrowRight size={16} style={{ marginLeft: 8 }} />
              </button>
              <button className="btn btn--secondary btn--lg">
                <Terminal size={16} style={{ marginRight: 8 }} /> View Pipeline
              </button>
            </div>

            <p style={{ fontFamily: 'var(--font-sans)', fontSize: 14, color: 'var(--color-muted-soft)' }}>
              No credit card required · 3 free projects · NVIDIA NIM powered
            </p>
          </div>

          {/* Right: Code Window Mockup */}
          <div style={{
            background: 'var(--color-surface-dark)', borderRadius: 16, padding: 0,
            overflow: 'hidden',
          }}>
            {/* Title Bar */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '12px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)',
            }}>
              <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#c64545' }} />
              <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#d4a017' }} />
              <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#5db872' }} />
              <span style={{ marginLeft: 12, fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--color-on-dark-soft)' }}>xgenpcb — AI Pipeline</span>
            </div>
            {/* Code Content */}
            <div style={{
              padding: '24px 20px', fontFamily: 'var(--font-mono)', fontSize: 13,
              lineHeight: 1.7, color: 'var(--color-on-dark-soft)',
            }}>
              <div><span style={{ color: 'var(--color-muted-soft)' }}>$</span> <span style={{ color: 'var(--color-on-dark)' }}>xgenpcb generate</span></div>
              <div style={{ color: 'var(--color-accent-teal)' }}>✓ Stage 0: Intent parsed (confidence: 0.94)</div>
              <div style={{ color: 'var(--color-accent-teal)' }}>✓ Stage 1: Schematic generated (12 nets, 0 ERC errors)</div>
              <div style={{ color: 'var(--color-accent-teal)' }}>✓ Stage 2: Components placed (8 parts, thermal OK)</div>
              <div style={{ color: 'var(--color-accent-teal)' }}>✓ Stage 3: Routes completed (100% nets, 0 DRC)</div>
              <div style={{ color: 'var(--color-accent-teal)' }}>✓ Stage 4: Validation passed (DFM: 92, SI: 88)</div>
              <div style={{ color: 'var(--color-accent-teal)' }}>✓ Stage 5: Output ready</div>
              <div style={{ marginTop: 12 }}>
                <span style={{ color: 'var(--color-primary)' }}>→</span>
                <span style={{ color: 'var(--color-on-dark)' }}> esp32_iot_board.kicad_pcb</span>
                <span style={{ color: 'var(--color-on-dark-soft)' }}> (50×50mm, 2L, 8 components)</span>
              </div>
              <div>
                <span style={{ color: 'var(--color-primary)' }}>→</span>
                <span style={{ color: 'var(--color-on-dark)' }}> gerber_files.zip</span>
                <span style={{ color: 'var(--color-on-dark-soft)' }}> (JLCPCB-ready)</span>
              </div>
              <div style={{ marginTop: 8 }}>
                <span style={{ color: 'var(--color-accent-amber)' }}>⚡</span>
                <span style={{ color: 'var(--color-on-dark-soft)' }}> Generated in 3m 42s</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats Band ──────────────────────────────────── */}
      <section style={{
        padding: '48px 32px', background: 'var(--color-surface-soft)',
        borderTop: '1px solid var(--color-hairline)',
        borderBottom: '1px solid var(--color-hairline)',
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', justifyContent: 'center', gap: 80 }}>
          {STATS.map((s) => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div style={{
                fontFamily: 'var(--font-display)', fontSize: 36, fontWeight: 400,
                letterSpacing: '-0.5px', color: 'var(--color-ink)', marginBottom: 4,
              }}>{s.value}</div>
              <div style={{ fontFamily: 'var(--font-sans)', fontSize: 14, color: 'var(--color-muted)' }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features Grid ───────────────────────────────── */}
      <section style={{ padding: '96px 32px', background: 'var(--color-canvas)' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <h2 style={{
              fontFamily: 'var(--font-display)', fontSize: 48, fontWeight: 400,
              lineHeight: 1.1, letterSpacing: '-1px', color: 'var(--color-ink)', marginBottom: 16,
            }}>
              Everything you need to ship boards
            </h2>
            <p style={{
              fontFamily: 'var(--font-sans)', fontSize: 18, color: 'var(--color-muted)',
              maxWidth: 560, margin: '0 auto',
            }}>
              Professional-grade PCB automation powered by NVIDIA NIM and physics-aware validation.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
            {FEATURES.map((f) => (
              <div key={f.title} style={{
                background: 'var(--color-surface-card)', borderRadius: 12, padding: 32,
                transition: 'transform 0.25s ease',
              }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-3px)')}
                onMouseLeave={(e) => (e.currentTarget.style.transform = 'translateY(0)')}
              >
                <div style={{
                  width: 40, height: 40, borderRadius: 8,
                  background: 'var(--color-canvas)', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', marginBottom: 16,
                }}>
                  <f.icon size={20} style={{ color: 'var(--color-primary)' }} />
                </div>
                <h3 style={{
                  fontFamily: 'var(--font-sans)', fontSize: 18, fontWeight: 500,
                  color: 'var(--color-ink)', marginBottom: 8,
                }}>{f.title}</h3>
                <p style={{
                  fontFamily: 'var(--font-sans)', fontSize: 16, color: 'var(--color-body)',
                  lineHeight: 1.55,
                }}>{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pipeline Section (Dark) ─────────────────────── */}
      <section style={{ padding: '96px 32px', background: 'var(--color-surface-dark)' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <h2 style={{
              fontFamily: 'var(--font-display)', fontSize: 48, fontWeight: 400,
              lineHeight: 1.1, letterSpacing: '-1px', color: 'var(--color-on-dark)', marginBottom: 16,
            }}>
              6-stage AI pipeline
            </h2>
            <p style={{ fontFamily: 'var(--font-sans)', fontSize: 18, color: 'var(--color-on-dark-soft)', maxWidth: 560, margin: '0 auto' }}>
              From natural language to manufacturing-ready output. Each stage validates through a specialized gate.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {PIPELINE_STAGES.map((s) => (
              <div key={s.num} style={{
                background: 'var(--color-surface-dark-elevated)', borderRadius: 12, padding: 24,
              }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 500,
                  color: 'var(--color-primary)', marginBottom: 8,
                  letterSpacing: '1.5px', textTransform: 'uppercase',
                }}>
                  STAGE {s.num}
                </div>
                <div style={{
                  fontFamily: 'var(--font-sans)', fontSize: 18, fontWeight: 500,
                  color: 'var(--color-on-dark)', marginBottom: 6,
                }}>{s.name}</div>
                <div style={{
                  fontFamily: 'var(--font-sans)', fontSize: 14, color: 'var(--color-on-dark-soft)',
                  lineHeight: 1.5,
                }}>{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ─────────────────────────────────────── */}
      <section style={{ padding: '96px 32px', background: 'var(--color-canvas)' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <h2 style={{
              fontFamily: 'var(--font-display)', fontSize: 48, fontWeight: 400,
              letterSpacing: '-1px', color: 'var(--color-ink)', marginBottom: 16,
            }}>
              Simple, transparent pricing
            </h2>
            <p style={{ fontSize: 18, color: 'var(--color-muted)' }}>Start free, upgrade when you're ready.</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
            {PRICING_TIERS.map((t) => (
              <div key={t.name} style={{
                background: t.featured ? 'var(--color-surface-dark)' : 'var(--color-canvas)',
                color: t.featured ? 'var(--color-on-dark)' : 'var(--color-ink)',
                border: t.featured ? 'none' : '1px solid var(--color-hairline)',
                borderRadius: 12, padding: 32, position: 'relative',
              }}>
                {t.featured && (
                  <div style={{
                    position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                    padding: '4px 12px', borderRadius: 9999,
                    background: 'var(--color-primary)', color: 'var(--color-on-primary)',
                    fontSize: 12, fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase',
                  }}>
                    MOST POPULAR
                  </div>
                )}
                <h3 style={{ fontFamily: 'var(--font-sans)', fontSize: 22, fontWeight: 500, marginBottom: 4 }}>{t.name}</h3>
                <p style={{ fontSize: 14, color: t.featured ? 'var(--color-on-dark-soft)' : 'var(--color-muted)', marginBottom: 16 }}>{t.description}</p>
                <div style={{ marginBottom: 24 }}>
                  <span style={{ fontFamily: 'var(--font-display)', fontSize: 36, fontWeight: 400, letterSpacing: '-0.5px' }}>{t.price}</span>
                  <span style={{ fontSize: 14, color: t.featured ? 'var(--color-on-dark-soft)' : 'var(--color-muted)' }}>{t.period}</span>
                </div>
                <ul style={{ listStyle: 'none', marginBottom: 24 }}>
                  {t.features.map((f) => (
                    <li key={f} style={{
                      display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
                      fontSize: 14, color: t.featured ? 'var(--color-on-dark-soft)' : 'var(--color-body)',
                    }}>
                      <CheckCircle2 size={16} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  className={t.featured ? 'btn btn--primary' : 'btn btn--secondary'}
                  style={{ width: '100%' }}
                  onClick={() => navigate('/dashboard')}
                >
                  {t.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Band (Coral) ────────────────────────────── */}
      <section style={{
        margin: '0 32px 32px', padding: 64, borderRadius: 12,
        background: 'var(--color-primary)', textAlign: 'center',
      }}>
        <h2 style={{
          fontFamily: 'var(--font-display)', fontSize: 36, fontWeight: 400,
          letterSpacing: '-0.5px', color: 'var(--color-on-primary)', marginBottom: 12,
        }}>
          Ready to automate your PCB workflow?
        </h2>
        <p style={{ fontSize: 18, color: 'rgba(255,255,255,0.85)', marginBottom: 32 }}>
          Join 10,000+ engineers who've shipped boards with XgenPCB.
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
          <button
            className="btn btn--lg"
            style={{ background: 'var(--color-canvas)', color: 'var(--color-primary)', border: 'none' }}
            onClick={() => navigate('/dashboard')}
          >
            Start Building Free <ArrowRight size={16} style={{ marginLeft: 8 }} />
          </button>
          <Link to="/pricing">
            <button className="btn btn--lg" style={{ background: 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.4)' }}>
              View Pricing
            </button>
          </Link>
        </div>
      </section>

      {/* ── Footer (Dark) ───────────────────────────────── */}
      <footer style={{
        background: 'var(--color-surface-dark)', padding: '64px 32px',
        color: 'var(--color-on-dark-soft)',
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr', gap: 48, marginBottom: 48 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <span style={{ fontSize: 18, color: 'var(--color-on-dark)' }}>✦</span>
                <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 18, color: 'var(--color-on-dark)' }}>XgenPCB</span>
              </div>
              <p style={{ fontSize: 14, lineHeight: 1.6, maxWidth: 280 }}>
                AI-powered PCB design automation. From prompt to fabrication-ready board.
              </p>
            </div>
            {[
              { title: 'Product', links: [['Dashboard', '/dashboard'], ['Templates', '/templates'], ['Pricing', '/pricing'], ['Marketplace', '/marketplace']] },
              { title: 'Community', links: [['Forum', '/forum'], ['Design Review', '/design-review/1'], ['Tutorials', '/tutorials']] },
              { title: 'Company', links: [['About', '#'], ['Blog', '#'], ['Careers', '#'], ['Contact', '#']] },
              { title: 'Legal', links: [['Privacy', '#'], ['Terms', '#'], ['Security', '#']] },
            ].map((col) => (
              <div key={col.title}>
                <h4 style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 14, color: 'var(--color-on-dark)', marginBottom: 16 }}>{col.title}</h4>
                <ul style={{ listStyle: 'none' }}>
                  {col.links.map(([label, href]) => (
                    <li key={label} style={{ marginBottom: 8 }}>
                      <Link to={href} style={{ fontSize: 14, color: 'var(--color-on-dark-soft)', textDecoration: 'none' }}>{label}</Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <p style={{ fontSize: 14 }}>© 2026 XgenPCB. All rights reserved.</p>
            <p style={{ fontSize: 14 }}>Made with ♥ for engineers worldwide</p>
          </div>
        </div>
      </footer>

      <style>{`
        @media (max-width: 768px) {
          .desktop-nav { display: none !important; }
          .mobile-menu-btn { display: block !important; }
        }
        @media (max-width: 1024px) {
          section > div[style*="grid-template-columns: 1fr 1fr"] {
            grid-template-columns: 1fr !important;
          }
          section > div > div[style*="grid-template-columns: repeat(3"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
