import json
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from openai import OpenAI
from app.services.llm.base import LLMProvider, LLMProviderError
from app.core.config import settings
from app.core.logging import logger

T = TypeVar("T", bound=BaseModel)

class OpenAILLMProvider(LLMProvider):
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        if not settings.OPENAI_API_KEY:
            raise LLMProviderError("OPENAI_API_KEY is not set in settings.")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info(f"Initialized OpenAILLMProvider with model {model_name}")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            content = response.choices[0].message.content
            if not content:
                raise LLMProviderError("Received empty response from OpenAI API.")
            return content
        except Exception as e:
            logger.error(f"Error in OpenAI generate: {e}")
            raise LLMProviderError(f"OpenAI API request failed: {e}")

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> T:
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            # Check if using OpenAI's native structured outputs support
            try:
                response = self.client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=messages,
                    response_format=response_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                parsed = response.choices[0].message.parsed
                if parsed is None:
                    raise ValueError("Failed to natively parse structured output.")
                return parsed
            except Exception as parse_e:
                logger.warning(f"Native OpenAI JSON parse failed, falling back to JSON schema prompt: {parse_e}")
                # Fallback: request JSON object format
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                content = response.choices[0].message.content
                if not content:
                    raise LLMProviderError("Received empty response from OpenAI API.")
                parsed_data = json.loads(content)
                return response_model.model_validate(parsed_data)
        except Exception as e:
            logger.error(f"Error in OpenAI structured generate: {e}")
            raise LLMProviderError(f"OpenAI structured generation failed: {e}")
