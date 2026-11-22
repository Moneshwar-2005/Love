"""
Sensitive Data Sanitizer and Protection Gate for Personal Memory (Phase 04).
Prevents permanent persistence of credentials, passwords, API keys, and private tokens.
"""

import re
from typing import Optional, Tuple


class SensitiveDataSanitizer:
    """
    Scans text payloads for sensitive security credentials, private keys,
    bearer tokens, and authentication secrets before persistent storage.
    """

    PATTERNS = [
        (
            "API Key / Secret Token",
            r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|aws_secret_access_key)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\./\+]{16,}['\"]?"
        ),
        (
            "Provider Key / Token",
            r"\b(?:sk-[a-zA-Z0-9_\-]{20,}|sk-ant-[a-zA-Z0-9_\-]{20,}|AIzaSy[a-zA-Z0-9_\-]{30,}|ghp_[a-zA-Z0-9]{30,}|gho_[a-zA-Z0-9]{30,})\b"
        ),
        (
            "Bearer Token",
            r"(?i)\bbearer\s+[a-zA-Z0-9_\-\.]{20,}\b"
        ),
        (
            "Password Credential",
            r"(?i)\b(?:my\s+password\s+is|password\s*[:=]\s*['\"]?[^'\"\s]{6,}['\"]?|db_password\s*[:=])"
        ),
        (
            "Private Key Block",
            r"-----BEGIN\s+(?:RSA|OPENSSH|EC|DSA|PGP)?\s*PRIVATE KEY-----"
        ),
        (
            "Credit Card Number",
            r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
        ),
        (
            "JWT Bearer Token",
            r"\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"
        ),
    ]

    @classmethod
    def check_for_sensitive_data(cls, text: str) -> Tuple[bool, Optional[str]]:
        """
        Inspects text for sensitive credential patterns.
        Returns (is_sensitive, detected_category).
        """
        for category, pattern in cls.PATTERNS:
            if re.search(pattern, text):
                return True, category
        return False, None

    @classmethod
    def sanitize_for_prompt(cls, text: str) -> str:
        """
        Replaces detected sensitive tokens in text with placeholder redactions.
        """
        sanitized = text
        for category, pattern in cls.PATTERNS:
            sanitized = re.sub(pattern, f"[REDACTED {category}]", sanitized)
        return sanitized
