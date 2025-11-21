import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional
from groq import Groq
import aiohttp

logger = logging.getLogger('Providers')

class AIProvider(ABC):
    """Base class for AI providers"""
    
    def __init__(self, model_name: str, system_instruction: str, config: Dict[str, Any], http_session: Optional[aiohttp.ClientSession] = None):
        self.model_name = model_name
        self.system_instruction = system_instruction
        self.config = config
        self.http_session = http_session
    
    @abstractmethod
    def initialize(self, history: List[Dict[str, Any]]) -> None:
        pass
    
    @abstractmethod
    async def generate_response(self, content: Any) -> str:
        pass

class GeminiProvider(AIProvider):
    """Google Gemini provider using new SDK"""
    
    def __init__(self, model_name: str, system_instruction: str, config: Dict[str, Any], http_session: Optional[aiohttp.ClientSession] = None):
        super().__init__(model_name, system_instruction, config, http_session)
        self.client = None
        self._history = []
        self._last_model = None
    
    def initialize(self, history: List[Dict[str, Any]]) -> None:
        """Initialize Gemini client with history"""
        # Skip if already initialized with same model
        if self.client and self._last_model == self.model_name:
            return
        
        try:
            from google import genai
        except ImportError:
            raise ValueError("google-genai not installed. Run: pip install google-genai")
        
        api_key = self.config.get('gemini_api_key')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        
        self.client = genai.Client(api_key=api_key)
        self._history = self._convert_history(history) if history else []
        self._last_model = self.model_name
        logger.info(f"Initialized Gemini with {len(self._history)} messages")
    
    def _convert_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert database history to Gemini format"""
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
        """Generate response from Gemini"""
        if not self.client:
            raise ValueError("Gemini not initialized")
        
        contents = self._history.copy()
        
        # Process input parts (text and images)

        current_parts = []
        
        if isinstance(parts, list):
            from google.genai import types
            import io
            
            for part in parts:
                if isinstance(part, str):
                    if part.strip():
                        # Ensure text is not empty
                        current_parts.append(types.Part.from_text(text=part))
                elif hasattr(part, 'save'):  # Check for PIL Image
                    try:
                        img_byte_arr = io.BytesIO()
                        part.save(img_byte_arr, format='JPEG')
                        img_bytes = img_byte_arr.getvalue()
                        
                        # Only add if we have valid image data
                        if img_bytes and len(img_bytes) > 0:
                            current_parts.append(types.Part.from_bytes(
                                data=img_bytes,
                                mime_type='image/jpeg'
                            ))
                        else:
                            logger.warning("Skipping empty image data")
                    except Exception as img_err:
                        logger.error(f"Image processing error: {img_err}")
        else:
            # Fallback for string input
            from google.genai import types
            current_parts.append(types.Part.from_text(text=str(parts)))
            
        if current_parts:
            contents.append(types.Content(role="user", parts=current_parts))
        else:
             # Handle empty content case
             from google.genai import types
             contents.append(types.Content(role="user", parts=[types.Part.from_text(text=".")]))
        
        try:
            # Build tools config for Gemini 3 and newer models
            tools = []
            # Only enable tools if explicitly supported/requested to avoid errors
            if "gemini-2" in self.model_name or "gemini-1.5-pro" in self.model_name:
                tools = [
                    {"google_search": {}},  # Enable Google Search/Grounding
                ]
                # Code execution can be risky or unsupported on some models, keeping it optional
                if "code" in self.model_name or "gemini-2.0-flash-thinking" in self.model_name:
                     tools.append({"code_execution": {}})
            
            config = {
                "system_instruction": {"parts": [{"text": self.system_instruction}]},
                "temperature": 1,
                "top_p": 0.95,
                "max_output_tokens": 8192,
            }
            
            # Add tools if supported
            if tools:
                config["tools"] = tools
                logger.info(f"Enabled Gemini tools: {len(tools)}")
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=contents,
                config=config
            )
            
            if response.candidates and response.candidates[0].content.parts:
                response_text = response.candidates[0].content.parts[0].text
                
                # Add to history for next turn
                from google.genai import types
                self._history.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=" ".join([str(p) for p in parts if isinstance(p, str)]))]
                ))
                self._history.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=response_text)]
                ))
                
                return response_text
            
            # Handle empty response gracefully
            logger.warning("Gemini returned empty response, using fallback")
            return "I apologize, but I couldn't generate a response. Please try again or rephrase your message."
            
        except Exception as e:
            if "503" in str(e) or "429" in str(e):
                logger.warning(f"Gemini API error {e}, retrying...")
                await asyncio.sleep(2)
                try:
                    return await self.generate_response(parts)
                except Exception as retry_e:
                    logger.error(f"Gemini retry failed: {retry_e}")
                    raise retry_e
            
            logger.error(f"Gemini error: {e}")
            raise


class GroqProvider(AIProvider):
    """Groq provider"""
    
    def __init__(self, model_name: str, system_instruction: str, config: Dict[str, Any], http_session: Optional[aiohttp.ClientSession] = None):
        super().__init__(model_name, system_instruction, config, http_session)
        self.client = None
        self.messages = []
    
    def initialize(self, history: List[Dict[str, Any]]) -> None:
        """Initialize Groq client with history"""
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
        
        logger.info(f"Initialized Groq with {len(self.messages)} messages")

    def _get_max_tokens_for_model(self) -> int:
        """Dynamic max tokens based on model"""
        if "8b" in self.model_name.lower():
            return 1024
        elif "70b" in self.model_name.lower():
            return 4096
        return 8192
    
    async def generate_response(self, content: str) -> str:
        """Generate response from Groq"""
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
    
    def __init__(self, model_name: str, system_instruction: str, config: Dict[str, Any], http_session: Optional[aiohttp.ClientSession] = None):
        super().__init__(model_name, system_instruction, config, http_session)
        self.messages = []
    
    def initialize(self, history: List[Dict[str, Any]]) -> None:
        """Initialize OpenRouter with history"""
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
        
        logger.info(f"Initialized OpenRouter with {len(self.messages)} messages")
    
    async def generate_response(self, content: str) -> str:
        """Generate response from OpenRouter"""
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
            if self.http_session:
                session = self.http_session
                should_close = False
            else:
                session = aiohttp.ClientSession()
                should_close = True

            try:
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
            finally:
                if should_close:
                    await session.close()
                    
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise
