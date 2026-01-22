"""
Inference adapter for LLM providers.
Abstracts different LLM providers behind a common interface.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class InferenceAdapter:
    """
    Adapter for LLM inference providers.
    """
    
    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LLM client."""
        if self.provider == "openai":
            try:
                import openai
                if not self.api_key:
                    logger.warning("OpenAI API key not provided")
                    return
                self._client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        elif self.provider == "anthropic":
            try:
                import anthropic
                if not self.api_key:
                    logger.warning("Anthropic API key not provided")
                    return
                self._client = anthropic.Anthropic(api_key=self.api_key)
                logger.info("Anthropic client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {str(e)}")
    
    async def generate(
        self,
        prompt: str,
        model: str = "gpt-4-turbo-preview",
        max_tokens: int = 100,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate text from prompt.
        
        Returns:
            Dictionary with generated text and metadata
        """
        if not self._client:
            # Stub response for testing
            return {
                "text": "[STUB: LLM client not configured]",
                "model": model,
                "tokens_used": len(prompt.split()) + max_tokens,
                "provider": self.provider
            }
        
        try:
            if self.provider == "openai":
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return {
                    "text": response.choices[0].message.content,
                    "model": model,
                    "tokens_used": response.usage.total_tokens,
                    "provider": self.provider
                }
            elif self.provider == "anthropic":
                response = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return {
                    "text": response.content[0].text,
                    "model": model,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                    "provider": self.provider
                }
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise
