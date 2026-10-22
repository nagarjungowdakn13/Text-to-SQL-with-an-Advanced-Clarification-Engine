import json
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
import google.generativeai as genai
from app.services.llm.base import LLMProvider, LLMProviderError
from app.core.config import settings
from app.core.logging import logger

T = TypeVar("T", bound=BaseModel)

class GeminiLLMProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        if not settings.GEMINI_API_KEY:
            raise LLMProviderError("GEMINI_API_KEY is not set in settings.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        logger.info(f"Initialized GeminiLLMProvider with model {model_name}")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )
            response = model.generate_content(prompt, generation_config=config)
            if not response.text:
                raise LLMProviderError("Received empty response from Gemini API.")
            return response.text
        except Exception as e:
            logger.error(f"Error in Gemini generate: {e}")
            raise LLMProviderError(f"Gemini API request failed: {e}")

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
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            
            # Request JSON output
            # We provide instructions to output valid JSON matching the model's schema.
            # Some versions of google-generativeai support response_schema directly.
            # Let's pass the schema to the config for structured generation.
            schema_dict = response_model.model_json_schema()
            
            config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
                response_schema=schema_dict,
                **kwargs
            )
            
            response = model.generate_content(prompt, generation_config=config)
            text = response.text
            
            if not text:
                raise LLMProviderError("Received empty response from Gemini API.")
                
            # Parse and validate the response
            parsed_data = json.loads(text)
            return response_model.model_validate(parsed_data)
        except Exception as e:
            logger.error(f"Error in Gemini structured generate: {e}")
            # Try a recovery step if JSON was slightly malformed (e.g. wrapped in markdown block)
            try:
                if 'response' in locals() and response.text:
                    cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                    parsed_data = json.loads(cleaned_text)
                    return response_model.model_validate(parsed_data)
            except Exception as inner_e:
                logger.error(f"Structured validation recovery also failed: {inner_e}")
            raise LLMProviderError(f"Gemini structured generation failed: {e}")
