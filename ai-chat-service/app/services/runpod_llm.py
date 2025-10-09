"""
RunPod LLM Service
Wrapper for RunPod API endpoints to replace Ollama local models
"""

import httpx
import asyncio
from typing import Optional, Dict, Any, AsyncIterator
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger(__name__)


class RunPodLLMService:
    """Service for interacting with RunPod LLM API"""

    def __init__(
        self,
        api_key: str,
        endpoint_id: str = "p94hyu5zhxdl82",
        base_url: str = "https://api.runpod.ai/v2",
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize RunPod LLM service

        Args:
            api_key: RunPod API key (Bearer token)
            endpoint_id: RunPod endpoint ID
            base_url: Base URL for RunPod API
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

        self.endpoint_url = f"{base_url}/{endpoint_id}/runsync"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        logger.info(
            "RunPod LLM service initialized",
            endpoint_id=endpoint_id,
            endpoint_url=self.endpoint_url
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text completion from RunPod LLM

        Args:
            prompt: Input prompt for the model
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Nucleus sampling parameter
            stream: Whether to stream the response
            **kwargs: Additional sampling parameters

        Returns:
            Dict containing the generated text and metadata
        """
        payload = {
            "input": {
                "prompt": prompt,
                "sampling_params": {
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    **kwargs
                }
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(
                    "Sending request to RunPod",
                    prompt_length=len(prompt),
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                response = await client.post(
                    self.endpoint_url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()

                result = response.json()

                logger.info(
                    "RunPod generation completed",
                    status_code=response.status_code,
                    response_time_ms=response.elapsed.total_seconds() * 1000
                )

                # Extract text from RunPod response format
                # Adjust based on actual RunPod response structure
                generated_text = self._extract_text(result)

                return {
                    "success": True,
                    "text": generated_text,
                    "raw_response": result,
                    "metadata": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(generated_text.split()) if generated_text else 0,
                        "model": "runpod-llm",
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                }

        except httpx.HTTPStatusError as e:
            logger.error(
                "RunPod API HTTP error",
                status_code=e.response.status_code,
                error=str(e)
            )
            raise Exception(f"RunPod API error: {e.response.status_code} - {e.response.text}")

        except httpx.TimeoutException:
            logger.error("RunPod API timeout", timeout=self.timeout)
            raise Exception(f"RunPod API timeout after {self.timeout}s")

        except Exception as e:
            logger.error("RunPod API unexpected error", error=str(e))
            raise Exception(f"RunPod API error: {str(e)}")

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream text completion from RunPod LLM

        Note: This is a wrapper - actual streaming depends on RunPod API support
        For now, it yields the complete response

        Args:
            prompt: Input prompt for the model
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Yields:
            Chunks of generated text
        """
        result = await self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
            **kwargs
        )

        if result.get("success"):
            text = result.get("text", "")
            # Simulate streaming by yielding in chunks
            chunk_size = 50
            words = text.split()
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                yield chunk
                await asyncio.sleep(0.05)  # Small delay to simulate streaming

    async def chat(
        self,
        messages: list[Dict[str, str]],
        max_tokens: int = 150,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chat completion using RunPod LLM

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Dict containing the response and metadata
        """
        # Convert messages to a single prompt
        prompt = self._messages_to_prompt(messages)

        return await self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

    def _messages_to_prompt(self, messages: list[Dict[str, str]]) -> str:
        """
        Convert chat messages to a single prompt string

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt_parts.append("Assistant:")

        return "\n".join(prompt_parts)

    def _extract_text(self, response: Dict[str, Any]) -> str:
        """
        Extract generated text from RunPod response

        Args:
            response: Raw RunPod API response

        Returns:
            Extracted text string
        """
        # Adjust based on actual RunPod response structure
        # Common patterns:

        # Pattern 1: Direct output field
        if "output" in response:
            output = response["output"]
            if isinstance(output, str):
                return output
            elif isinstance(output, dict) and "text" in output:
                return output["text"]
            elif isinstance(output, dict) and "generated_text" in output:
                return output["generated_text"]

        # Pattern 2: Nested in result
        if "result" in response:
            result = response["result"]
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and "text" in result:
                return result["text"]

        # Pattern 3: Choices format (OpenAI-like)
        if "choices" in response and len(response["choices"]) > 0:
            first_choice = response["choices"][0]
            if "text" in first_choice:
                return first_choice["text"]
            elif "message" in first_choice and "content" in first_choice["message"]:
                return first_choice["message"]["content"]

        # Fallback: return full response as string
        logger.warning("Could not extract text from RunPod response, returning raw response")
        return str(response)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check RunPod API health

        Returns:
            Dict with health status
        """
        try:
            result = await self.generate(
                prompt="Hello",
                max_tokens=5,
                temperature=0.1
            )

            return {
                "healthy": True,
                "service": "runpod_llm",
                "endpoint_id": self.endpoint_id,
                "response_time_ms": result.get("metadata", {}).get("response_time_ms", 0)
            }
        except Exception as e:
            logger.error("RunPod health check failed", error=str(e))
            return {
                "healthy": False,
                "service": "runpod_llm",
                "endpoint_id": self.endpoint_id,
                "error": str(e)
            }
