# Chainlit Frontend Deployment Guide

Complete guide for deploying Chainlit frontend with your AI Chat Service on Railway.

## Why Chainlit?

Chainlit is purpose-built for AI chat applications and offers several advantages:

✅ **Easy Integration** - Built for Python backends, seamless FastAPI integration
✅ **Chat Profiles** - Multiple modes (chat, search, research, unified)
✅ **Beautiful UI** - Modern, responsive, mobile-friendly
✅ **Conversation History** - Built-in session management
✅ **File Upload** - Native support for file attachments
✅ **Streaming** - Real-time streaming responses
✅ **Authentication** - OAuth support (Google, GitHub, etc.)
✅ **Customizable** - Easy theming and branding
✅ **Lightweight** - Fast deployment, minimal dependencies

## Quick Deploy to Railway

### Step 1: Prepare Your Repository

```bash
# Ensure you're in the project root
cd unified-ai-system-clean

# Add Chainlit files
git add chainlit-frontend/
git commit -m "Add Chainlit frontend"
git push origin main
```

### Step 2: Deploy on Railway

1. **Create New Service**
   - Go to your Railway project (same project as AI Chat Service)
   - Click "New" → "GitHub Repo"
   - Select your repository
   - Set **root directory**: `chainlit-frontend`

2. **Configure Environment Variables**

   In Railway dashboard, add these variables:

   ```bash
   # Required
   AI_CHAT_SERVICE_URL=https://your-ai-chat-service.railway.app
   PORT=8080

   # Optional
   DEFAULT_CHAT_MODE=unified
   API_TIMEOUT=60
   ```

3. **Deploy**
   - Railway will detect the Dockerfile
   - Build and deploy automatically
   - Get your URL: `https://chainlit-xxx.railway.app`

### Step 3: Update AI Chat Service CORS

Add Chainlit URL to allowed origins:

```bash
# In AI Chat Service environment variables
ALLOWED_ORIGINS=https://your-chainlit.railway.app
```

Redeploy AI Chat Service for CORS to take effect.

## Local Development

### Setup

```bash
cd chainlit-frontend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and set AI_CHAT_SERVICE_URL
# For local development: http://localhost:8000
```

### Run Locally

```bash
# Make sure AI Chat Service is running on port 8000
cd ../ai-chat-service
uvicorn app.main:app --reload --port 8000

# In another terminal, run Chainlit
cd ../chainlit-frontend
chainlit run app.py --port 8080
```

Open browser: `http://localhost:8080`

## Features & Usage

### Chat Profiles (Modes)

Chainlit supports multiple chat modes via profiles:

- **🚀 Unified** - Search + Chat combined
- **💬 Chat** - Pure conversation
- **🔍 Search** - Document search
- **📚 Research** - Deep research mode

Users can switch modes using the profile selector in the UI.

### Conversation History

Chainlit automatically manages conversation history:
- Stores last 10 messages for context
- Passes to backend API
- Persists during session

### File Upload

Enable file uploads in `.chainlit` config:

```toml
[features.spontaneous_file_upload]
    enabled = true
    accept = ["*/*"]
    max_files = 5
    max_size_mb = 10
```

Handle uploads in `app.py`:

```python
@cl.on_message
async def main(message: cl.Message):
    # Access uploaded files
    files = message.elements

    if files:
        for file in files:
            # Process file
            content = file.content
            name = file.name
```

### Streaming Responses

To enable streaming from backend:

```python
@cl.on_message
async def main(message: cl.Message):
    msg = cl.Message(content="")
    await msg.send()

    # Stream from backend API
    async for chunk in api_client.stream_message(message.content):
        msg.content += chunk
        await msg.stream_token(chunk)
```

## Customization

### Branding

1. **Logo**: Add to `public/` folder
   - `logo_light.png` - Light mode logo
   - `logo_dark.png` - Dark mode logo
   - Recommended size: 200x50px

2. **Theme**: Edit `.chainlit` config

```toml
[UI.theme.light.primary]
    main = "#F80061"  # Your brand color

[UI.theme.dark.primary]
    main = "#F80061"  # Your brand color
```

3. **Name & Description**: Edit `.chainlit` config

```toml
[UI]
name = "Your App Name"
description = "Your app description"
```

### Custom CSS

Create `public/custom.css`:

```css
/* Custom styles */
.message-content {
    font-size: 16px;
}
```

Reference in `.chainlit`:

```toml
[UI]
custom_css = "/public/custom.css"
```

### Custom Welcome Message

Edit `chainlit.md` to customize the welcome screen.

## Authentication

### Add OAuth (Google, GitHub)

1. **Install Literal AI** (optional but recommended)

```bash
pip install literalai
```

2. **Configure OAuth in `.chainlit`**

```toml
[project]
user_env = []

# Add OAuth provider
```

3. **Set Environment Variables**

```bash
OAUTH_GOOGLE_CLIENT_ID=your-client-id
OAUTH_GOOGLE_CLIENT_SECRET=your-client-secret
CHAINLIT_AUTH_SECRET=your-secret-key
```

