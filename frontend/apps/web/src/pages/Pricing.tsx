import { Link, useNavigate } from 'react-router-dom';
import { Check, ArrowRight, Mail } from 'lucide-react';

const PLANS = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'For learning and hobby projects',
    features: ['3 Projects', '2-layer boards', '10 AI generations/month', '100MB storage', 'Basic DRC', 'Community support', 'Export to Gerber'],
    cta: 'Start Free',
    featured: false,
  },
  {
    name: 'Pro',
    price: '$29',
    period: '/month',
    description: 'For engineers shipping production boards',
    features: ['Unlimited projects', '6-layer boards', '100 AI generations/month', '1GB storage', 'Advanced DRC + DFM', 'Priority support', 'Team collaboration (2 seats)', 'All export formats', 'BOM generation', 'Instant quotes'],
    cta: 'Start Building',
    featured: true,
  },
  {
    name: 'Team',
    price: '$99',
    period: '/month',
    description: 'For teams and organizations',
    features: ['Everything in Pro', '16-layer boards', 'Unlimited AI generations', '10GB storage', '20 team seats', 'SSO & SAML', 'Dedicated support', 'Custom part libraries', 'API access', 'Invoice billing'],
    cta: 'Contact Sales',
    featured: false,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For large organizations',
    features: ['Unlimited everything', 'On-premise deployment', 'Custom integrations', 'Dedicated account manager', 'SLA guarantees', 'Training sessions', 'Custom contracts'],
    cta: 'Talk to Sales',
    featured: false,
  },
];

const FAQ = [
  { q: 'Can I cancel anytime?', a: 'Yes, you can cancel your subscription at any time. Your access will continue until the end of your billing period.' },
  { q: 'What payment methods do you accept?', a: 'We accept all major credit cards (Visa, MasterCard, American Express) and PayPal.' },
  { q: 'Can I upgrade or downgrade later?', a: 'Absolutely! You can change your plan at any time from your account settings.' },
  { q: 'Is there a free trial?', a: 'Yes! Pro comes with a 14-day free trial. No credit card required to start.' },
  { q: 'What happens to my projects if I cancel?', a: 'Your projects remain yours. You can export them anytime, even after cancellation.' },
  { q: 'Do you offer student discounts?', a: 'Yes! Contact us with your school email for a 50% discount on Pro.' },
];

