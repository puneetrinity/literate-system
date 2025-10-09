"""RunPod serverless handler for AI Chat Service."""
import runpod
import asyncio
import json
from typing import Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import FastAPI app
from app.main import app
from fastapi.testclient import TestClient

# Create test client for internal routing
client = TestClient(app)

async def handle_chat(message: str, mode: str = "unified", session_id: str = None, user_id: str = None) -> Dict[str, Any]:
    """Handle chat request."""
    payload = {
        "message": message,
        "mode": mode,
        "session_id": session_id or "runpod-session",
        "user_id": user_id or "runpod-user"
    }

    response = client.post("/api/v1/chat/unified", json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Chat request failed: {response.status_code}", "detail": response.text}

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler for AI Chat Service.

    Expected input:
    {
        "input": {
            "action": "chat" | "health",
            "message": "user message",
            "mode": "unified" | "chat" | "search" | "research",
            "session_id": "optional-session-id",
            "user_id": "optional-user-id"
        }
    }
    """
    try:
        input_data = event.get("input", {})
        action = input_data.get("action", "chat")

        logger.info(f"Handling action: {action}")

        if action == "health":
            response = client.get("/health")
            return response.json()

        elif action == "chat":
            message = input_data.get("message")
            if not message:
                return {"error": "Message is required for chat action"}

            mode = input_data.get("mode", "unified")
            session_id = input_data.get("session_id")
            user_id = input_data.get("user_id")

            # Run async chat
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(handle_chat(message, mode, session_id, user_id))
            loop.close()

            return result

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    logger.info("Starting RunPod serverless handler for AI Chat Service...")
    runpod.serverless.start({"handler": handler})
