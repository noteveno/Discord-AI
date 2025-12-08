# Kamao AI - src package
__version__ = "2.1.0"

# Module exports
from .bot import KamaoBot, UserSession
from .exceptions import (
    KamaoError, ProviderError, RateLimitError, 
    APITimeoutError, DatabaseError, ValidationError
)
