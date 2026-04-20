# XgenPCB Deployment Guide

## Quick Start (Local Development)

```bash
# 1. Start infrastructure
make db-up

# 2. Start backend
cd backend && make dev

# 3. Start frontend
cd frontend/apps/web && npm run dev
```

---

## Deployment (Production)

### Frontend (Vercel)

```bash
cd frontend/apps/web

# Build
npm run build

# Deploy (requires Vercel CLI)
vercel --prod

# Or connect GitHub repo in Vercel dashboard
# Settings:
# - Framework: Vite
# - Build command: npm run build  
# - Output directory: dist
```

**Environment Variables (Vercel):**
```
VITE_API_URL=https://api.yourdomain.com
```

### Backend (Render/Railway)

**Option 1: Render.com**
```bash
# Push to GitHub
# Connect repo in Render dashboard
# Settings:
# - Build command: cd backend && pip install -e .
# - Start command: uvicorn services.gateway.main:app --host 0.0.0.0 --port $PORT
```

**Option 2: Railway**
```bash
# railway login
# railway init
# railway up
```

**Environment Variables (Backend):**
```
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379
OPENAI_API_KEY=sk-...
JWT_SECRET=your-secret-key
```

---

## Free Tier Limits (MVP)

| Feature | Free | Pro |
|---------|------|-----|
| Projects | 3/month | Unlimited |
| PCB Layers | 2 | 8 |
| AI Chat | Basic | Domain-adapted |
| Auto-route | Basic | Priority RL |
| Fab Quotes | Community | Live |
| Support | Community | Email |

---

## Stripe Configuration (Pro Tier)

```python
# backend/services/payment/routes.py
import stripe

@router.post("/create-checkout")
async def create_checkout_session(request: CheckoutRequest):
    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{
            "price": "price_id_from_stripe",
            "quantity": 1,
        }],
        success_url="https://xgenpcb.com/success",
        cancel_url="https://xgenpcb.com/cancel",
    )
    return {"url": session.url}
```

---

## Monitoring (Optional)

**Sentry (Error Tracking):**
```bash
pip install sentry-sdk
```

**Logflare (Log Analytics):**
```bash
# Add to backend config
LOGFLARE_API_KEY=...
```

---

## CDN (Optional)

For best performance, add Cloudflare:
1. Point domain to Vercel/Render
2. Enable "Always on HTTPS"
3. Add page rules for caching static assets

---

## Domain Setup

1. Buy domain (Namecheap, Cloudflare, or Porkbun)
2. Add to Vercel (frontend)
3. Add CNAME record for api.yourdomain.com -> Render/Railway

---

## Success Metrics

- [x] Build passes
- [ ] Deploy to Vercel
- [ ] Deploy backend
- [ ] Configure domain
- [ ] Add Stripe
- [ ] Launch (announce)