"""
Custom exception hierarchy for Kamao AI
Provides specific error types for better error handling and user feedback
"""


class KamaoError(Exception):
    """Base exception for all Kamao AI errors"""
    
    def __init__(self, message: str, user_hint: str = None):
        super().__init__(message)
        self.user_hint = user_hint or "Please try again or contact an admin."


class ProviderError(KamaoError):
    """Base exception for AI provider errors"""
    
    def __init__(self, provider: str, message: str, user_hint: str = None):
        self.provider = provider
        hint = user_hint or f"Try switching providers with /model"
        super().__init__(f"[{provider}] {message}", hint)


class RateLimitError(ProviderError):
    """Raised when API rate limit is hit"""
    
    def __init__(self, provider: str, retry_after: int = None):
        self.retry_after = retry_after
        message = f"Rate limit exceeded"
        if retry_after:
            message += f" (retry after {retry_after}s)"
        hint = "Please wait a moment before sending another message."
        super().__init__(provider, message, hint)


class APITimeoutError(ProviderError):
    """Raised when API request times out"""
    
    def __init__(self, provider: str, timeout: int = None):
        self.timeout = timeout
        message = f"Request timed out"
        if timeout:
            message += f" after {timeout}s"
        hint = "The AI service is slow. Try a faster model or wait."
        super().__init__(provider, message, hint)


class AuthenticationError(ProviderError):
    """Raised when API authentication fails"""
    
    def __init__(self, provider: str):
        message = "Authentication failed - invalid API key"
        hint = "Contact the bot admin to fix the API configuration."
        super().__init__(provider, message, hint)


class ModelNotFoundError(ProviderError):
    """Raised when requested model doesn't exist"""
    
    def __init__(self, provider: str, model: str):
        self.model = model
        message = f"Model '{model}' not found"
        hint = "Use /model to select a valid model."
        super().__init__(provider, message, hint)


class ContentFilterError(ProviderError):
    """Raised when content is blocked by provider safety filters"""
    
    def __init__(self, provider: str):
        message = "Response blocked by content filter"
        hint = "Try rephrasing your message or using a different model."
        super().__init__(provider, message, hint)


class EmptyResponseError(ProviderError):
    """Raised when provider returns empty response"""
    
    def __init__(self, provider: str):
        message = "Received empty response"
        hint = "Try sending your message again."
        super().__init__(provider, message, hint)


class DatabaseError(KamaoError):
    """Base exception for database errors"""
    
    def __init__(self, message: str, operation: str = None):
        self.operation = operation
        hint = "Your message may not have been saved. Try /reset if issues persist."
        super().__init__(f"Database error: {message}", hint)


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        super().__init__(f"Failed to connect to database", "connect")


class DatabaseWriteError(DatabaseError):
    """Raised when database write fails"""
    
    def __init__(self, operation: str = "write"):
        super().__init__(f"Failed to write data", operation)


class ValidationError(KamaoError):
    """Raised when input validation fails"""
    
    def __init__(self, field: str, message: str):
        self.field = field
        hint = f"Please check your {field} and try again."
        super().__init__(f"Invalid {field}: {message}", hint)


class SessionError(KamaoError):
    """Raised when session management fails"""
    
    def __init__(self, user_id: int, message: str):
        self.user_id = user_id
        hint = "Try again in a moment."
        super().__init__(f"Session error for user {user_id}: {message}", hint)


class ConfigurationError(KamaoError):
    """Raised when bot configuration is invalid"""
    
    def __init__(self, config_key: str, message: str):
        self.config_key = config_key
        hint = "Contact the bot admin to fix the configuration."
        super().__init__(f"Configuration error ({config_key}): {message}", hint)
