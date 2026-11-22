"""
Memory Candidate Extraction Service for Conversation Turns (Phase 04 / 04.5).
"""

import re
from typing import List, Optional
from backend.app.memory.sanitizer import SensitiveDataSanitizer
from backend.app.memory.schemas import MemoryCategory, MemoryExtractionCandidate


class MemoryExtractionService:
    """
    Scans natural language prompts to identify high-value durable facts,
    user preferences, and project architectural decisions.
    
    Strictly distinguishes between explicit user commands (which may be persisted directly)
    and independently identified facts (which require explicit user consent as pending suggestions).
    """

    EXPLICIT_TRIGGERS = [
        r"(?i)\b(?:remember\s+(?:that|this)?|keep\s+in\s+mind(?:\s+that)?|don't\s+forget(?:\s+that)?|note\s+that)\s+(.+)",
    ]

    PREFERENCE_TRIGGERS = [
        r"(?i)\b(?:always\s+use|never\s+use|my\s+preference\s+is|i\s+prefer)\s+(.+)",
    ]

    PROJECT_TRIGGERS = [
        r"(?i)\b(?:we\s+decided\s+to\s+(?:use|implement|adopt)|the\s+architecture\s+(?:is|uses)|the\s+project\s+(?:name\s+is|uses))\s+(.+)",
        r"(?i)\b(?:our\s+database\s+is|we\s+are\s+building)\s+(.+)",
    ]

    PERSONAL_TRIGGERS = [
        r"(?i)\b(?:i\s+am|i\s+work\s+as|my\s+role\s+is|i\s+live\s+in|call\s+me)\s+(.+)",
    ]

    @classmethod
    def extract_candidates(cls, message: str) -> List[MemoryExtractionCandidate]:
        """
        Extracts potential memory candidates from a user prompt.
        Filters out sensitive credentials and determines if explicit user approval is needed.
        """
        text = message.strip()
        candidates: List[MemoryExtractionCandidate] = []

        # 1. Sensitive Data Check: If raw secrets are in the prompt, reject candidate generation completely
        is_sensitive, sensitive_cat = SensitiveDataSanitizer.check_for_sensitive_data(text)
        if is_sensitive:
            return []

        # 2. Check explicit commands ("Remember that...", "Keep in mind that...")
        for pattern in cls.EXPLICIT_TRIGGERS:
            match = re.search(pattern, text)
            if match:
                content = match.group(1).strip().rstrip(".").capitalize()
                category = MemoryCategory.PERSONAL if "prefer" in text.lower() else MemoryCategory.KNOWLEDGE
                candidates.append(
                    MemoryExtractionCandidate(
                        content=content,
                        category=category,
                        confidence=0.95,
                        importance=4,
                        source_statement=text,
                        needs_approval=False,  # Explicit command from user
                        reasoning="Explicit user directive to retain memory."
                    )
                )

        # 3. Check preferences mentioned in passing ("I prefer...", "My preference is...")
        # If not explicitly preceded by "remember that", this requires user approval!
        if not candidates:
            for pattern in cls.PREFERENCE_TRIGGERS:
                match = re.search(pattern, text)
                if match:
                    content = match.group(0).strip().rstrip(".").capitalize()
                    candidates.append(
                        MemoryExtractionCandidate(
                            content=content,
                            category=MemoryCategory.PERSONAL,
                            confidence=0.85,
                            importance=3,
                            source_statement=text,
                            needs_approval=True,  # Requires explicit consent
                            reasoning="User preference detected in dialogue without explicit remember command."
                        )
                    )

        # 4. Check project decisions ("We decided to use...", "Our database is...")
        for pattern in cls.PROJECT_TRIGGERS:
            match = re.search(pattern, text)
            if match:
                content = match.group(0).strip().rstrip(".").capitalize()
                candidates.append(
                    MemoryExtractionCandidate(
                        content=content,
                        category=MemoryCategory.PROJECT,
                        confidence=0.90,
                        importance=4,
                        source_statement=text,
                        needs_approval=True,  # Architectural facts require consent
                        reasoning="Architectural/project decision statement identified from dialogue."
                    )
                )

        # 5. Check personal profile facts ("I work as...", "My role is...")
        for pattern in cls.PERSONAL_TRIGGERS:
            match = re.search(pattern, text)
            if match:
                content = match.group(0).strip().rstrip(".").capitalize()
                candidates.append(
                    MemoryExtractionCandidate(
                        content=content,
                        category=MemoryCategory.PERSONAL,
                        confidence=0.85,
                        importance=3,
                        source_statement=text,
                        needs_approval=True,  # Personal facts require consent
                        reasoning="User personal profile statement identified from dialogue."
                    )
                )

        return candidates
