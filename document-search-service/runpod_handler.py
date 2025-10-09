"""RunPod serverless handler for document search service."""
import runpod
import asyncio
from typing import Dict, Any
from app.main import app
from app.search.ultra_fast_engine import UltraFastSearchEngine
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize search engine
search_engine = None

def init_engine():
    """Initialize the search engine."""
    global search_engine
    if search_engine is None:
        logger.info("Initializing search engine...")
        search_engine = UltraFastSearchEngine()
        logger.info("Search engine initialized")
    return search_engine

async def handle_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Handle search request."""
    engine = init_engine()
    results = await engine.search(query=query, top_k=top_k)
    return {
        "results": [
            {
                "text": r.text,
                "score": r.score,
                "metadata": r.metadata
            }
            for r in results
        ]
    }

async def handle_upload(file_content: bytes, filename: str, metadata: Dict = None) -> Dict[str, Any]:
    """Handle document upload."""
    engine = init_engine()
    doc_id = await engine.add_document(
        content=file_content,
        filename=filename,
        metadata=metadata or {}
    )
    return {"document_id": doc_id, "status": "uploaded"}

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler function.

    Expected input:
    {
        "input": {
            "action": "search" | "upload" | "health",
            "query": "search query" (for search),
            "top_k": 5 (optional, for search),
            "file_content": "base64_encoded_content" (for upload),
            "filename": "document.pdf" (for upload),
            "metadata": {} (optional, for upload)
        }
    }
    """
    try:
        input_data = event.get("input", {})
        action = input_data.get("action", "search")

        logger.info(f"Handling action: {action}")

        if action == "health":
            return {"status": "healthy", "service": "document-search"}

        elif action == "search":
            query = input_data.get("query")
            if not query:
                return {"error": "Query is required for search action"}

            top_k = input_data.get("top_k", 5)

            # Run async search
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(handle_search(query, top_k))
            loop.close()

            return result

        elif action == "upload":
            import base64

            file_content_b64 = input_data.get("file_content")
            filename = input_data.get("filename")

            if not file_content_b64 or not filename:
                return {"error": "file_content and filename are required for upload action"}

            # Decode base64 content
            file_content = base64.b64decode(file_content_b64)
            metadata = input_data.get("metadata", {})

            # Run async upload
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(handle_upload(file_content, filename, metadata))
            loop.close()

            return result

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    logger.info("Starting RunPod serverless handler...")
    runpod.serverless.start({"handler": handler})
