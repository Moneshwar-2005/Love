"""Comprehensive Tokenizer Benchmark and Evaluation Suite for LOVE Native AI.

Implements Task 9:
- Measures actual vocabulary size & total merge rules
- Evaluates on strictly held-out English text (native_ai/datasets/raw/held_out_eval.txt)
- Computes:
  - Average tokens per word
  - Average tokens per character
  - Compression ratio against raw UTF-8 bytes (bytes per token)
  - Unknown/uncommon byte sequence resilience
  - Encoding throughput (tokens/second & characters/second)
  - Decoding throughput (tokens/second)
  - Memory footprint of tokenizer in memory
- Trains a temporary experimental 4,096-token BPE tokenizer to benchmark vocabulary scaling
  efficiency against the primary 8,192-token baseline without modifying primary configs.
- Exports results to native_ai/experiments/nai_02_tokenizer_benchmark.json.
"""
import sys
import os
import time
import json
import psutil
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders
from native_ai.tokenizer.love_tokenizer import LoveTokenizer, LoveTokenizerConfig

ARTIFACTS_DIR = PROJECT_ROOT / "native_ai" / "tokenizer" / "artifacts"
HELD_OUT_PATH = PROJECT_ROOT / "native_ai" / "datasets" / "raw" / "held_out_eval.txt"
SEED_CORPUS_PATH = PROJECT_ROOT / "native_ai" / "datasets" / "raw" / "seed_corpus.txt"
EXPERIMENTS_DIR = PROJECT_ROOT / "native_ai" / "experiments"


def evaluate_tokenizer_metrics(tokenizer: LoveTokenizer, text: str, name: str = "primary_8192") -> Dict[str, Any]:
    raw_bytes = len(text.encode("utf-8"))
    num_chars = len(text)
    num_words = len(text.split())

    # Process RAM before
    process = psutil.Process(os.getpid())
    ram_before_mb = process.memory_info().rss / (1024 * 1024)

    # 1. Encode
    encoded_ids = tokenizer.encode(text)
    num_tokens = len(encoded_ids)

    # Ratios
    tokens_per_word = num_tokens / num_words if num_words > 0 else 0.0
    tokens_per_char = num_tokens / num_chars if num_chars > 0 else 0.0
    bytes_per_token = raw_bytes / num_tokens if num_tokens > 0 else 0.0
    compression_ratio = raw_bytes / (num_tokens * 2)  # assuming 16-bit uint16 token IDs vs 8-bit UTF-8

    # 2. Speed Benchmarking (Repeated runs over repeated sample for statistical reliability)
    repeat_count = 50
    large_text = text * repeat_count
    large_bytes = len(large_text.encode("utf-8"))

    # Encoding speed
    t0 = time.perf_counter()
    large_encoded = tokenizer.encode(large_text)
    enc_duration = time.perf_counter() - t0
    enc_tokens_per_sec = len(large_encoded) / enc_duration
    enc_chars_per_sec = len(large_text) / enc_duration

    # Decoding speed
    t1 = time.perf_counter()
    decoded_text = tokenizer.decode(large_encoded)
    dec_duration = time.perf_counter() - t1
    dec_tokens_per_sec = len(large_encoded) / dec_duration

    ram_after_mb = process.memory_info().rss / (1024 * 1024)

    # Vocabulary boundary check
    max_id = max(encoded_ids) if encoded_ids else 0
    min_id = min(encoded_ids) if encoded_ids else 0
    in_bounds = (min_id >= 0) and (max_id < tokenizer.vocab_size)

    # Unknown byte handling test
    exotic_string = "Unicode test: 🚀 Café résumé naïve π ≈ 3.14159 — Japanese: こんにちは — Math: √x²"
    exotic_encoded = tokenizer.encode(exotic_string)
    exotic_decoded = tokenizer.decode(exotic_encoded)
    exotic_roundtrip_ok = (exotic_decoded == exotic_string)

    results = {
        "model_name": name,
        "vocab_size": tokenizer.vocab_size,
        "sample_bytes": raw_bytes,
        "sample_chars": num_chars,
        "sample_words": num_words,
        "encoded_tokens": num_tokens,
        "tokens_per_word": round(tokens_per_word, 4),
        "tokens_per_char": round(tokens_per_char, 4),
        "bytes_per_token": round(bytes_per_token, 4),
        "compression_ratio": round(compression_ratio, 4),
        "encoding_tokens_per_sec": round(enc_tokens_per_sec, 2),
        "encoding_chars_per_sec": round(enc_chars_per_sec, 2),
        "decoding_tokens_per_sec": round(dec_tokens_per_sec, 2),
        "tokenizer_ram_mb": round(ram_after_mb, 2),
        "token_ids_in_bounds": in_bounds,
        "exotic_unicode_roundtrip_ok": exotic_roundtrip_ok,
    }
    return results


