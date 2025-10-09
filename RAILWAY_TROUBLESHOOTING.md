# Railway Deployment Troubleshooting

## Error: "Dockerfile `Dockerfile` does not exist"

### Cause
Railway is looking for the Dockerfile in the **root directory** of the repository, but this is a **monorepo** with multiple services. The Dockerfile is located in `ai-chat-service/Dockerfile`, not at the root.

### Solution

#### Via Railway Dashboard (Recommended)

1. Open your Railway project
2. Click on the service that's failing
3. Click **"Settings"** (gear icon in sidebar)
4. Scroll to **"Service Settings"** section
5. Look for **"Root Directory"** field
6. Enter: **`ai-chat-service`** (exactly, no leading/trailing slashes)
7. The setting auto-saves
8. Go to **"Deployments"** tab
9. Click **"Redeploy"** or click the three dots (...) → **"Redeploy"**

#### Via Railway CLI

```bash
# In your local repository
cd ai-chat-service

# Deploy from this directory
railway up

# Or set the root directory
railway service --root ai-chat-service
```

---

## Verification Steps

### 1. Verify Dockerfile Exists

```bash
# In your local repository
ls -la ai-chat-service/Dockerfile
```

Expected output:
```
-rw-r--r-- 1 user user 1275 Oct  9 10:08 ai-chat-service/Dockerfile
```

✅ **Dockerfile exists!**

### 2. Verify Dockerfile Content

```bash
head -5 ai-chat-service/Dockerfile
```

Expected output:
```dockerfile
# Railway-optimized Dockerfile for AI Chat Service with RunPod LLM
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
```

✅ **Dockerfile is valid!**

### 3. Check Railway Root Directory Setting

In Railway Dashboard:
```
Settings → Service Settings → Root Directory

Should show: ai-chat-service
Not: (empty) or / or literate-system
```

---

## Common Mistakes

### ❌ Wrong: Root Directory is empty or "/"
```
Root Directory: [empty]
or
Root Directory: /
```
Railway looks at repository root → Can't find Dockerfile

### ❌ Wrong: Root Directory has trailing slash
```
Root Directory: ai-chat-service/
```
May cause path issues on some systems

### ✅ Correct: Root Directory is exactly "ai-chat-service"
```
Root Directory: ai-chat-service
```
Railway looks at `ai-chat-service/Dockerfile` → Success!

---

## Step-by-Step Fix with Screenshots Reference

### Step 1: Access Service Settings
```
Railway Dashboard
└─→ Your Project
    └─→ Your Service (failing one)
        └─→ Settings (left sidebar, gear icon)
```

### Step 2: Find Root Directory Setting
```
Settings Page
└─→ Scroll down to "Service Settings"
    └─→ Find "Root Directory" field
        └─→ Currently shows: [empty] or wrong value
```

### Step 3: Set Correct Value
```
Root Directory: [ai-chat-service]  ← Type this
                ^
                |
                No leading or trailing slashes!
```

### Step 4: Redeploy
```
Deployments Tab
└─→ Latest Deployment (failed)
    └─→ Three dots menu (...)
        └─→ Click "Redeploy"
```

### Step 5: Watch Build Logs
```
Deployment View
└─→ Build logs will show:
    ✓ Found Dockerfile
    ✓ Building from ai-chat-service/Dockerfile
    ✓ Installing dependencies
    ✓ Successfully built
```

---

## Alternative: Deploy Each Service Separately

If you're still having issues, try this approach:

### Method 1: Create Service Manually

1. **Create new service** in Railway
2. **Don't** use "Deploy from GitHub" initially
3. **Go to Settings first**
4. **Set Root Directory** = `ai-chat-service`
5. **Then** connect GitHub repository
6. **Deploy**

### Method 2: Use Railway CLI

```bash
# Navigate to service directory
cd ai-chat-service

# Initialize Railway in this directory
railway init

# This will create the service with correct root directory
railway up
```

---

## Confirm It's Working

After setting Root Directory and redeploying, you should see:

### Build Logs Should Show:
```
╭─ Dockerfile ────────────────────╮
│ Using Dockerfile at:            │
│ /app/ai-chat-service/Dockerfile │
╰─────────────────────────────────╯

Step 1/10 : FROM python:3.10-slim
✓ Successfully pulled python:3.10-slim

Step 2/10 : ENV PYTHONDONTWRITEBYTECODE=1
✓ Running

... (more build steps)

✓ Build successful
✓ Deploying...
✓ Deployment successful
```

### Deployment Should Show:
```
Status: Running
Health: Healthy
URL: https://your-service.railway.app
```

### Test Endpoint:
```bash
curl https://your-service.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "ai_chat_service",
  "timestamp": "2024-10-09T..."
}
```

---

## Still Not Working?

### Check These:

1. **Repository Access**
   - Verify Railway has access to your GitHub repository
   - Check Railway → Settings → GitHub → Repository Access

2. **Branch**
   - Verify deploying from correct branch (usually `master` or `main`)
   - Settings → GitHub → Production Branch

3. **File Permissions**
   - Ensure Dockerfile is committed to git
   - Run: `git ls-files ai-chat-service/Dockerfile`
   - Should output: `ai-chat-service/Dockerfile`

4. **Railway Service Type**
   - Ensure it's a "Web Service" not a "Worker"
   - Settings → Service Type → Web Service

---

## Contact Railway Support

If issue persists, share this info with Railway support:

```
Repository: puneetrinity/literate-system
Branch: master
Root Directory: ai-chat-service
Dockerfile Path (from root): ai-chat-service/Dockerfile
Error: "Dockerfile `Dockerfile` does not exist"

Dockerfile verified exists locally:
$ ls -la ai-chat-service/Dockerfile
-rw-r--r-- 1 user user 1275 Oct  9 10:08 ai-chat-service/Dockerfile

Dockerfile verified in git:
$ git ls-files ai-chat-service/Dockerfile
ai-chat-service/Dockerfile

Root Directory setting in Railway: [provide value shown]
```

---

## Quick Reference

| Setting | Value |
|---------|-------|
| Root Directory | `ai-chat-service` |
| Dockerfile Path | `Dockerfile` (relative to root dir) |
| Full Path | `ai-chat-service/Dockerfile` |
| Start Command | (leave empty, uses Dockerfile CMD) |
| Build Command | (leave empty, uses Dockerfile) |

---

**Bottom Line**: Railway needs to know this is a monorepo. Set **Root Directory** to `ai-chat-service` and it will find the Dockerfile! 🚀