4. **Update app.py**

```python
@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    # Custom authentication logic
    if username == "admin" and password == "password":
        return cl.User(identifier="admin")
    return None
```

## Database Integration

### Add PostgreSQL for Conversation Persistence

1. **Add PostgreSQL in Railway**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway auto-sets `DATABASE_URL`

2. **Install Dependencies**

```bash
pip install asyncpg sqlalchemy
```

3. **Configure Chainlit**

```bash
CHAINLIT_DATABASE_URL=$DATABASE_URL
```

Chainlit will automatically store conversations in the database.

## Monitoring & Analytics

### Literal AI Integration

Literal AI provides monitoring for Chainlit apps:

1. **Sign up**: https://cloud.getliteral.ai
2. **Get API key**
3. **Set environment variable**:

```bash
LITERAL_API_KEY=your-literal-api-key
```

4. **View analytics**:
   - User conversations
   - Performance metrics
   - Error tracking
   - Usage statistics

## Testing

### Test Backend Connection

```python
# In Chainlit console or separate script
import asyncio
from app import api_client

async def test():
    health = await api_client.get_health()
    print(health)

    response = await api_client.send_message("Hello!")
    print(response)

asyncio.run(test())
```

### Test UI

1. Open Chainlit: `http://localhost:8080`
2. Try each chat profile
3. Send test messages
4. Check backend logs
5. Verify responses

## Production Checklist

- [ ] Backend API URL configured correctly
- [ ] CORS settings updated in backend
- [ ] Environment variables set in Railway
- [ ] Logo added (optional)
- [ ] Theme customized (optional)
- [ ] Welcome message customized
- [ ] Authentication configured (if needed)
- [ ] Database configured (if needed)
- [ ] Monitoring enabled (if needed)
- [ ] Health checks passing
- [ ] Custom domain configured (optional)

## Troubleshooting

### Chainlit won't start

**Check:**
- `AI_CHAT_SERVICE_URL` is set correctly
- All dependencies installed
- Port 8080 is available
- Railway logs for errors

### Can't connect to backend

**Check:**
- Backend is running and accessible
- CORS configured in backend
- URL is correct (https, not http)
- Network connectivity

### Streaming not working

**Check:**
- Backend supports streaming endpoint
- Frontend streaming code implemented
- Timeout settings adequate

### File upload not working

**Check:**
- File upload enabled in `.chainlit`
- File size within limits
- File type allowed
- Backend handles file processing

## Performance Optimization

### Caching

Enable caching for faster responses:

```python
# In app.py
from functools import lru_cache

@lru_cache(maxsize=100)
async def cached_api_call(message: str):
    return await api_client.send_message(message)
```

### Lazy Loading

Load heavy dependencies only when needed:

```python
@cl.on_message
async def main(message: cl.Message):
    # Import only when needed
    from heavy_module import process
    result = await process(message.content)
```

### Connection Pooling

Reuse HTTP connections:

```python
# Global client with connection pooling
api_client = ChatAPIClient(
    base_url=AI_CHAT_SERVICE_URL,
    timeout=60
)
```

## Advanced Features

### Multi-User Support

Chainlit supports multiple concurrent users:
- Each user gets isolated session
- Conversation history per user
- No data leakage between sessions

### Custom Actions

Add custom buttons/actions:

```python
@cl.action_callback("action_button")
async def on_action(action: cl.Action):
    await cl.Message(content="Button clicked!").send()

# In message
actions = [
    cl.Action(name="action_button", value="clicked", label="Click Me")
]
await cl.Message(content="Message with action", actions=actions).send()
```

### Data Tables

Display structured data:

```python
from chainlit.element import Data

data = Data(
    name="results",
    content={"results": search_results},
    display="side"
)
await cl.Message(content="Results", elements=[data]).send()
```

## Cost Estimation

### Railway Costs

- **Chainlit Frontend**: ~$5-10/month (Starter plan)
- **AI Chat Service**: ~$10-20/month (depends on usage)
- **PostgreSQL** (optional): ~$5/month
- **Total**: ~$20-35/month

### Optimization Tips

1. Use caching to reduce API calls
2. Implement rate limiting
3. Use single Railway project (shared resources)
4. Monitor usage with Literal AI

## Next Steps

1. ✅ Deploy Chainlit to Railway
2. 🔄 Customize branding and theme
3. 🔄 Add authentication (if needed)
4. 🔄 Configure database (if needed)
5. 🔄 Set up monitoring
6. 🔄 Add custom domain
7. 🔄 Optimize performance

## Support & Resources

- **Chainlit Docs**: https://docs.chainlit.io
- **Chainlit Discord**: https://discord.gg/chainlit
- **Railway Docs**: https://docs.railway.app
- **Literal AI**: https://docs.getliteral.ai

---

**Your Chainlit frontend is ready to deploy!** 🚀

It's simpler, faster, and more integrated with Python backends compared to LobeChat.
