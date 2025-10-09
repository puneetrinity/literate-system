# Railway Deployment Guide

This guide covers deploying the AI Chat Service to Railway with RunPod LLM integration and optional LobeChat frontend.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **RunPod API Key**: Your RunPod API key and endpoint ID
3. **GitHub Repository**: Code should be in a GitHub repository

## Quick Deploy

### Option 1: Deploy via Railway Dashboard

1. **Create New Project**
   - Go to Railway dashboard
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize and select your repository

2. **Configure Service**
   - Railway will detect the Dockerfile
   - Set root directory to `ai-chat-service` if needed
   - Railway will automatically use `railway.json` config

3. **Set Environment Variables**

   Copy these required variables to Railway:

   ```bash
   # Required
   RUNPOD_API_KEY=your_runpod_api_key_here
   RUNPOD_ENDPOINT_ID=your_endpoint_id_here
   LLM_PROVIDER=runpod
   ENVIRONMENT=production

   # Generate a secure secret
   JWT_SECRET_KEY=<generate-random-string>
   ```

4. **Add Redis (Optional but Recommended)**
   - In your Railway project, click "New"
   - Select "Database" → "Add Redis"
   - Railway will automatically set `REDIS_URL` environment variable

5. **Deploy**
   - Railway will automatically deploy on push to main branch
   - Monitor build logs in Railway dashboard
   - Get your deployment URL from Railway

### Option 2: Deploy via Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Navigate to service directory
cd ai-chat-service

# Initialize Railway project
railway init

# Link to your project (or create new)
railway link

# Set environment variables
railway variables set RUNPOD_API_KEY=your_runpod_api_key_here
railway variables set RUNPOD_ENDPOINT_ID=your_endpoint_id_here
railway variables set LLM_PROVIDER=runpod
railway variables set ENVIRONMENT=production

# Deploy
railway up
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RUNPOD_API_KEY` | RunPod API authentication key | `rpa_FT9...` |
| `RUNPOD_ENDPOINT_ID` | RunPod endpoint identifier | `your_endpoint_id_here` |
| `LLM_PROVIDER` | LLM provider type | `runpod` |
| `ENVIRONMENT` | Deployment environment | `production` |
| `JWT_SECRET_KEY` | Secret for JWT tokens | Random 32+ char string |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Application port | `8000` |
| `REDIS_URL` | Redis connection URL | Railway auto-sets |
| `DOCUMENT_SEARCH_URL` | Document search service URL | - |
| `ALLOWED_ORIGINS` | CORS allowed origins | `*` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `100` |

## Adding LobeChat Frontend

### Deploy LobeChat to Railway

1. **Create New Service in Same Project**
   ```bash
   # In Railway dashboard
   # Click "New" → "GitHub Repo"
   # Select LobeChat repository (fork it first if needed)
   ```

2. **Configure LobeChat**

   Set these environment variables in LobeChat service:

   ```bash
   # Point to your AI Chat Service
   OPENAI_API_BASE_URL=https://your-ai-chat-service.railway.app/api/v1

   # Optional: Custom API key validation
   OPENAI_API_KEY=your-custom-key

   # Enable features
   ENABLE_OAUTH=false
   ```

3. **Update AI Chat Service CORS**

   Add LobeChat URL to ALLOWED_ORIGINS:
   ```bash
   ALLOWED_ORIGINS=https://your-lobechat.railway.app
   ```

### Alternative: Use LobeChat Docker

Create a new Railway service with custom Dockerfile:

```dockerfile
FROM lobehub/lobe-chat:latest

ENV OPENAI_API_BASE_URL=https://your-ai-chat-service.railway.app/api/v1
ENV OPENAI_API_KEY=not-required

EXPOSE 3000
```

## API Endpoints

Once deployed, your service will be available at:

```
https://your-service-name.railway.app
```

### Available Endpoints

- **Chat API**: `POST /api/v1/chat/unified`
- **Health Check**: `GET /health`
- **API Docs**: `GET /docs`
- **OpenAPI Schema**: `GET /openapi.json`

### Testing Your Deployment

```bash
# Health check
curl https://your-service.railway.app/health

# Test chat endpoint
curl -X POST https://your-service.railway.app/api/v1/chat/unified \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "mode": "unified"
  }'
