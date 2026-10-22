from typing import Optional
from app.services.llm.base import LLMProvider, LLMProviderError
from app.services.llm.mock import MockLLMProvider
from app.services.llm.openai import OpenAILLMProvider
from app.services.llm.gemini import GeminiLLMProvider
from app.services.llm.anthropic import AnthropicLLMProvider
from app.core.config import settings
from app.core.logging import logger

def get_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None
) -> LLMProvider:
    """
    Factory to retrieve an LLM provider.
    Falls back to MockLLMProvider if requested provider is missing API keys.
    """
    # Use config defaults if not explicitly provided
    provider = (provider_name or settings.DEFAULT_LLM_PROVIDER or "mock").lower()
    model = model_name or settings.DEFAULT_LLM_MODEL or "mock-model"

    try:
        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                logger.warning("OpenAI API key missing. Falling back to Mock LLM provider.")
                return MockLLMProvider(model_name="mock-openai-fallback")
            return OpenAILLMProvider(model_name=model)
            
        elif provider == "gemini":
            if not settings.GEMINI_API_KEY:
                logger.warning("Gemini API key missing. Falling back to Mock LLM provider.")
                return MockLLMProvider(model_name="mock-gemini-fallback")
            return GeminiLLMProvider(model_name=model)
            
        elif provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                logger.warning("Anthropic API key missing. Falling back to Mock LLM provider.")
                return MockLLMProvider(model_name="mock-anthropic-fallback")
            return AnthropicLLMProvider(model_name=model)
            
        elif provider == "mock":
            return MockLLMProvider(model_name=model)
            
        else:
            logger.warning(f"Unknown LLM provider '{provider}'. Falling back to Mock LLM provider.")
            return MockLLMProvider(model_name=model)
            
    except Exception as e:
        logger.error(f"Error building LLM provider {provider}: {e}. Falling back to Mock provider.")
        return MockLLMProvider(model_name="mock-emergency-fallback")
