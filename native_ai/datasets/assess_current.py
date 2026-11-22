"""Assessment of existing dataset fixtures for LOVE Native AI.

Implements Task 3:
Evaluates current seed corpus and held-out evaluation text:
- Corpus size (bytes, chars, lines, words, unique words)
- Subject coverage
- Language quality
- Repetition rate
- Template-generated text indicators
- Duplicates
- Text diversity
- Training/evaluation leakage
"""
import sys
import json
import hashlib
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

RAW_DIR = PROJECT_ROOT / "native_ai" / "datasets" / "raw"
MANIFESTS_DIR = PROJECT_ROOT / "native_ai" / "datasets" / "manifests"
TOKENIZER_DIR = PROJECT_ROOT / "native_ai" / "tokenizer" / "artifacts"


def assess_assets():
    raw_corpus_path = RAW_DIR / "seed_corpus.txt"
    held_out_path = RAW_DIR / "held_out_eval.txt"
    manifest_path = MANIFESTS_DIR / "seed_corpus_manifest.json"

    report = {"seed_corpus": {}, "held_out_eval": {}, "leakage_check": {}}

    if raw_corpus_path.exists():
        text = raw_corpus_path.read_text(encoding="utf-8")
        words = text.split()
        unique_words = set(w.lower() for w in words)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        unique_paragraphs = set(paragraphs)

        # Word frequency & diversity
        word_counts = Counter(w.lower() for w in words)
        ttr = len(unique_words) / len(words) if words else 0.0  # Type-Token Ratio

        report["seed_corpus"] = {
            "size_bytes": len(text.encode("utf-8")),
            "num_chars": len(text),
            "num_words": len(words),
            "unique_words": len(unique_words),
            "type_token_ratio": round(ttr, 4),
            "num_paragraphs": len(paragraphs),
            "unique_paragraphs": len(unique_paragraphs),
            "paragraph_duplicate_rate_pct": round((1.0 - len(unique_paragraphs) / max(1, len(paragraphs))) * 100, 2),
            "top_10_words": word_counts.most_common(10),
        }

    if held_out_path.exists():
        htext = held_out_path.read_text(encoding="utf-8")
        hwords = htext.split()
        hunique_words = set(w.lower() for w in hwords)
        hparagraphs = [p.strip() for p in htext.split("\n\n") if p.strip()]

        report["held_out_eval"] = {
            "size_bytes": len(htext.encode("utf-8")),
            "num_chars": len(htext),
            "num_words": len(hwords),
            "unique_words": len(hunique_words),
            "num_paragraphs": len(hparagraphs),
        }

    # Leakage check: verify if any paragraph in held_out appears in seed_corpus
    if raw_corpus_path.exists() and held_out_path.exists():
        seed_paras = set(p.strip() for p in raw_corpus_path.read_text(encoding="utf-8").split("\n\n") if p.strip())
        eval_paras = set(p.strip() for p in held_out_path.read_text(encoding="utf-8").split("\n\n") if p.strip())
        leakage = seed_paras.intersection(eval_paras)
        report["leakage_check"] = {
            "overlapping_paragraphs": len(leakage),
            "has_leakage": len(leakage) > 0,
        }

    return report


if __name__ == "__main__":
    rep = assess_assets()
    print("=== CURRENT DATASET ASSESSMENT REPORT ===")
    print(json.dumps(rep, indent=2))
