"""Automated Test Suite for LOVE Native AI Tokenizer & Transformer Compatibility.

Implements Tasks 8 and 10:
- Encode/decode round-trip fidelity
- Empty string handling
- Whitespace-only string handling
- Uppercase, lowercase, and mixed case preservation
- Punctuation and symbol coverage
- Numbers and mathematical expressions
- URLs and file paths as plain text
- Unicode and uncommon international characters
- Repetitive text handling
- Long inputs (> 4,096 characters)
- Special-token boundaries & isolation (<pad>, <unk>, <bos>, <eos>, <|system|>, <|user|>, <|assistant|>, <|tool|>)
- Unknown and uncommon byte sequences
- Save/reload equivalence across disk serialization
- Deterministic encoding output across repeated runs
- Vocabulary size check (must equal 8,192)
- Token ID boundary checks (0 <= token_id < 8192)
- Integration compatibility with LoveForCausalLM (tiny.yaml):
  - Token IDs fit embedding table
  - Sequences respect context length (512)
  - Forward pass executes with correct logit shape [batch_size, seq_len, 8192]
  - Autoregressive generation succeeds
"""
import pytest
import torch
from pathlib import Path

from native_ai.tokenizer.love_tokenizer import LoveTokenizer, LoveTokenizerConfig
from native_ai.model.love_model import LoveModelConfig, LoveForCausalLM

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "tokenizer" / "artifacts"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "tiny.yaml"


@pytest.fixture(scope="module")
def tokenizer():
    return LoveTokenizer.from_pretrained(ARTIFACTS_DIR)


@pytest.fixture(scope="module")
def tiny_model():
    config = LoveModelConfig.from_yaml(str(CONFIG_PATH))
    torch.manual_seed(42)
    model = LoveForCausalLM(config)
    model.eval()
    return model


def test_vocab_size_and_special_tokens(tokenizer):
    """Verify vocabulary size equals exactly 8,192 and all special tokens are registered."""
    assert tokenizer.vocab_size == 8192, f"Expected vocab size 8192, got {tokenizer.vocab_size}"

    expected_specials = [
        "<pad>", "<unk>", "<bos>", "<eos>",
        "<|system|>", "<|user|>", "<|assistant|>", "<|tool|>"
    ]
    for token in expected_specials:
        token_id = tokenizer.token_to_id(token)
        assert token_id is not None, f"Special token {token} not found in vocabulary"
        assert 0 <= token_id < 8192, f"Special token {token} ID {token_id} out of bounds"
        # Verify decoding recovers the special token
        assert tokenizer.decode([token_id]) == token


def test_encode_decode_round_trip(tokenizer):
    """Verify that standard English text round-trips with 100% fidelity."""
    sample = "The quick brown fox jumps over the lazy dog."
    tokens = tokenizer.encode(sample)
    decoded = tokenizer.decode(tokens)
    assert decoded == sample, f"Round-trip failed: '{decoded}' != '{sample}'"


def test_empty_and_whitespace_text(tokenizer):
    """Verify handling of empty strings and whitespace-only text."""
    # Empty string
    assert tokenizer.encode("") == []
    assert tokenizer.decode([]) == ""

    # Whitespace only
    ws = "   \n\t  \r\n  "
    ws_tokens = tokenizer.encode(ws)
    assert len(ws_tokens) > 0
    assert tokenizer.decode(ws_tokens) == ws


def test_case_preservation(tokenizer):
    """Verify that upper, lower, and mixed casing is strictly preserved."""
    texts = [
        "UPPERCASE SENTENCE WITH WORDS",
        "lowercase sentence with words",
        "mIxEd CaSe SeNtEnCe WiTh WoRdS",
        "CamelCaseIdentifier and snake_case_identifier",
    ]
    for t in texts:
        tokens = tokenizer.encode(t)
        assert tokenizer.decode(tokens) == t, f"Casing not preserved for: {t}"


def test_punctuation_and_symbols(tokenizer):
    """Verify all ASCII punctuation, symbols, and operators."""
    symbols = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~\\\"'"
    tokens = tokenizer.encode(symbols)
    assert tokenizer.decode(tokens) == symbols


def test_numbers_and_formatting(tokenizer):
    """Verify numerical values, floating point numbers, and timestamps."""
    numbers = "12345 67890 3.14159265 2026-11-21 18:30:00 -42 +100 $1,250.75 99.99%"
    tokens = tokenizer.encode(numbers)
    assert tokenizer.decode(tokens) == numbers


def test_urls_and_identifiers(tokenizer):
    """Verify URLs, email addresses, and filesystem paths as plain text."""
    urls = "https://love.local/v1/models?format=json#metadata admin@love.internal C:\\Windows\\System32 /usr/bin/env"
    tokens = tokenizer.encode(urls)
    assert tokenizer.decode(tokens) == urls


def test_unicode_and_uncommon_characters(tokenizer):
    """Verify international Unicode characters, accents, and symbols via byte-level BPE."""
    unicode_text = "Café résumé naïve façade — Greek: αβγδε — Japanese: こんにちは — Math: ∑∫√π ≈ 3.14"
    tokens = tokenizer.encode(unicode_text)
    assert all(0 <= tid < 8192 for tid in tokens)
    assert tokenizer.decode(tokens) == unicode_text


