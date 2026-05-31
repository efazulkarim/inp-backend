# Deploying to Vercel

This FastAPI backend is configured for Vercel serverless deployment.

## Quick Deploy

1. **Connect repository** to Vercel (GitHub, GitLab, or Bitbucket).

2. **Set environment variables** in Vercel Project Settings → Environment Variables:

   | Variable | Required | Description |
   |----------|----------|-------------|
   | `DATABASE_URL` | Yes | PostgreSQL connection string (Neon recommended) |
   | `SECRET_KEY` | Yes | JWT signing key (generate a secure random string) |
   | `SESSION_SECRET_KEY` | Yes | Session encryption key |
   | `FRONTEND_URL` | Yes | Your frontend URL (e.g. `https://app.insightpilot.co`) |
   | `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
   | `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
   | `GOOGLE_REDIRECT_URI` | Yes* | `https://YOUR_VERCEL_DOMAIN/auth/google/callback` |
   | `STRIPE_SECRET_KEY` | Yes | Stripe secret key |
   | `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
   | `GLM_API_KEY` or `VULTR_API_KEY` | One | LLM provider API key |

   \* On Vercel, `GOOGLE_REDIRECT_URI` is auto-built from `VERCEL_URL` if not set. Add `https://YOUR_PROJECT.vercel.app/auth/google/callback` to Google Cloud Console → Credentials → Authorized redirect URIs.

3. **Deploy**:
   ```bash
   vercel
   ```
   Or push to your connected Git branch.

## Post-Deploy Checklist

- [ ] Add your Vercel API URL to **Google Cloud Console** → Credentials → Authorized redirect URIs
- [ ] Update **Stripe webhook** endpoint to `https://YOUR_PROJECT.vercel.app/api/stripe/webhook`
- [ ] Run database migrations (from local or CI): `alembic upgrade head`
- [ ] Add `FRONTEND_URL` to CORS (handled automatically if set in env)

## Local Development with Vercel

```bash
pip install -r requirements.txt
vercel dev
```

## Limitations

- **Function timeout**: 10s (Hobby), 60s (Pro). Long report generation may need optimization.
- **Cold starts**: First request after idle may be slower.
- **Alembic**: Run migrations locally or in CI before deploy; do not run during Vercel build.
