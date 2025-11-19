import re
import logging
import asyncio
from typing import List, Any, Optional
import aiohttp
import yt_dlp
from PIL import Image
import io

logger = logging.getLogger('Utils')

def sanitize_discord_markdown(text: str) -> str:
    """Fix markdown issues, especially tables and code blocks"""
    lines = text.split('\n')
    in_code_block = False
    
    for i, line in enumerate(lines):
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
    
    if in_code_block:
        lines.append('```')
        logger.warning("Fixed unclosed code block")
    
    # Remove <think> tags from reasoning models
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = '\n'.join(lines)
    text = _convert_markdown_tables(text)
    text = re.sub(r'(?<!<)(https?://\S+)(?!>)', r'<\1>', text)
    
    return text

def _convert_markdown_tables(text: str) -> str:
    """Convert markdown tables to formatted text"""
    table_pattern = r'(\|.*?\|\n\|(?:\s*[:-]+[-:| ]+\|\n)(?:\|.*?\|\n)+)'
    
    def replace_table(match):
        return f"```\n📊 Table Data:\n{match.group(1)}```"
    
    return re.sub(table_pattern, replace_table, text, flags=re.MULTILINE)

def optimize_response_length(query: str, response: str) -> str:
    """Intelligently trim responses"""
    query_lower = query.lower().strip()
    
    simple_patterns = [
        r'^(what|who|when|where|is|are|can|do|does|did)\s',
        r'\?$',
        r'^(yes|no)\s',
        r'^(define|explain)\s+\w+$',
    ]
    
    is_simple = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in simple_patterns)
    
    if is_simple and len(response) > 800:
        paragraphs = response.split('\n\n')
        essential = paragraphs[0] if paragraphs else response
        
        if len(essential) > 600:
            sentences = essential.split('.')
            essential = '. '.join(sentences[:4]) + '.'
        
        if len(response) > len(essential):
            essential += "\n\n*Ask for more details if needed.*"
        
        logger.info(f"Optimized response: {len(response)} -> {len(essential)} chars")
        return essential
    
    return response

def estimate_tokens(text: str, encoding: Optional[Any] = None) -> int:
    """Better token estimation"""
    if encoding:
        try:
            return len(encoding.encode(str(text)))
        except:
            pass
    
    text = str(text)
    word_tokens = len(text.split()) * 1.3
    char_tokens = len(text) * 0.25
    return int(max(word_tokens, char_tokens))

def split_message_smart(text: str, limit: int = 1900) -> List[str]:
    """Split message preserving code blocks"""
    if len(text) <= limit:
        return [text]
    
    parts = []
    current_part = ""
    in_code_block = False
    
    lines = text.split('\n')
    
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
        
        if len(current_part) + len(line) + 1 > limit:
            if in_code_block:
                current_part += '\n```'
                parts.append(current_part)
                current_part = '```\n' + line
            else:
                parts.append(current_part)
                current_part = line
        else:
            if current_part:
                current_part += '\n'
            current_part += line
    
    if current_part:
        if in_code_block:
            current_part += '\n```'
        parts.append(current_part)
    
    return parts

async def download_image(url: str) -> Optional[Image.Image]:
    """Download image from URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return Image.open(io.BytesIO(await resp.read()))
    except Exception as e:
        logger.error(f"Image download error: {e}")
    return None

async def download_file(url: str) -> Optional[bytes]:
    """Download file from URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception as e:
        logger.error(f"File download error: {e}")
    return None

def extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})(?:\?|$)',
        r'youtube\.com/live/([a-zA-Z0-9_-]{11})',
        r'&v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def get_youtube_transcript(video_id: str) -> str:
    """Get YouTube video transcript"""
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'skip_download': True,
        }
        
        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        info = await asyncio.get_event_loop().run_in_executor(None, extract)
        
        title = info.get('title', 'Unknown')
        description = info.get('description', '')[:500]
        duration = info.get('duration', 0)
        uploader = info.get('uploader', 'Unknown')
        
        transcript = ""
        subs = info.get('subtitles', {}) or info.get('automatic_captions', {})
        
        if subs:
            for lang in ['en', 'en-US', 'en-GB']:
                if lang in subs:
                    for sub in subs[lang]:
                        if sub.get('ext') == 'json3':
                            try:
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(sub['url']) as resp:
                                        if resp.status == 200:
                                            data = await resp.json()
                                            texts = []
                                            for event in data.get('events', []):
                                                for seg in event.get('segs', []):
                                                    if 'utf8' in seg:
                                                        texts.append(seg['utf8'])
                                            transcript = ' '.join(texts).replace('\n', ' ')
                                            break
                            except Exception as e:
                                logger.warning(f"Subtitle error: {e}")
                    if transcript:
                        break
        
        duration_str = f"{duration//60}:{duration%60:02d}" if duration else "Unknown"
        
        result = f"""📺 **{title}**
👤 {uploader} | ⏱️ {duration_str}
📝 {description}

{'📄 ' + transcript[:3000] if transcript else '⚠️ No transcript available'}"""
        
        return result
        
    except Exception as e:
        logger.error(f"YT error for {video_id}: {e}", exc_info=True)
        return f"[YouTube: {video_id}] Error: {str(e)[:100]}. Video might be private, deleted, or missing subtitles."


# NEW: Video URL extraction and processing
async def extract_video_url(text: str) -> Optional[str]:
    """Extract video URL from various cloud providers"""
    patterns = [
        r'(https?://[^\s]+\.mp4)',
        r'(https?://[^\s]+\.webm)',
        r'(https?://[^\s]+\.mov)',
        r'(https?://drive\.google\.com/[^\s]+)',
        r'(https?://.*dropbox\.com/[^\s]+)',
        r'(https?://streamable\.com/[a-zA-Z0-9]+)',
        r'(https?://.*vimeo\.com/[^\s]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

async def get_video_info(url: str) -> Optional[dict]:
    """Get video metadata - basic implementation"""
    try:
        # Streamable specific handling
        if "streamable.com" in url:
            # Streamable requires scraping or API, for now we'll just return the URL
            # The model can often access the public page directly if search is enabled
            return {
                'title': 'Streamable Video',
                'description': f'Video hosted on Streamable: {url}',
                'url': url,
                'provider': 'streamable'
            }
            
        # For now, return basic info for others
        return {
            'title': 'Video',
            'description': f'Video from {url[:50]}...',
            'url': url
        }
    except Exception as e:
        logger.error(f"Video info error: {e}")
        return None