"""
Chainlit Frontend for AI Chat Service
Connects to FastAPI backend with RunPod LLM integration
"""

import os
import chainlit as cl
import httpx
from typing import Optional, Dict, Any
import asyncio

# Configuration
AI_CHAT_SERVICE_URL = os.getenv(
    "AI_CHAT_SERVICE_URL",
    "http://localhost:8000"
)
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "60"))
DEFAULT_MODE = os.getenv("DEFAULT_CHAT_MODE", "unified")

# API client
class ChatAPIClient:
    """Client for AI Chat Service API"""

    def __init__(self, base_url: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def send_message(
        self,
        message: str,
        mode: str = "unified",
        include_search: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send message to AI Chat Service"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/chat/unified",
                json={
                    "message": message,
                    "mode": mode,
                    "include_search": include_search,
                    "context": context or {}
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"API Error: {e.response.status_code} - {e.response.text}",
                "metadata": {"error": str(e)}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection Error: {str(e)}",
                "metadata": {"error": str(e)}
            }

    async def get_health(self) -> Dict[str, Any]:
        """Check API health"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def get_modes(self) -> Dict[str, Any]:
        """Get available chat modes"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/chat/modes")
            response.raise_for_status()
            return response.json()
        except Exception:
            return {
                "modes": {
                    "unified": {"name": "Unified Search & Chat", "icon": "🚀"},
                    "chat": {"name": "AI Conversation", "icon": "💬"},
                    "search": {"name": "Document Search", "icon": "🔍"},
                    "research": {"name": "Research Assistant", "icon": "📚"}
                }
            }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global API client
api_client = ChatAPIClient(AI_CHAT_SERVICE_URL, API_TIMEOUT)


@cl.on_chat_start
async def start():
    """Initialize chat session"""

    # Check backend health
    health = await api_client.get_health()

    if health.get("status") == "healthy":
        welcome_msg = f"""# Welcome to AI Chat System! 🚀

**Status:** ✅ Connected to backend
**Backend:** {AI_CHAT_SERVICE_URL}
**Mode:** {DEFAULT_MODE.title()}

I'm your AI assistant powered by RunPod. I can help you with:
- 🔍 **Search** - Find information in documents
- 💬 **Chat** - Have natural conversations
- 📚 **Research** - Conduct comprehensive research
- 🚀 **Unified** - Combine search with intelligent responses

Just type your message to get started!
"""
    else:
        welcome_msg = f"""# AI Chat System ⚠️

**Status:** ⚠️ Backend connection issue
**Backend:** {AI_CHAT_SERVICE_URL}
**Error:** {health.get('error', 'Unknown')}

Please check that the AI Chat Service is running and accessible.
"""

    await cl.Message(content=welcome_msg).send()

    # Store session state
    cl.user_session.set("mode", DEFAULT_MODE)
    cl.user_session.set("conversation_history", [])


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages"""

    # Get session state
    mode = cl.user_session.get("mode", DEFAULT_MODE)
    conversation_history = cl.user_session.get("conversation_history", [])

    # Show typing indicator
    msg = cl.Message(content="")
    await msg.send()

    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": message.content
    })

    # Send to backend API
    response = await api_client.send_message(
        message=message.content,
        mode=mode,
        include_search=mode in ["unified", "search", "research"],
        context={
            "conversation_history": conversation_history[-10:]  # Last 10 messages
        }
    )

    if response.get("success"):
        # Extract response content
        response_content = response.get("message", "No response received")
        search_results = response.get("search_results", [])
        metadata = response.get("metadata", {})

        # Format response
        formatted_response = response_content

        # Add search results if available
        if search_results and len(search_results) > 0:
            formatted_response += "\n\n---\n\n### 📚 Search Results\n\n"
            for idx, result in enumerate(search_results[:3], 1):
                title = result.get("title", "Document")
                score = result.get("score", 0) * 100
                formatted_response += f"**{idx}. {title}** (Relevance: {score:.1f}%)\n"

        # Add metadata footer
        processing_time = metadata.get("processing_time_ms", 0)
        search_count = metadata.get("search_results_count", 0)

        footer = f"\n\n---\n*Processed in {processing_time:.0f}ms"
        if search_count > 0:
            footer += f" · {search_count} documents searched"
        footer += f" · Mode: {mode}*"

        formatted_response += footer

        # Update message
        msg.content = formatted_response
        await msg.update()

        # Add to conversation history
        conversation_history.append({
            "role": "assistant",
            "content": response_content
        })

    else:
        # Error handling
        error_msg = response.get("message", "Unknown error occurred")
        msg.content = f"❌ **Error:**\n\n{error_msg}\n\nPlease try again or check the backend logs."
        await msg.update()

    # Update session
    cl.user_session.set("conversation_history", conversation_history)


@cl.on_settings_update
async def settings_update(settings):
    """Handle settings changes"""
    mode = settings.get("mode", DEFAULT_MODE)
    cl.user_session.set("mode", mode)

    await cl.Message(
        content=f"✅ Chat mode updated to: **{mode.title()}**"
    ).send()


@cl.on_chat_end
async def end():
    """Cleanup on chat end"""
    pass


# Settings configuration
@cl.set_chat_profiles
async def chat_profiles():
    """Define chat profiles (modes)"""
    modes = await api_client.get_modes()

    profiles = []
    for mode_id, mode_info in modes.get("modes", {}).items():
        profiles.append(
            cl.ChatProfile(
                name=mode_id,
                markdown_description=f"{mode_info.get('icon', '💬')} **{mode_info.get('name', mode_id.title())}**\n\n{mode_info.get('description', '')}",
                icon=mode_info.get('icon', '💬')
            )
        )

    return profiles if profiles else [
        cl.ChatProfile(
            name="unified",
            markdown_description="🚀 **Unified Search & Chat**\n\nCombines document search with conversational AI",
            icon="🚀"
        ),
        cl.ChatProfile(
            name="chat",
            markdown_description="💬 **AI Conversation**\n\nPure conversational AI without search",
            icon="💬"
        ),
        cl.ChatProfile(
            name="search",
            markdown_description="🔍 **Document Search**\n\nDirect document search with results",
            icon="🔍"
        ),
        cl.ChatProfile(
            name="research",
            markdown_description="📚 **Research Assistant**\n\nComprehensive research with analysis",
            icon="📚"
        )
    ]


@cl.on_chat_profile
async def on_chat_profile(profile: cl.ChatProfile):
    """Handle profile (mode) changes"""
    mode = profile.name
    cl.user_session.set("mode", mode)

    await cl.Message(
        content=f"✅ Switched to **{profile.markdown_description.split('**')[1]}** mode"
    ).send()


# Health check endpoint for Railway
@cl.on_chat_resume
async def on_resume(thread_id: str):
    """Resume chat session"""
    await cl.Message(
        content="Welcome back! Your conversation has been resumed."
    ).send()