```

## Monitoring

### Railway Built-in Monitoring

- **Metrics**: View CPU, memory, network in Railway dashboard
- **Logs**: Real-time logs available in dashboard
- **Deployments**: Track deployment history and rollbacks

### Application Metrics

Access Prometheus metrics at:
```
https://your-service.railway.app/metrics
```

### Health Checks

Railway will automatically monitor:
```
GET /health
```

Response should be:
```json
{
  "status": "healthy",
  "service": "ai_chat_service",
  "timestamp": "2024-01-01T00:00:00"
}
```

## Scaling

### Horizontal Scaling

Railway Pro/Team plans support multiple replicas:

1. Go to service settings
2. Adjust "Replica Count"
3. Railway handles load balancing automatically

### Vertical Scaling

Railway automatically scales resources based on usage.

For manual control:
1. Service Settings → Resources
2. Adjust CPU/Memory limits

## Troubleshooting

### Common Issues

**1. Build Fails**
```bash
# Check Dockerfile path in railway.json
# Verify all dependencies in requirements.txt
# Check build logs in Railway dashboard
```

**2. RunPod Connection Errors**
```bash
# Verify RUNPOD_API_KEY is correct
# Check RUNPOD_ENDPOINT_ID matches your endpoint
# Test RunPod API directly with curl
```

**3. Redis Connection Issues**
```bash
# Ensure Redis addon is added to project
# Verify REDIS_URL environment variable is set
# Check Railway service networking
```

**4. CORS Errors**
```bash
# Add your frontend domain to ALLOWED_ORIGINS
# Format: https://domain1.com,https://domain2.com
```

### Debug Mode

Enable debug logging:
```bash
railway variables set DEBUG=true
railway variables set LOG_LEVEL=DEBUG
```

View logs:
```bash
railway logs
```

## Cost Optimization

### Railway Pricing

- **Starter Plan**: $5/month - Good for development
- **Pro Plan**: $20/month - Includes more resources
- Pay-as-you-go for resources beyond plan limits

### Tips to Reduce Costs

1. **Use Redis caching** to reduce RunPod API calls
2. **Set rate limits** to prevent abuse
3. **Monitor usage** via Railway dashboard
4. **Use single replica** for low-traffic apps
5. **Optimize Docker image** - already done in provided Dockerfile

### RunPod Costs

- RunPod charges per API call and compute time
- Use caching to minimize API calls
- Monitor usage in RunPod dashboard

## CI/CD

Railway automatically deploys on:
- Push to main branch (default)
- Pull request merges

### Custom Deploy Branch

```bash
# Change deploy branch in Railway dashboard
# Settings → Environment → Production Branch
```

### Manual Deploy

```bash
railway up --environment production
```

## Security Best Practices

1. **Environment Variables**: Never commit secrets to git
2. **JWT Secret**: Use strong random string (32+ characters)
3. **Rate Limiting**: Enabled by default (100 req/min)
4. **CORS**: Restrict to your frontend domains only
5. **HTTPS**: Railway provides automatic SSL certificates

## Backup and Recovery

### Database Backups (if using PostgreSQL)

Railway automatically backs up databases.

### Configuration Backup

Export environment variables:
```bash
railway variables > backup.env
```

### Rollback Deployment

In Railway dashboard:
1. Go to "Deployments"
2. Find previous successful deployment
3. Click "Redeploy"

## Next Steps

1. **Set up monitoring** - Add external monitoring (e.g., Sentry, DataDog)
2. **Configure custom domain** - Railway supports custom domains
3. **Add document search** - Deploy document-search-service similarly
4. **Set up staging** - Create staging environment in Railway
5. **Enable auto-scaling** - Configure based on traffic patterns

## Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **RunPod Docs**: [docs.runpod.io](https://docs.runpod.io)

## Example .env for Local Testing

```bash
# Copy to .env for local development
ENVIRONMENT=development
DEBUG=true
LLM_PROVIDER=runpod
RUNPOD_API_KEY=your_runpod_api_key_here
RUNPOD_ENDPOINT_ID=your_endpoint_id_here
REDIS_URL=redis://localhost:6379
ALLOWED_ORIGINS=http://localhost:3000
JWT_SECRET_KEY=dev-secret-key-change-in-production
```

Test locally:
```bash
# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```
