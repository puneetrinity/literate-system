"""
OpenAI-compatible API adapter for LobeChat integration
Provides OpenAI-format endpoints that route to our RunPod-powered chat service
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time
import json
import asyncio
from datetime import datetime
from app.api.chat_unified import unified_chat, ChatRequest, get_runpod_service
from app.core.config import get_settings

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible API"])


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: Optional[int] = 500
    stream: bool = False


@router.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint
    Routes to our unified_chat with RunPod backend
    """
    # Extract conversation context
    user_message = ""
    system_prompt = ""
    conversation_history = []

    for msg in request.messages:
        if msg.role == "system":
            system_prompt = msg.content
        elif msg.role == "user":
            user_message = msg.content
        conversation_history.append({"role": msg.role, "content": msg.content})

    # Get the last user message for processing
    if not user_message:
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break

    if not user_message:
        return {
            "error": {
                "message": "No user message found in request",
                "type": "invalid_request_error",
                "code": "invalid_request"
            }
        }

    # Handle streaming vs non-streaming
    if request.stream:
        return StreamingResponse(
            stream_chat_completion(
                user_message=user_message,
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ),
            media_type="text/event-stream"
        )
    else:
        # Non-streaming response
        return await create_completion_response(
            user_message=user_message,
            system_prompt=system_prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )


async def create_completion_response(
    user_message: str,
    system_prompt: str,
    model: str,
    temperature: float,
    max_tokens: int
) -> Dict[str, Any]:
    """Create a non-streaming chat completion response"""
    settings = get_settings()

    try:
        # Try RunPod LLM first
        if settings.llm_provider == "runpod":
            runpod_service = get_runpod_service()
            if runpod_service:
                # Construct full prompt
                full_prompt = ""
                if system_prompt:
                    full_prompt = f"System: {system_prompt}\n\n"
                full_prompt += f"User: {user_message}\n\nAssistant:"

                result = await runpod_service.generate(
                    prompt=full_prompt,
                    max_tokens=max_tokens or 500,
                    temperature=temperature
                )

                if result.get("success"):
                    response_text = result.get("text", "").strip()

                    return {
                        "id": f"chatcmpl-{int(time.time() * 1000)}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": response_text
                                },
                                "finish_reason": "stop"
                            }
                        ],
                        "usage": {
                            "prompt_tokens": len(user_message.split()),
                            "completion_tokens": len(response_text.split()),
                            "total_tokens": len(user_message.split()) + len(response_text.split())
                        }
                    }

        # Fallback to unified chat endpoint
        chat_request = ChatRequest(
            message=user_message,
            mode="unified",
            include_search=False  # For chat completion, don't include search by default
        )

        result = await unified_chat(chat_request)

        return {
            "id": f"chatcmpl-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.message
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(result.message.split()),
                "total_tokens": len(user_message.split()) + len(result.message.split())
            }
        }

    except Exception as e:
        return {
            "error": {
                "message": str(e),
                "type": "server_error",
                "code": "internal_error"
            }
        }


async def stream_chat_completion(
    user_message: str,
    system_prompt: str,
    conversation_history: List[Dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int
):
    """Stream chat completion responses in OpenAI SSE format"""
    settings = get_settings()

    try:
        # Construct full prompt
        full_prompt = ""
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\n"
        full_prompt += f"User: {user_message}\n\nAssistant:"

        # Try RunPod streaming
        if settings.llm_provider == "runpod":
            runpod_service = get_runpod_service()
            if runpod_service:
                async for chunk in runpod_service.generate_stream(
                    prompt=full_prompt,
                    max_tokens=max_tokens or 500,
                    temperature=temperature
                ):
                    # Format as OpenAI SSE
                    sse_data = {
                        "id": f"chatcmpl-{int(time.time() * 1000)}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "content": chunk
                                },
                                "finish_reason": None
                            }
                        ]
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                    await asyncio.sleep(0.01)

                # Send final chunk
                final_chunk = {
                    "id": f"chatcmpl-{int(time.time() * 1000)}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }
                    ]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
                return

        # Fallback: use non-streaming and simulate streaming
        result = await create_completion_response(
            user_message=user_message,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        if "error" not in result:
            content = result["choices"][0]["message"]["content"]

            # Simulate streaming by chunking
            words = content.split()
            chunk_size = 5

            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "

                sse_data = {
                    "id": f"chatcmpl-{int(time.time() * 1000)}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": chunk
                            },
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(sse_data)}\n\n"
                await asyncio.sleep(0.05)

            # Send final chunk
            final_chunk = {
                "id": f"chatcmpl-{int(time.time() * 1000)}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"

    except Exception as e:
        error_data = {
            "error": {
                "message": str(e),
                "type": "server_error",
                "code": "internal_error"
            }
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.get("/models")
async def list_models():
    """List available models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "runpod",
                "permission": [],
                "root": "gpt-3.5-turbo",
                "parent": None
            },
            {
                "id": "gpt-4",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "runpod",
                "permission": [],
                "root": "gpt-4",
                "parent": None
            },
            {
                "id": "gpt-4-turbo",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "runpod",
                "permission": [],
                "root": "gpt-4-turbo",
                "parent": None
            }
        ]
    }


@router.get("/models/{model_id}")
async def retrieve_model(model_id: str):
    """Retrieve a model instance (OpenAI-compatible)"""
    return {
        "id": model_id,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "runpod",
        "permission": [],
        "root": model_id,
        "parent": None
    }
