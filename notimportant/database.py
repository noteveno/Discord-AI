import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import gzip
import logging

logger = logging.getLogger('Database')

class ChatDatabase:
    """SQLite-based storage with compression for old messages"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        attachments TEXT,
                        timestamp TEXT NOT NULL,
                        tokens INTEGER DEFAULT 0
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                
                # Initialize token count if not exists
                conn.execute("""
                    INSERT OR IGNORE INTO metadata (key, value) 
                    VALUES ('token_count', '0')
                """)
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing database: {e}")
            raise
    
    def add_message(self, role: str, content: str, 
                   attachments: Optional[List[Dict]] = None, tokens: int = 0):
        """Add message with auto-compression for old data"""
        # Compress content if it's large
        if len(content) > 50000:
            content = self._compress_content(content)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO messages (role, content, attachments, timestamp, tokens)
                VALUES (?, ?, ?, ?, ?)
            """, (
                role, 
                content, 
                json.dumps(attachments) if attachments else None,
                datetime.utcnow().isoformat(),
                tokens
            ))
            
            # Update token count
            conn.execute("""
                UPDATE metadata SET value = 
                CAST(CAST(value AS INTEGER) + ? AS TEXT)
                WHERE key = 'token_count'
            """, (tokens,))
        
        # Auto-cleanup old messages (keep last 100)
        self._cleanup_old_messages()
    
    def _compress_content(self, content: str) -> str:
        """Compress content and store as base64"""
        import base64
        compressed = gzip.compress(content.encode('utf-8'))
        return "COMPRESSED:" + base64.b64encode(compressed).decode('ascii')
    
    def _decompress_content(self, content: str) -> str:
        """Decompress content if it was compressed"""
        if content.startswith("COMPRESSED:"):
            import base64
            compressed = base64.b64decode(content[11:])
            return gzip.decompress(compressed).decode('utf-8')
        return content
    
    def _cleanup_old_messages(self):
        """Keep only last N messages"""
        retention = 100  # Configurable
        with sqlite3.connect(self.db_path) as conn:
            # Get count
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
            
            if count > retention:
                # Delete oldest messages
                conn.execute("""
                    DELETE FROM messages 
                    WHERE id IN (
                        SELECT id FROM messages 
                        ORDER BY id ASC 
                        LIMIT ?
                    )
                """, (count - retention,))
                
                # Recalculate token count
                cursor = conn.execute("SELECT SUM(tokens) FROM messages")
                total_tokens = cursor.fetchone()[0] or 0
                
                conn.execute("""
                    UPDATE metadata SET value = ?
                    WHERE key = 'token_count'
                """, (str(total_tokens),))
                
                logger.info(f"Cleaned up old messages. Kept {retention}, tokens: {total_tokens}")
    
    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT role, content, attachments, timestamp, tokens
                FROM messages
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            
            messages = []
            for row in cursor.fetchall():
                content = self._decompress_content(row[1])
                attachments = json.loads(row[2]) if row[2] else []
                
                messages.append({
                    "role": row[0],
                    "content": content,
                    "attachments": attachments,
                    "timestamp": row[3],
                    "tokens": row[4]
                })
                
            logger.info(f"Loaded {len(messages)} messages from DB: { self.db_path}")
            return list(reversed(messages))
    
    def get_token_count(self) -> int:
        """Get total token count"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM metadata WHERE key = 'token_count'")
            return int(cursor.fetchone()[0])
    
    def reset_context(self, keep_last: int = 10):
        """Reset conversation, keep last N messages"""
        with sqlite3.connect(self.db_path) as conn:
            # Get IDs to keep
            cursor = conn.execute("""
                SELECT id FROM messages
                ORDER BY id DESC
                LIMIT ?
            """, (keep_last,))
            keep_ids = [row[0] for row in cursor.fetchall()]
            
            if not keep_ids:
                # Clear all
                conn.execute("DELETE FROM messages")
                conn.execute("UPDATE metadata SET value = '0' WHERE key = 'token_count'")
                return
            
            # Delete others
            placeholders = ",".join("?" * len(keep_ids))
            conn.execute(f"""
                DELETE FROM messages 
                WHERE id NOT IN ({placeholders})
            """, keep_ids)
            
            # Recalculate tokens
            cursor = conn.execute("SELECT SUM(tokens) FROM messages")
            total_tokens = cursor.fetchone()[0] or 0
            conn.execute("""
                UPDATE metadata SET value = ?
                WHERE key = 'token_count'
            """, (str(total_tokens),))
            
            logger.info(f"Context reset. Kept {len(keep_ids)} messages, tokens: {total_tokens}")
    
    def clear_all(self):
        """Clear entire conversation"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages")
            conn.execute("UPDATE metadata SET value = '0' WHERE key = 'token_count'")
