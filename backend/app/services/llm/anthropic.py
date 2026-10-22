import json
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
import anthropic
from app.services.llm.base import LLMProvider, LLMProviderError
from app.core.config import settings
from app.core.logging import logger

T = TypeVar("T", bound=BaseModel)

class AnthropicLLMProvider(LLMProvider):
    def __init__(self, model_name: str = "claude-3-5-sonnet-20240620"):
        self.model_name = model_name
        if not settings.ANTHROPIC_API_KEY:
            raise LLMProviderError("ANTHROPIC_API_KEY is not set in settings.")
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        logger.info(f"Initialized AnthropicLLMProvider with model {model_name}")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        try:
            params = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            if system_instruction:
                params["system"] = system_instruction

            response = self.client.messages.create(**params)
            # Content can be a list of text blocks
            content = response.content[0].text
            if not content:
                raise LLMProviderError("Received empty response from Anthropic API.")
            return content
        except Exception as e:
            logger.error(f"Error in Anthropic generate: {e}")
            raise LLMProviderError(f"Anthropic API request failed: {e}")

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
            schema_json = json.dumps(response_model.model_json_schema(), indent=2)
            
            # Formulate structured prompt instructions for Anthropic
            json_instruction = (
                f"You MUST respond ONLY with a raw JSON object that conforms to the following Pydantic schema:\n"
                f"{schema_json}\n"
                f"Do not include any introductory or concluding text, explanations, or markdown code blocks (such as ```json). Output ONLY raw valid JSON."
            )
            
            combined_system = f"{system_instruction}\n\n{json_instruction}" if system_instruction else json_instruction
            
            response_text = self.generate(
                prompt=prompt,
                system_instruction=combined_system,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Clean markdown code blocks if the LLM outputted them despite instructions
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```"):
                lines = cleaned_text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned_text = "\n".join(lines).strip()
                
            parsed_data = json.loads(cleaned_text)
            return response_model.model_validate(parsed_data)
        except Exception as e:
            logger.error(f"Error in Anthropic structured generate: {e}")
            raise LLMProviderError(f"Anthropic structured generation failed: {e}")
