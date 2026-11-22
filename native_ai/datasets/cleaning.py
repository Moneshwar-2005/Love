"""Text Cleaning Module for LOVE Native AI Dataset Pipeline.

Implements Task 7:
- Unicode normalization (NFKC)
- HTML entity decoding and artifact removal
- Excessive whitespace reduction (collapses 3+ newlines to 2, strips trailing whitespace)
- Code indentation preservation
- Control character removal (preserving \n, \t)
- Document filtering (minimum character & word thresholds)
- Excessive paragraph repetition truncation
"""
import re
import html
import unicodedata
from typing import Optional, Tuple, Dict, Any


class TextCleaner:
    def __init__(
        self,
        min_chars: int = 40,
        min_words: int = 8,
        max_repeated_paragraph_ratio: float = 0.5,
    ):
        self.min_chars = min_chars
        self.min_words = min_words
        self.max_repeated_paragraph_ratio = max_repeated_paragraph_ratio

    def clean_text(self, text: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Cleans text while preserving capitalization, punctuation, code formatting,
        and mathematical expressions.
        Returns:
            (cleaned_text, metadata_dict) or (None, rejection_reason_dict)
        """
        if not text or not isinstance(text, str):
            return None, {"rejected": True, "reason": "empty_or_non_string"}

        # 1. Unicode normalization (NFKC)
        normalized = unicodedata.normalize("NFKC", text)

        # 2. HTML unescaping and tag stripping
        unescaped = html.unescape(normalized)
        cleaned = re.sub(r"<(p|br|div|span|h[1-6]|ul|ol|li)[^>]*>", "\n", unescaped, flags=re.IGNORECASE)
        cleaned = re.sub(r"</(p|div|h[1-6]|ul|ol|li)>", "\n", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)  # Strip remaining basic tags

        # 3. Strip control characters (except newline, tab, carriage return)
        cleaned = "".join(ch for ch in cleaned if ch in ("\n", "\t", "\r") or unicodedata.category(ch) != "Cc")

        # 4. Standardize line endings and collapse excessive empty lines (3+ -> 2)
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in cleaned.split("\n")]
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

        # 5. Length validation
        num_chars = len(cleaned)
        words = cleaned.split()
        num_words = len(words)

        if num_chars < self.min_chars:
            return None, {"rejected": True, "reason": f"too_short_chars_{num_chars}"}
        if num_words < self.min_words:
            return None, {"rejected": True, "reason": f"too_short_words_{num_words}"}

        # 6. Check repeated paragraphs (boilerplate / template loop detection)
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        if len(paragraphs) > 2:
            unique_paras = set(paragraphs)
            duplicate_ratio = 1.0 - (len(unique_paras) / len(paragraphs))
            if duplicate_ratio > self.max_repeated_paragraph_ratio:
                # Deduplicate repeated paragraphs in-place while preserving first occurrence order
                seen = set()
                deduped_paras = []
                for p in paragraphs:
                    if p not in seen:
                        seen.add(p)
                        deduped_paras.append(p)
                cleaned = "\n\n".join(deduped_paras).strip()

        return cleaned, {
            "rejected": False,
            "orig_chars": len(text),
            "cleaned_chars": len(cleaned),
            "words": len(cleaned.split()),
        }