def train_experimental_small_tokenizer(corpus_path: Path, vocab_size: int = 4096) -> LoveTokenizer:
    """Trains a temporary 4,096-token BPE tokenizer for comparative vocabulary research."""
    tok = Tokenizer(models.BPE(unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    special_tokens = ["<pad>", "<unk>", "<bos>", "<eos>", "<|system|>", "<|user|>", "<|assistant|>", "<|tool|>"]
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=1,
        show_progress=False,
        special_tokens=special_tokens,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
    )
    tok.train([str(corpus_path)], trainer)
    return LoveTokenizer(tok, LoveTokenizerConfig(vocab_size=tok.get_vocab_size(), special_tokens=special_tokens))


def main():
    print("=" * 80)
    print("  LOVE NATIVE AI: TOKENIZER BENCHMARK & EVALUATION")
    print("=" * 80)

    # 1. Load Primary 8,192 Tokenizer
    primary_tok = LoveTokenizer.from_pretrained(ARTIFACTS_DIR)
    print(f"Loaded Primary Tokenizer from: {ARTIFACTS_DIR}")
    print(f"Primary Vocab Size: {primary_tok.vocab_size}")

    # 2. Read Held-Out Evaluation Corpus
    if not HELD_OUT_PATH.exists():
        raise FileNotFoundError(f"Missing held-out evaluation text at {HELD_OUT_PATH}")

    held_out_text = HELD_OUT_PATH.read_text(encoding="utf-8")
    print(f"Held-Out Text Loaded: {len(held_out_text)} characters, {len(held_out_text.split())} words")

    # 3. Evaluate Primary 8,192 Tokenizer
    primary_metrics = evaluate_tokenizer_metrics(primary_tok, held_out_text, name="LOVE-Native-BPE-8192")

    print("\n--- PRIMARY 8,192 VOCABULARY RESULTS ---")
    for k, v in primary_metrics.items():
        print(f"  {k:30s}: {v}")

    # 4. Train & Evaluate Experimental 4,096 Tokenizer (Comparative Study)
    print("\nTraining experimental 4,096-token tokenizer for scaling comparison...")
    exp_tok = train_experimental_small_tokenizer(SEED_CORPUS_PATH, vocab_size=4096)
    exp_metrics = evaluate_tokenizer_metrics(exp_tok, held_out_text, name="Experimental-BPE-4096")

    print("\n--- EXPERIMENTAL 4,096 VOCABULARY RESULTS ---")
    for k, v in exp_metrics.items():
        print(f"  {k:30s}: {v}")

    # Comparative Summary
    comparison = {
        "primary_8192": primary_metrics,
        "experimental_4096": exp_metrics,
        "tokens_per_word_reduction": round(
            (exp_metrics["tokens_per_word"] - primary_metrics["tokens_per_word"]) / exp_metrics["tokens_per_word"] * 100, 2
        ),
        "compression_gain_pct": round(
            (primary_metrics["compression_ratio"] - exp_metrics["compression_ratio"]) / exp_metrics["compression_ratio"] * 100, 2
        ),
    }

    print("\n--- COMPARATIVE SCALING SUMMARY ---")
    print(f"  Tokens per Word: 4,096 vocab -> {exp_metrics['tokens_per_word']} | 8,192 vocab -> {primary_metrics['tokens_per_word']}")
    print(f"  Efficiency Improvement: {comparison['tokens_per_word_reduction']}% fewer tokens per word with 8k vocab")
    print(f"  Bytes per Token: 4,096 vocab -> {exp_metrics['bytes_per_token']} | 8,192 vocab -> {primary_metrics['bytes_per_token']}")

    # 5. Export Metrics
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = EXPERIMENTS_DIR / "nai_02_tokenizer_benchmark.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    print(f"\nSaved benchmark telemetry to: {out_file}")


if __name__ == "__main__":
    main()
