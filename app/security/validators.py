"""Input validation and sanitization module."""

import re
from typing import Tuple
from app.core.config import settings


class InputValidationError(ValueError):
    """Custom exception for input validation errors."""
    pass


class InputValidator:
    """Validates and sanitizes user input prior to RAG processing."""

    # Zero-width spaces, direction override, and suspicious hidden Unicode characters
    INVISIBLE_CHARS_PATTERN = re.compile(r"[\u200B-\u200D\uFEFF\u202A-\u202E]")
    CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Strip invisible, control, and formatting bypass characters."""
        if not text:
            return ""
        # Remove invisible unicode characters (used in prompt smuggling)
        cleaned = cls.INVISIBLE_CHARS_PATTERN.sub("", text)
        # Remove non-printable control characters
        cleaned = cls.CONTROL_CHARS_PATTERN.sub("", cleaned)
        return cleaned.strip()

    @classmethod
    def validate(cls, text: str) -> Tuple[bool, str]:
        """Validate input length, character sanity, and non-empty constraints.
        
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not text or not text.strip():
            return False, "Query cannot be empty."

        sanitized = cls.sanitize(text)

        if len(sanitized) < 3:
            return False, "Query is too short (minimum 3 characters)."

        if len(sanitized) > settings.max_query_length:
            return False, (
                f"Query exceeds maximum allowed length of {settings.max_query_length} "
                f"characters (received {len(sanitized)})."
            )

        return True, ""