def test_repeated_text_and_long_input(tokenizer):
    """Verify tokenization on repeated text and inputs exceeding 4,096 characters."""
    repeated = "repeat " * 200
    tokens = tokenizer.encode(repeated)
    assert tokenizer.decode(tokens) == repeated

    long_input = "Long text stream for tokenizer capacity validation. " * 100  # ~5,300 chars
    tokens_long = tokenizer.encode(long_input)
    assert len(tokens_long) > 500
    assert tokenizer.decode(tokens_long) == long_input


def test_special_token_boundaries_and_chat_template(tokenizer):
    """Verify conversational role markers do not collide with adjacent text."""
    prompt = "<|system|>You are LOVE.<|user|>Hello!<|assistant|>Greetings! How may I assist you?<|tool|>call()"
    tokens = tokenizer.encode(prompt)
    decoded = tokenizer.decode(tokens)
    assert decoded == prompt

    # Verify special tokens retain individual IDs
    sys_id = tokenizer.system_token_id
    usr_id = tokenizer.user_token_id
    asst_id = tokenizer.assistant_token_id
    tool_id = tokenizer.tool_token_id

    assert sys_id in tokens
    assert usr_id in tokens
    assert asst_id in tokens
    assert tool_id in tokens

    # Test skip_special_tokens=True in decode
    stripped = tokenizer.decode(tokens, skip_special_tokens=True)
    assert "<|system|>" not in stripped
    assert "<|user|>" not in stripped
    assert "<|assistant|>" not in stripped
    assert "<|tool|>" not in stripped
    assert "You are LOVE.Hello!Greetings! How may I assist you?call()" in stripped


def test_save_and_reload_equivalence(tokenizer, tmp_path):
    """Verify that saving and reloading the tokenizer produces bit-for-bit identical outputs."""
    save_dir = tmp_path / "test_tok"
    tokenizer.save_pretrained(save_dir)

    reloaded = LoveTokenizer.from_pretrained(save_dir)
    assert reloaded.vocab_size == tokenizer.vocab_size

    test_string = "Testing serialization equivalence for LOVE Native AI BPE Tokenizer!"
    orig_tokens = tokenizer.encode(test_string)
    reload_tokens = reloaded.encode(test_string)
    assert orig_tokens == reload_tokens
    assert reloaded.decode(reload_tokens) == tokenizer.decode(orig_tokens)


def test_deterministic_encoding(tokenizer):
    """Verify that encoding is completely deterministic across repeated invocations."""
    sample = "Deterministic encoding verification over repeated runs."
    first = tokenizer.encode(sample)
    for _ in range(10):
        assert tokenizer.encode(sample) == first


def test_batch_encode_padding_and_truncation(tokenizer):
    """Verify batch encoding with padding, attention masks, and context truncation."""
    texts = [
        "Short text.",
        "A somewhat longer sentence intended for batch testing.",
        "An extremely long sentence " * 50,
    ]
    batch = tokenizer.batch_encode(texts, padding=True, truncation=True, max_length=64, return_tensors="pt")

    input_ids = batch["input_ids"]
    attention_mask = batch["attention_mask"]

    assert isinstance(input_ids, torch.Tensor)
    assert isinstance(attention_mask, torch.Tensor)
    assert input_ids.shape == (3, 64)
    assert attention_mask.shape == (3, 64)

    # Padding tokens in row 0 should match pad_token_id
    assert (input_ids[0, attention_mask[0] == 0] == tokenizer.pad_token_id).all()


def test_transformer_integration_compatibility(tokenizer, tiny_model):
    """
    INTEGRATION TEST (Task 10):
    Verify that token IDs emitted by LoveTokenizer feed seamlessly into
    LoveForCausalLM without out-of-bounds errors or shape mismatches.
    """
    assert tiny_model.config.vocab_size == tokenizer.vocab_size == 8192, (
        f"Model vocab ({tiny_model.config.vocab_size}) != Tokenizer vocab ({tokenizer.vocab_size})"
    )

    prompt = "<|system|>You are LOVE.<|user|>Hello!<|assistant|>"
    batch = tokenizer.batch_encode([prompt], return_tensors="pt", max_length=512)
    input_ids = batch["input_ids"]

    # Verify bounds
    assert (input_ids >= 0).all()
    assert (input_ids < 8192).all()

    # Forward pass
    with torch.no_grad():
        logits, loss = tiny_model(input_ids)

    batch_size, seq_len = input_ids.shape
    assert logits.shape == (batch_size, seq_len, 8192), (
        f"Expected logits shape ({batch_size}, {seq_len}, 8192), got {logits.shape}"
    )
    assert torch.isfinite(logits).all(), "Logits contain non-finite values (NaN/Inf)"

    # Autoregressive generation test
    generated_ids = tiny_model.generate(input_ids, max_new_tokens=8, temperature=0.7)
    assert generated_ids.shape == (batch_size, seq_len + 8)

    # Decode generated tokens
    decoded_output = tokenizer.decode(generated_ids[0].tolist())
    assert len(decoded_output) > len(prompt)