export function Pricing() {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-canvas)' }}>
      {/* ── Nav ─────────────────────────────────────────── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 50, height: 64,
        background: 'var(--color-canvas)',
        borderBottom: '1px solid var(--color-hairline)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 32px',
      }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
          <span style={{ fontSize: 18 }}>✦</span>
          <span style={{ fontWeight: 600, fontSize: 18, color: 'var(--color-ink)' }}>XgenPCB</span>
        </Link>
        <button className="btn btn--secondary btn--sm" onClick={() => navigate('/dashboard')}>
          Go to Dashboard
        </button>
      </nav>

      {/* ── Pricing Section ─────────────────────────────── */}
      <section style={{ padding: '96px 32px', background: 'var(--color-canvas)' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <h1 style={{
              fontFamily: 'var(--font-display)', fontSize: 48, fontWeight: 400,
              letterSpacing: '-1px', color: 'var(--color-ink)', marginBottom: 12,
            }}>Simple, transparent pricing</h1>
            <p style={{ fontSize: 18, color: 'var(--color-muted)' }}>Start free, upgrade when you're ready</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20 }}>
            {PLANS.map((plan) => (
              <div key={plan.name} style={{
                background: plan.featured ? 'var(--color-surface-dark)' : 'var(--color-canvas)',
                color: plan.featured ? 'var(--color-on-dark)' : 'var(--color-ink)',
                border: plan.featured ? 'none' : '1px solid var(--color-hairline)',
                borderRadius: 12, padding: 32, position: 'relative',
              }}>
                {plan.featured && (
                  <div style={{
                    position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                    padding: '4px 12px', borderRadius: 9999,
                    background: 'var(--color-primary)', color: 'var(--color-on-primary)',
                    fontSize: 12, fontWeight: 500, letterSpacing: '1px', textTransform: 'uppercase',
                  }}>MOST POPULAR</div>
                )}

                <h3 style={{ fontFamily: 'var(--font-sans)', fontSize: 22, fontWeight: 500, marginBottom: 4 }}>
                  {plan.name}
                </h3>
                <p style={{
                  fontSize: 14, marginBottom: 16,
                  color: plan.featured ? 'var(--color-on-dark-soft)' : 'var(--color-muted)',
                }}>{plan.description}</p>

                <div style={{ marginBottom: 24 }}>
                  <span style={{
                    fontFamily: 'var(--font-display)', fontSize: 36, fontWeight: 400, letterSpacing: '-0.5px',
                  }}>{plan.price}</span>
                  <span style={{
                    fontSize: 14,
                    color: plan.featured ? 'var(--color-on-dark-soft)' : 'var(--color-muted)',
                  }}>{plan.period}</span>
                </div>

                <ul style={{ listStyle: 'none', marginBottom: 24 }}>
                  {plan.features.map((f) => (
                    <li key={f} style={{
                      display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
                      fontSize: 14,
                      color: plan.featured ? 'var(--color-on-dark-soft)' : 'var(--color-body)',
                    }}>
                      <Check size={16} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
                      {f}
                    </li>
                  ))}
                </ul>

                <button
                  className={plan.featured ? 'btn btn--primary' : 'btn btn--secondary'}
                  style={{ width: '100%' }}
                  onClick={() => navigate('/dashboard')}
                >
                  {plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ─────────────────────────────────────────── */}
      <section style={{ padding: '96px 32px', background: 'var(--color-surface-soft)' }}>
        <div style={{ maxWidth: 700, margin: '0 auto' }}>
          <h2 style={{
            fontFamily: 'var(--font-display)', fontSize: 36, fontWeight: 400,
            letterSpacing: '-0.5px', color: 'var(--color-ink)',
            marginBottom: 48, textAlign: 'center',
          }}>Frequently asked questions</h2>

          <div>
            {FAQ.map((item, i) => (
              <details key={i} style={{
                borderBottom: '1px solid var(--color-hairline)',
                padding: '20px 0',
              }}>
                <summary style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  cursor: 'pointer', listStyle: 'none',
                  fontFamily: 'var(--font-sans)', fontSize: 16, fontWeight: 500,
                  color: 'var(--color-ink)',
                }}>
                  {item.q}
                  <span style={{ color: 'var(--color-muted-soft)', fontSize: 12, transition: 'transform 0.2s' }}>▼</span>
                </summary>
                <p style={{
                  marginTop: 12, fontSize: 16, color: 'var(--color-body)', lineHeight: 1.6,
                }}>{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Band ────────────────────────────────────── */}
      <section style={{
        margin: '32px', padding: 64, borderRadius: 12,
        background: 'var(--color-primary)', textAlign: 'center',
      }}>
        <h2 style={{
          fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 400,
          letterSpacing: '-0.3px', color: 'var(--color-on-primary)', marginBottom: 12,
        }}>Have questions?</h2>
        <p style={{ fontSize: 16, color: 'rgba(255,255,255,0.85)', marginBottom: 24 }}>
          We're here to help. Contact our team for any billing questions.
        </p>
        <button
          className="btn btn--lg"
          style={{ background: 'var(--color-canvas)', color: 'var(--color-primary)', border: 'none' }}
        >
          <Mail size={16} style={{ marginRight: 8 }} /> Contact Sales
        </button>
      </section>

      {/* ── Footer ──────────────────────────────────────── */}
      <footer style={{
        background: 'var(--color-surface-dark)', padding: '48px 32px',
        color: 'var(--color-on-dark-soft)', textAlign: 'center',
      }}>
        <p style={{ fontSize: 14 }}>© 2026 XgenPCB. All rights reserved.</p>
      </footer>
    </div>
  );
}