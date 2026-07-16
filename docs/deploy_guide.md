# ICARUS Deployment Guide

## Option A — Local Docker (test production setup locally)

### Prerequisites
- Docker Desktop installed and running

### Run everything with one command

```bash
# From ICARUS root
docker-compose up -d
```

This starts:
- ICARUS backend on http://localhost:8000
- PostgreSQL on localhost:5432
- Qdrant on localhost:6333
- Redis on localhost:6379

### Check everything is running

```bash
docker-compose ps
docker-compose logs backend --tail=50
```

### Stop everything

```bash
docker-compose down
```

### Rebuild after code changes

```bash
docker-compose up -d --build backend
```

---

## Option B — Railway (free public URL)

Railway gives you a public URL like `icarus-production.up.railway.app`
Free tier: 500 hours/month — enough for a portfolio project.

### Step 1 — Create Railway account
Go to https://railway.app and sign up with GitHub.

### Step 2 — Create a new project
- Click "New Project"
- Select "Deploy from GitHub repo"
- Select your `zayyydh/ICARUS` repository

### Step 3 — Add environment variables
In Railway dashboard → your service → Variables, add:

```
GEMINI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_ID=your_id
GITHUB_TOKEN=your_token
GITHUB_USERNAME=zayyydh
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash-lite
ICARUS_ENV=production
LOG_LEVEL=INFO
DEFAULT_PERSONALITY=bro
DEFAULT_LANGUAGE=hinglish
ELEVENLABS_MODEL=eleven_multilingual_v2
```

### Step 4 — Add PostgreSQL + Redis
In Railway:
- Click "+ New" → Database → PostgreSQL
- Click "+ New" → Database → Redis
- Railway automatically injects `DATABASE_URL` and `REDIS_URL`

### Step 5 — Update settings.py for Railway URLs
Railway provides different env var names. Add to your `.env.example`:

```env
# Railway auto-injects these:
DATABASE_URL=  # maps to POSTGRES_URL
REDIS_URL=     # already correct
```

In `backend/app/config/settings.py`, add:
```python
# Railway compat — uses DATABASE_URL instead of POSTGRES_URL
POSTGRES_URL: str = Field(
    default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://icarus:icarus@localhost:5432/icarus")
)
```

### Step 6 — Deploy
Railway auto-deploys on every push to your `main` branch.

```bash
git checkout main
git merge develop
git push origin main
```

Watch the deployment at railway.app/dashboard.

### Step 7 — Get your URL
Railway assigns a URL like: `icarus-production.up.railway.app`

Test it:
```
curl https://icarus-production.up.railway.app/api/v1/health
```

Should return: `{"status":"online","system":"ICARUS","version":"0.1.0"}`

---

## Option C — Render (alternative free tier)

Similar to Railway. Go to https://render.com:
- New → Web Service
- Connect GitHub repo
- Build Command: `pip install -r requirements/base.txt`
- Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add environment variables same as Railway

---

## Updating the UI for production

Once deployed, update `icarus_ui.html`:

```javascript
// Change this line:
const API = 'http://localhost:8000/api/v1';

// To your Railway URL:
const API = 'https://icarus-production.up.railway.app/api/v1';
```

Then host the HTML on GitHub Pages:
- Go to repo Settings → Pages
- Source: Deploy from branch → main → /docs
- Move `frontend/index.html` to `docs/index.html`
- Push → your UI is live at `zayyydh.github.io/ICARUS`

---

## Final production checklist

```
✅ .env never committed (in .gitignore)
✅ ICARUS_ENV=production in Railway vars
✅ Health endpoint returns 200
✅ CORS configured for your frontend domain
✅ Rate limiting on API endpoints
✅ Logs going to Railway dashboard
```