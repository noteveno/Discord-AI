import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Any, Dict  # FIXED: Added missing imports
from groq import Groq
import aiohttp

logger = logging.getLogger('Providers')

class AIProvider(ABC):
    """Base class for AI providers"""
    
    def __init__(self, model_name: str, system_instruction: str, config: Dict[str, Any]):
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.config = config
    
    @abstractmethod
    def initialize(self, history: List[Dict[str, Any]]) -> None:
        pass
    
    @abstractmethod
    async def generate_response(self, content: Any) -> str:
        pass

class GeminiProvider(AIProvider):
    """Google Gemini provider using new SDK"""
    
    def __init__(self, model_name: str, system_instruction: str, config: Dict[str, Any]):
        super().__init__(model_name, system_instruction, config)
        self.client = None
        self._history = []
        self._last_model = None
    
    def initialize(self, history: List[Dict[str, Any]]) -> None:
        if self.client and self._last_model == self.model_name:  # NEW
            return  # Already initialized
        try:
            from google import genai  # Import here to catch if missing
        except ImportError:
            raise ValueError("google-genai not installed. Run: pip install google-genai")
        
        api_key = self.config.get('gemini_api_key')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        
        self.client = genai.Client(api_key=api_key)
        self._history = self._convert_history(history) if history else []
        if not self._history:
            self._history = self._convert_history(history)
            
        self._last_model = self.model_name
        
        if self.client and self._last_model == self.model_name:
            return  # Already initialized

    
    def _convert_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from google.genai import types
        
        contents = []
        for msg in history:
            role = "model" if msg["role"] == "model" else "user"
            parts = [types.Part.from_text(text=msg["content"])]
            
            if msg.get("attachments"):
                for att in msg["attachments"]:
                    parts.append(types.Part.from_text(
                        text=f"[{att['type']}: {att['name']}]"
                    ))
            contents.append(types.Content(parts=parts, role=role))
        return contents
    
    async def generate_response(self, parts: List[Any]) -> str:
        if not self.client:
            raise ValueError("Gemini not initialized")
        
        contents = self._history.copy()
        
        if isinstance(parts, list):
            text_parts = [str(p) for p in parts if isinstance(p, str)]
            image_parts = [p for p in parts if hasattr(p, 'convert')]
            
            current_content = {
                "role": "user",
                "parts": [{"text": " ".join(text_parts)}]
            }
            
            if image_parts:
                try:
                    from google.genai import types
                    for img in image_parts:
                        current_content["parts"].append(types.Part.from_bytes(
                            data=img.tobytes(),
                            mime_type='image/jpeg'
                        ))
                except Exception as img_err:
                    logger.error(f"Image processing error: {img_err}")

            
            contents.append(current_content)
        else:
            contents.append({
                "role": "user",
                "parts": [{"text": str(parts)}]
            })
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=contents,
                config={
                    "system_instruction": {"parts": [{"text": self.system_instruction}]},
                    "temperature": 1,
                    "top_p": 0.95,
                    "max_output_tokens": 8192,
                }
            )
            
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            
                if response.candidates and response.candidates[0].content.parts:
                    response_text = response.candidates[0].content.parts[0].text
                
                    # CRITICAL: Add to history for next turn
                    from google.genai import types
                    self._history.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=response_text)]
                    ))
                
                    return response_text
            
            
            raise ValueError("Empty response from Gemini")
            
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            raise

class GroqProvider(AIProvider):
    """Groq provider"""
    
    def __init__(self, model_name: str, system_instruction: str, config: Dict[str, Any]):
        super().__init__(model_name, system_instruction, config)
        self.client = None
        self.messages = []
    
    def initialize(self, history: List[Dict[str, Any]]) -> None:
        api_key = self.config.get('groq_api_key')
        if not api_key:
            raise ValueError("GROQ_API not set")
        self.client = Groq(api_key=api_key)
        self.messages = [{"role": "system", "content": self.system_instruction}]
        
        for msg in history:
            role = "assistant" if msg["role"] == "model" else "user"
            parts = [msg["content"]]
        
            if msg.get("attachments"):
                for att in msg["attachments"]:
                    parts.append(f"[{att['type']}: {att['name']}]")
        
            self.messages.append({
                "role": role, 
                "content": " ".join(parts)
            })

    def _get_max_tokens_for_model(self) -> int:
        """Dynamic max tokens based on model"""
        if "8b" in self.model_name.lower():
            return 1024
        elif "70b" in self.model_name.lower():
            return 4096
        return 8192

    
    async def generate_response(self, content: str) -> str:
        if not self.client:
            raise ValueError("Groq not initialized")
        
        self.messages.append({"role": "user", "content": content})
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model_name,
                messages=self.messages,
                temperature=1.0,
                max_tokens=self._get_max_tokens_for_model()
            )
            
            response_text = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": response_text})
            return response_text
            
        except Exception as e:
            logger.error(f"Groq error: {e}")
            raise

class OpenRouterProvider(AIProvider):
    """OpenRouter provider"""
    
    def __init__(self, model_name: str, system_instruction: str, config: Dict[str, Any]):
        super().__init__(model_name, system_instruction, config)
        self.messages = []
    
    def initialize(self, history: List[Dict[str, Any]]) -> None:
        self.messages = [{"role": "system", "content": self.system_instruction}]
        
        for msg in history:
            role = "assistant" if msg["role"] == "model" else "user"
            parts = [msg["content"]]
            
            if msg.get("attachments"):
                for att in msg["attachments"]:
                    parts.append(f"[{att['type']}: {att['name']}]")
            
            self.messages.append({
                "role": role,
                "content": " ".join(parts)
            })
    
    async def generate_response(self, content: str) -> str:
        api_key = self.config.get('openrouter_api_key')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        self.messages.append({"role": "user", "content": content})
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Title": "Kamao AI Discord Bot",
            "Content-Type": "application/json",
            "HTTP-Referer": self.config.get('openrouter_referrer', ''),
        }
        
        data = {
            "model": self.model_name,
            "messages": self.messages,
            "temperature": 0.8,
            "max_tokens": 8192
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"OpenRouter error {resp.status}: {error_text}")
                        raise Exception(f"API Error {resp.status}: {error_text[:200]}")
                    
                    result = await resp.json()
                    response_text = result['choices'][0]['message']['content']
                    
                    self.messages.append({"role": "assistant", "content": response_text})
                    return response_text
                    
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise

