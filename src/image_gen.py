"""
Image Generation Module using Pollinations.ai
Free, no-key API for high-quality image generation
"""
import aiohttp
import urllib.parse
import random
import logging
from typing import Optional

logger = logging.getLogger('ImageGen')

class ImageGenerator:
    """Handles image generation requests"""
    
    BASE_URL = "https://image.pollinations.ai/prompt/"
    
    STYLES = {
        "Realistic": "realistic, highly detailed, 8k, photorealistic",
        "Anime": "anime style, studio ghibli, vibrant colors",
        "3D": "3d render, unreal engine 5, octane render",
        "Painting": "oil painting, artistic, brush strokes",
        "Cyberpunk": "cyberpunk, neon lights, futuristic",
        "Vintage": "vintage, retro, 1980s style, grain"
    }
    
    @staticmethod
    async def generate(prompt: str, style: str = "Realistic", seed: Optional[int] = None, width: int = 1024, height: int = 1024) -> str:
        """
        Generate image URL from prompt
        Returns the direct URL to the image (Pollinations generates on the fly)
        """
        if seed is None:
            seed = random.randint(0, 999999)
            
        # Enhance prompt with style
        style_prompt = ImageGenerator.STYLES.get(style, "")
        full_prompt = f"{prompt}, {style_prompt}" if style_prompt else prompt
        
        # URL encode prompt
        encoded_prompt = urllib.parse.quote(full_prompt)
        
        # Construct URL
        # Format: https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&seed={seed}&nologo=true
        url = f"{ImageGenerator.BASE_URL}{encoded_prompt}?width={width}&height={height}&seed={seed}&nologo=true&model=flux"
        
        logger.info(f"Generated image URL for prompt: {prompt[:50]}... (Style: {style})")
        return url
