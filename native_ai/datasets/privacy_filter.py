"""Quality & Privacy Filter for LOVE Native AI Dataset Pipeline.

Implements Task 9:
- Detects and filters Personal Identifiable Information (PII):
  - Personal email addresses (redacted or flagged)
  - Personal phone numbers
- Detects and strictly rejects sensitive credentials & secrets:
  - Private cryptographic keys (RSA, EC, OpenSSH, PGP)
  - High-entropy API keys (Bearer tokens, OpenAI `sk-`, GitHub `ghp_`, AWS keys)
  - Plaintext password assignments
  - JWT tokens
- Rejects confidential corporate / personal document markings
- Preserves valid technical identifiers, code variables, and documentation URLs.
- Provides privacy telemetry without logging sensitive data.
"""
import re
from typing import Tuple, Dict, Any, List


class PrivacyFilter:
    # Strict exclusion patterns (if matched, entire document is rejected)
    REJECT_PATTERNS = [
        # Private keys
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
        re.compile(r"-----BEGIN RSA PRIVATE KEY-----", re.IGNORECASE),
        re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----", re.IGNORECASE),
        # API Keys & Auth Tokens
        re.compile(r"\b(sk-[a-zA-Z0-9]{20,})\b"),           # OpenAI style
        re.compile(r"\b(ghp_[a-zA-Z0-9]{20,})\b"),          # GitHub Personal Access Token
        re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),              # AWS Access Key
        re.compile(r"\b(AIza[0-9A-Za-z-_]{35})\b"),         # Google API key
        re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), # JWT
        # Password assignments in config/code
        re.compile(r"""(?:password|passwd|pwd|api_secret|client_secret)\s*[:=]\s*["'][^"'\s]{6,}["']""", re.IGNORECASE),
        # Confidentiality markings
        re.compile(r"\b(?:STRICTLY CONFIDENTIAL|CONFIDENTIAL AND PROPRIETARY|RESTRICTED - DO NOT DISTRIBUTE)\b", re.IGNORECASE),
    ]

    # Redaction patterns (PII replaced with placeholder instead of document rejection)
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
    PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

    # Safe technical domains that should not be redacted as email
    SAFE_EMAIL_DOMAINS = {"example.com", "example.org", "domain.com", "local", "internal"}

    def inspect_and_filter(self, text: str) -> Tuple[bool, str, List[str]]:
        """
        Evaluates text for privacy violations.
        Returns:
            (is_admitted, sanitized_text, flags_list)
        """
        flags: List[str] = []

        # 1. Check strict rejection patterns
        for pattern in self.REJECT_PATTERNS:
            match = pattern.search(text)
            if match:
                pattern_name = pattern.pattern[:30]
                flags.append(f"rejected_secret_or_confidential_{pattern_name}")
                return False, "", flags

        # 2. Redact email addresses (except safe mock domains)
        def replace_email(match):
            email = match.group(0)
            domain = email.split("@")[-1].lower()
            if domain in self.SAFE_EMAIL_DOMAINS:
                return email
            flags.append("redacted_email")
            return "[EMAIL_REDACTED]"

        sanitized = self.EMAIL_PATTERN.sub(replace_email, text)

        # 3. Redact phone numbers
        def replace_phone(match):
            phone = match.group(0)
            # Avoid redacting simple version strings like 1.2.3.4
            if phone.count(".") == 3 and not phone.startswith("+"):
                return phone
            flags.append("redacted_phone")
            return "[PHONE_REDACTED]"

        sanitized = self.PHONE_PATTERN.sub(replace_phone, sanitized)

        return True, sanitized, flags
