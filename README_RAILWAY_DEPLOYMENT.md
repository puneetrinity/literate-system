# Railway Deployment Instructions

## Important: This is a Monorepo

This repository contains **multiple services** that need to be deployed separately on Railway. Railway cannot auto-detect which service to deploy from the root directory.

## How to Deploy

### ⚠️ DO NOT deploy from the root directory!

Instead, follow these steps:

---

## Option 1: Deploy via Railway Dashboard (Recommended)

### Step 1: Deploy AI Chat Service

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose this repository: `puneetrinity/literate-system`
5. **IMPORTANT**: Click **"Add variables"** or **"Settings"** first
6. In Settings → **Service Settings**:
   - **Root Directory**: `ai-chat-service`
   - **Start Command**: Leave empty (uses Dockerfile CMD)
7. Add environment variables:
   ```
   RUNPOD_API_KEY=your_runpod_api_key
   RUNPOD_ENDPOINT_ID=your_endpoint_id
   LLM_PROVIDER=runpod
   ENVIRONMENT=production
   JWT_SECRET_KEY=your_random_secret_32_chars
   ```
8. Click **"Deploy"**

### Step 2: Add Redis (Optional but Recommended)

1. In the same project, click **"New"**
2. Select **"Database"** → **"Add Redis"**
3. Railway automatically sets `REDIS_URL` in AI Chat Service

### Step 3: Deploy Chainlit Frontend

1. In the same project, click **"New"**
2. Select **"GitHub Repo"** → Choose `puneetrinity/literate-system`
3. Railway creates a new service
4. In Settings → **Service Settings**:
   - **Root Directory**: `chainlit-frontend`
5. Add environment variable:
   ```
   AI_CHAT_SERVICE_URL=https://your-ai-chat-service-url.railway.app
   PORT=8080
   ```
6. Click **"Deploy"**

### Step 4: Update CORS

1. Go back to **AI Chat Service** settings
2. Add environment variable:
   ```
   ALLOWED_ORIGINS=https://your-chainlit-url.railway.app
   ```
3. Railway will auto-redeploy

---

## Option 2: Deploy via Railway CLI

### Prerequisites

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login
```

### Deploy AI Chat Service

```bash
# Create new project
railway init

# Link to project
railway link

# Deploy AI Chat Service
cd ai-chat-service
railway up

# Set environment variables
railway variables set RUNPOD_API_KEY=your_key
railway variables set RUNPOD_ENDPOINT_ID=your_endpoint
railway variables set LLM_PROVIDER=runpod
railway variables set ENVIRONMENT=production
railway variables set JWT_SECRET_KEY=your_secret
```

### Deploy Chainlit Frontend

```bash
# In the same project, create new service
cd ../chainlit-frontend

# Create new service (you may need to do this via dashboard)
railway up

# Set environment variables
railway variables set AI_CHAT_SERVICE_URL=https://your-ai-service.railway.app
railway variables set PORT=8080
```

---

## Why This Happens

Railway's auto-detection (Railpack) looks at the **root directory** and sees:
- Multiple service folders
- No `start.sh` script at root level
- No clear single application to deploy

This is expected for a **monorepo** structure!

## Solution

Always specify the **Root Directory** for each service:

| Service | Root Directory |
|---------|---------------|
| AI Chat Service | `ai-chat-service` |
| Chainlit Frontend | `chainlit-frontend` |
| Document Search | `document-search-service` |

## Troubleshooting

### "Railpack could not determine how to build"

**Fix**: Set Root Directory in Service Settings to the specific service folder.

### "start.sh not found"

**Fix**: Railway is looking in the wrong directory. Set Root Directory.

### "Multiple services in one repo?"

**Yes!** This is a monorepo. Deploy each service separately with different root directories.

---

## Quick Reference

### AI Chat Service Environment Variables

```bash
# Required
RUNPOD_API_KEY=your_runpod_api_key
RUNPOD_ENDPOINT_ID=your_endpoint_id
LLM_PROVIDER=runpod
ENVIRONMENT=production
JWT_SECRET_KEY=generate_random_32_chars

# Optional
REDIS_URL=redis://default:password@host:port  # Auto-set by Railway
ALLOWED_ORIGINS=https://your-chainlit.railway.app
```

### Chainlit Frontend Environment Variables

```bash
# Required
AI_CHAT_SERVICE_URL=https://your-ai-chat-service.railway.app
PORT=8080

# Optional
DEFAULT_CHAT_MODE=unified
API_TIMEOUT=60
```

---

## Full Documentation

- **AI Chat Service**: `ai-chat-service/RAILWAY_DEPLOYMENT.md`
- **Chainlit Frontend**: `chainlit-frontend/CHAINLIT_DEPLOYMENT.md`
- **Complete Overview**: `DEPLOYMENT_SUMMARY.md`

---

## Support

If you need help:
1. Check the Railway docs: https://docs.railway.app
2. Check service-specific deployment guides in each folder
3. Railway Discord: https://discord.gg/railway

---

## Architecture

```
┌─────────────────────────────────────────┐
│   GitHub Repository (Monorepo)         │
│   puneetrinity/literate-system          │
└──────────────┬──────────────────────────┘
               │
               ├─── ai-chat-service/      ──→  Railway Service 1
               │                                 (Root: ai-chat-service)
               │
               ├─── chainlit-frontend/    ──→  Railway Service 2
               │                                 (Root: chainlit-frontend)
               │
               └─── document-search-service/ ──→ Optional Service 3
                                                  (Root: document-search-service)
```

Each service is deployed independently with its own root directory setting!
