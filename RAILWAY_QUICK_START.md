# Railway Deployment - Quick Start Guide

## ⚠️ Critical: This is a Monorepo!

Railway is showing an error because it's looking at the **root directory** which contains multiple services. You need to tell Railway which service to deploy.

---

## 🚀 Fix: Set Root Directory

### In Railway Dashboard:

1. **After connecting your GitHub repo**, Railway will fail to auto-detect
2. **Don't panic!** This is expected for monorepos
3. Click on the service (or go to **Settings**)
4. Find **"Root Directory"** setting
5. Set it to: **`ai-chat-service`** (for the backend) or **`chainlit-frontend`** (for the frontend)
6. Click **"Redeploy"** or **"Deploy"**

---

## 📋 Step-by-Step Visual Guide

### Step 1: Create New Project
```
Railway Dashboard → New Project → Deploy from GitHub Repo
└─→ Select: puneetrinity/literate-system
```

### Step 2: Configure Service Settings
```
Click on the service → Settings → Service Settings

┌─────────────────────────────────────┐
│  Service Settings                   │
├─────────────────────────────────────┤
│  Root Directory:  [ai-chat-service] │  ← Set this!
│                                     │
│  Start Command:   [Leave empty]    │
│                                     │
│  Builder:         [DOCKERFILE]     │  ← Auto-detected
└─────────────────────────────────────┘
```

### Step 3: Add Environment Variables
```
Settings → Variables → Add Variable

Required for AI Chat Service:
┌────────────────────────────────────────────┐
│ RUNPOD_API_KEY       = your_api_key        │
│ RUNPOD_ENDPOINT_ID   = your_endpoint_id    │
│ LLM_PROVIDER         = runpod              │
│ ENVIRONMENT          = production          │
│ JWT_SECRET_KEY       = random_32_chars     │
└────────────────────────────────────────────┘
```

### Step 4: Deploy
```
Railway will now:
1. ✓ Find Dockerfile in ai-chat-service/
2. ✓ Build the Docker image
3. ✓ Deploy the service
4. ✓ Give you a URL: https://your-service.railway.app
```

---

## 🎯 Complete Deployment Checklist

### Service 1: AI Chat Service (Backend)

- [ ] Create new service from GitHub
- [ ] Set **Root Directory** = `ai-chat-service`
- [ ] Add environment variables:
  - [ ] `RUNPOD_API_KEY`
  - [ ] `RUNPOD_ENDPOINT_ID`
  - [ ] `LLM_PROVIDER=runpod`
  - [ ] `ENVIRONMENT=production`
  - [ ] `JWT_SECRET_KEY` (random 32+ chars)
- [ ] Deploy
- [ ] Test: `curl https://your-service.railway.app/health`
- [ ] Copy the service URL

### Service 2: Add Redis (Optional)

- [ ] Click **"New"** in same project
- [ ] Select **"Database"** → **"Add Redis"**
- [ ] Railway auto-sets `REDIS_URL` in all services

### Service 3: Chainlit Frontend

- [ ] Click **"New"** in same project
- [ ] Select **"GitHub Repo"** → Select repository
- [ ] Set **Root Directory** = `chainlit-frontend`
- [ ] Add environment variable:
  - [ ] `AI_CHAT_SERVICE_URL=https://your-ai-service-url.railway.app`
  - [ ] `PORT=8080`
- [ ] Deploy
- [ ] Copy the Chainlit URL

### Service 4: Update CORS

- [ ] Go back to **AI Chat Service** settings
- [ ] Add variable: `ALLOWED_ORIGINS=https://your-chainlit.railway.app`
- [ ] Railway auto-redeploys

### Service 5: Test Everything

- [ ] Open Chainlit URL in browser
- [ ] Send a test message
- [ ] Verify response from RunPod
- [ ] Check Railway logs for both services

---

## 🐛 Common Errors & Fixes

### Error: "Railpack could not determine how to build"
**Cause**: Railway is looking at root directory
**Fix**: Set **Root Directory** to `ai-chat-service` or `chainlit-frontend`

### Error: "start.sh not found"
**Cause**: Railway is in the wrong directory
**Fix**: Set **Root Directory** in service settings

### Error: "No Dockerfile found"
**Cause**: Root Directory not set correctly
**Fix**: Verify Root Directory = `ai-chat-service` (with no trailing slash)

### Error: "RUNPOD_API_KEY not set"
**Cause**: Environment variables missing
**Fix**: Add all required environment variables in Settings → Variables

### Error: "Connection refused" in Chainlit
**Cause**: AI Chat Service URL wrong or CORS not set
**Fix**:
1. Verify `AI_CHAT_SERVICE_URL` in Chainlit
2. Add `ALLOWED_ORIGINS` in AI Chat Service

---

## 📊 Expected Results

### AI Chat Service
- **Build time**: 3-5 minutes
- **Container size**: ~200-300 MB
- **Startup time**: 10-30 seconds
- **Health endpoint**: `GET /health` returns 200 OK
- **API docs**: `GET /docs` (Swagger UI)

### Chainlit Frontend
- **Build time**: 2-3 minutes
- **Container size**: ~150-200 MB
- **Startup time**: 5-10 seconds
- **URL**: Opens Chainlit chat interface
- **Features**: 4 chat profiles visible

---

## 🔗 URLs You'll Get

After deployment, you'll have:

```
1. AI Chat Service
   https://ai-chat-service-production-xxx.railway.app

2. Chainlit Frontend
   https://chainlit-frontend-production-xxx.railway.app

3. Redis (internal only)
   redis://default:password@xxx.railway.internal:6379
```

---

## 📞 Need Help?

1. **Check logs**: Railway Dashboard → Service → Logs
2. **Check settings**: Verify Root Directory is set
3. **Check variables**: Verify all environment variables
4. **Check docs**:
   - `ai-chat-service/RAILWAY_DEPLOYMENT.md`
   - `chainlit-frontend/CHAINLIT_DEPLOYMENT.md`
5. **Railway Discord**: https://discord.gg/railway

---

## 🎓 Understanding Monorepos

Your repository structure:
```
literate-system/                    ← Root (don't deploy from here!)
├── ai-chat-service/               ← Deploy as Service 1
│   ├── Dockerfile                ← Railway will find this
│   ├── requirements.txt
│   └── app/
├── chainlit-frontend/             ← Deploy as Service 2
│   ├── Dockerfile                ← Railway will find this
│   ├── requirements.txt
│   └── app.py
└── document-search-service/       ← Optional Service 3
    └── Dockerfile
```

**Key Point**: Each folder is a **separate service**. Railway needs to know which one to deploy by setting the **Root Directory**.

---

## ✅ Success Indicators

You'll know it's working when:

1. ✅ Railway build succeeds (green checkmark)
2. ✅ Health endpoint returns 200 OK
3. ✅ Chainlit opens in browser
4. ✅ You can send messages and get responses
5. ✅ Logs show RunPod API calls succeeding

---

**Ready to deploy!** Follow the checklist above step by step. 🚀
