"""RunPod serverless handler for Chainlit Frontend."""
import runpod
import asyncio
import logging
from typing import Dict, Any
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# This handler proxies requests to the backend AI Chat Service
# For RunPod deployment, Chainlit should run as a regular web service
# This handler is for API-based interactions

async def handle_message(message: str, backend_url: str, mode: str = "unified") -> Dict[str, Any]:
    """Handle chat message by forwarding to backend."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{backend_url}/api/v1/chat/unified",
                json={
                    "message": message,
                    "mode": mode,
                    "session_id": "runpod-session",
                    "user_id": "runpod-user"
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Backend request failed: {str(e)}")
            return {"error": str(e)}

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler for Chainlit Frontend.

    Expected input:
    {
        "input": {
            "action": "message" | "health",
            "message": "user message",
            "backend_url": "https://your-ai-chat-service-url",
            "mode": "unified" | "chat" | "search" | "research"
        }
    }
    """
    try:
        input_data = event.get("input", {})
        action = input_data.get("action", "message")

        logger.info(f"Handling action: {action}")

        if action == "health":
            return {"status": "healthy", "service": "chainlit-frontend"}

        elif action == "message":
            message = input_data.get("message")
            backend_url = input_data.get("backend_url")

            if not message:
                return {"error": "Message is required"}

            if not backend_url:
                return {"error": "backend_url is required"}

            mode = input_data.get("mode", "unified")

            # Run async message handling
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(handle_message(message, backend_url, mode))
            loop.close()

            return result

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    logger.info("Starting RunPod serverless handler for Chainlit Frontend...")
    runpod.serverless.start({"handler": handler})
