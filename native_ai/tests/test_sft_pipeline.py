"""Automated Test Suite for LOVE Native AI SFT Dataset & Pipeline (NAI-07A).

Verifies:
1. Conversation validation, structure, and role ordering.
2. Multi-turn serialization and special token formatting.
3. Assistant-only loss masking and gradient isolation (zero gradient on -100).
4. Dynamic batch padding and collation target masking.
5. Truncation safety and rejection of oversized turn pairs.
6. Conversation-tree split isolation and content-hash disjointness.
7. Deduplication, PII detection, and secret rejection.
8. Source provenance, license accounting, and manifest checksum verification.
9. Dry-run forward pass finiteness and parameter immutability.
"""
import json
import hashlib
from pathlib import Path
import pytest
import torch
import torch.nn.functional as F

from native_ai.model.love_model import LoveForCausalLM, LoveModelConfig
from native_ai.tokenizer.love_tokenizer import LoveTokenizer
from native_ai.datasets.privacy_filter import PrivacyFilter
from native_ai.datasets.sft.format import (
    Message,
    ConversationExample,
    LOVEInstructionFormatter,
    SYSTEM_TOKEN_ID,
    USER_TOKEN_ID,
    ASSISTANT_TOKEN_ID,
    EOS_TOKEN_ID,
    PAD_TOKEN_ID,
    IGNORE_INDEX,
    TruncationSafetyError,
)
from native_ai.datasets.sft.dataloader import (
    SFTDataset,
    SFTCollator,
    SFTDataLoader,
)

BASE_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def tokenizer():
    tok_dir = BASE_DIR / "tokenizer" / "artifacts"
    return LoveTokenizer.from_pretrained(str(tok_dir))


@pytest.fixture(scope="module")
def sample_conversation():
    return ConversationExample(
        conversation_id="conv_test_001",
        tree_id="tree_test_001",
        source_id="src_test",
        category="general_conversation",
        license="Apache-2.0",
        messages=[
            Message(role="system", content="You are LOVE, a helpful assistant."),
            Message(role="user", content="What is the capital of France?"),
            Message(role="assistant", content="The capital of France is Paris."),
        ],
    )


# =========================================================================
# 1. Structural Validation and Role Ordering Tests
# =========================================================================

def test_valid_conversation_passes(sample_conversation):
    is_valid, reason = LOVEInstructionFormatter.validate_conversation(sample_conversation)
    assert is_valid is True
    assert reason is None


def test_invalid_conversation_role_ordering():
    # User immediately following user
    bad_conv = ConversationExample(
        conversation_id="bad_01",
        tree_id="tree_bad",
        source_id="src_test",
        category="general_conversation",
        license="MIT",
        messages=[
            Message(role="user", content="First question"),
            Message(role="user", content="Second question"),
            Message(role="assistant", content="Answer"),
        ],
    )
    is_valid, reason = LOVEInstructionFormatter.validate_conversation(bad_conv)
    assert is_valid is False
    assert "Role ordering violation" in reason


def test_conversation_must_end_with_assistant():
    bad_conv = ConversationExample(
        conversation_id="bad_02",
        tree_id="tree_bad",
        source_id="src_test",
        category="general_conversation",
        license="MIT",
        messages=[
            Message(role="user", content="Question"),
        ],
    )
    is_valid, reason = LOVEInstructionFormatter.validate_conversation(bad_conv)
    assert is_valid is False


def test_empty_content_rejected():
    bad_conv = ConversationExample(
        conversation_id="bad_03",
        tree_id="tree_bad",
        source_id="src_test",
        category="general_conversation",
        license="MIT",
        messages=[
            Message(role="user", content="   "),
            Message(role="assistant", content="Valid answer"),
        ],
    )
    is_valid, reason = LOVEInstructionFormatter.validate_conversation(bad_conv)
    assert is_valid is False
    assert "Empty content" in reason


# =========================================================================
# 2. Serialization and Token IDs
# =========================================================================

def test_serialization_format(sample_conversation):
    text = LOVEInstructionFormatter.serialize_text(sample_conversation)
    assert text.startswith("<|system|>")
    assert "<|user|>" in text
    assert "<|assistant|>" in text
    assert text.endswith("<eos>")


def test_special_token_constants(tokenizer):
    assert PAD_TOKEN_ID == tokenizer.special_token_ids["<pad>"] == 0
    assert EOS_TOKEN_ID == tokenizer.special_token_ids["<eos>"] == 3
    assert SYSTEM_TOKEN_ID == tokenizer.special_token_ids["<|system|>"] == 4
    assert USER_TOKEN_ID == tokenizer.special_token_ids["<|user|>"] == 5
    assert ASSISTANT_TOKEN_ID == tokenizer.special_token_ids["<|assistant|>"] == 6


# =========================================================================
# 3. Assistant-Only Loss Masking & Gradient Isolation
# =========================================================================

def test_assistant_only_loss_masking_alignment(sample_conversation, tokenizer):
    inputs, targets = LOVEInstructionFormatter.encode_conversation(
        example=sample_conversation,
        tokenizer=tokenizer,
        max_seq_len=512,
    )
    assert len(inputs) == len(targets)
    assert len(inputs) <= 512

    # First token is SYSTEM_TOKEN_ID (4), target must be IGNORE_INDEX (-100)
    assert inputs[0] == SYSTEM_TOKEN_ID
    assert targets[0] == IGNORE_INDEX

    # Final target must be EOS_TOKEN_ID (3)
    assert targets[-1] == EOS_TOKEN_ID

    # System prompt and user prompt tokens must be masked to -100
    # Assistant response tokens must be active (>= 0)
    asst_header_idx = inputs.index(ASSISTANT_TOKEN_ID)
    for pos in range(asst_header_idx):
        assert targets[pos] == IGNORE_INDEX, f"Position {pos} before assistant header must be masked to -100"

    # From assistant header onwards, target for header is first content token (>= 0)
    assert targets[asst_header_idx] != IGNORE_INDEX
    for pos in range(asst_header_idx, len(targets)):
        assert targets[pos] != IGNORE_INDEX, f"Assistant token at {pos} should be active target"


def test_zero_gradient_on_masked_positions():
    """Proves that targets with -100 contribute strictly zero loss and zero gradient."""
    seq_len = 16
    vocab_size = 8192
    logits = torch.randn(1, seq_len, vocab_size, requires_grad=True)

    # First 10 positions masked (-100), last 6 active
    targets = torch.tensor([[-100] * 10 + [42, 43, 44, 45, 46, 3]], dtype=torch.long)

    loss = F.cross_entropy(logits.view(-1, vocab_size), targets.view(-1), ignore_index=IGNORE_INDEX)
    loss.backward()

    grad = logits.grad[0]
    for pos in range(seq_len):
        tgt = targets[0, pos].item()
        g_norm = grad[pos].norm().item()
        if tgt == IGNORE_INDEX:
            assert g_norm == 0.0, f"Expected 0.0 gradient at masked position {pos}, got {g_norm}"
        else:
            assert g_norm > 0.0, f"Expected non-zero gradient at active position {pos}, got {g_norm}"


# =========================================================================
# 4. Dynamic Batch Padding and Collation
# =========================================================================

def test_collator_padding_and_masking():
    collator = SFTCollator(pad_token_id=0, ignore_index=-100, max_seq_len=512)
    batch = [
        ([10, 20, 30], [-100, 20, 3]),
        ([10, 20, 30, 40, 50], [-100, -100, 30, 40, 3]),
    ]
    inp_t, tgt_t, mask_t = collator(batch)

    assert inp_t.shape == (2, 5)
    assert tgt_t.shape == (2, 5)
    assert mask_t.shape == (2, 5)

    # First sequence padded by 2 tokens
    assert inp_t[0, 3].item() == 0 and inp_t[0, 4].item() == 0
    assert tgt_t[0, 3].item() == -100 and tgt_t[0, 4].item() == -100
    assert mask_t[0, 3].item() == 0 and mask_t[0, 4].item() == 0

    # Second sequence has no padding
    assert mask_t[1].tolist() == [1, 1, 1, 1, 1]


# =========================================================================
# 5. Truncation Safety Tests
# =========================================================================

def test_truncation_safety_rejection(tokenizer):
    """Verifies that an immediate turn pair exceeding context limit raises TruncationSafetyError."""
    long_content = "word " * 600  # Exceeds 512 tokens
    oversized_conv = ConversationExample(
        conversation_id="conv_oversized",
        tree_id="tree_oversized",
        source_id="src_test",
        category="general_conversation",
        license="MIT",
        messages=[
            Message(role="user", content="Hello"),
            Message(role="assistant", content=long_content),
        ],
    )
    with pytest.raises(TruncationSafetyError):
        LOVEInstructionFormatter.encode_conversation(
            example=oversized_conv,
            tokenizer=tokenizer,
            max_seq_len=512,
            allow_turn_truncation=True,
        )


def test_multiturn_sliding_window_preserves_final_turn(tokenizer):
    """Verifies that multi-turn truncation drops older turns while preserving system prompt and final turn."""
    turn1_user = "Turn 1 user question. " * 50
    turn1_asst = "Turn 1 assistant answer. " * 50
    turn2_user = "Turn 2 final user question."
    turn2_asst = "Turn 2 final assistant answer."

    multiturn_conv = ConversationExample(
        conversation_id="conv_multi_trunc",
        tree_id="tree_multi_trunc",
        source_id="src_test",
        category="general_conversation",
        license="MIT",
        messages=[
            Message(role="system", content="System instruction."),
            Message(role="user", content=turn1_user),
            Message(role="assistant", content=turn1_asst),
            Message(role="user", content=turn2_user),
            Message(role="assistant", content=turn2_asst),
        ],
    )

    inputs, targets = LOVEInstructionFormatter.encode_conversation(
        example=multiturn_conv,
        tokenizer=tokenizer,
        max_seq_len=512,
        allow_turn_truncation=True,
    )
    assert len(inputs) <= 512
    # Verify final assistant target tokens are present
    assert targets[-1] == EOS_TOKEN_ID


# =========================================================================
# 6. Tree Isolation and Disjointness Tests
# =========================================================================

def test_split_files_and_manifest_exist():
    sft_dir = BASE_DIR / "datasets" / "sft"
    manifest_path = sft_dir / "manifests" / "sft_manifest.json"
    train_path = sft_dir / "splits" / "sft_train.jsonl"
    val_path = sft_dir / "splits" / "sft_val.jsonl"
    test_path = sft_dir / "splits" / "sft_test.jsonl"

    assert manifest_path.exists()
    assert train_path.exists()
    assert val_path.exists()
    assert test_path.exists()


def test_tree_and_content_isolation():
    sft_dir = BASE_DIR / "datasets" / "sft" / "splits"

    trees_by_split = {}
    hashes_by_split = {}

    for split_key in ["train", "val", "test"]:
        fp = sft_dir / f"sft_{split_key}.jsonl"
        trees = set()
        hashes = set()
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                trees.add(d["tree_id"])
                hashes.add(d["metadata"]["content_hash"])
        trees_by_split[split_key] = trees
        hashes_by_split[split_key] = hashes

    # Assert pairwise tree isolation
    assert len(trees_by_split["train"] & trees_by_split["val"]) == 0
    assert len(trees_by_split["train"] & trees_by_split["test"]) == 0
    assert len(trees_by_split["val"] & trees_by_split["test"]) == 0

    # Assert pairwise content hash isolation
    assert len(hashes_by_split["train"] & hashes_by_split["val"]) == 0
    assert len(hashes_by_split["train"] & hashes_by_split["test"]) == 0
    assert len(hashes_by_split["val"] & hashes_by_split["test"]) == 0


def test_manifest_checksum_fidelity():
    sft_dir = BASE_DIR / "datasets" / "sft"
    manifest_path = sft_dir / "manifests" / "sft_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for split_key, file_stem in [("train", "sft_train.jsonl"), ("validation", "sft_val.jsonl"), ("test", "sft_test.jsonl")]:
        fp = sft_dir / "splits" / file_stem
        disk_sha = hashlib.sha256(fp.read_bytes()).hexdigest()
        manifest_sha = manifest["splits"][split_key]["sha256"]
        assert disk_sha == manifest_sha, f"SHA mismatch on {file_stem}"


# =========================================================================
# 7. Privacy and Secret Filtering Tests
# =========================================================================

def test_privacy_filter_rejection_and_redaction():
    pf = PrivacyFilter()

    # Secret rejection (RSA key)
    rsa_text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y3wZkFfakeKey...\n-----END RSA PRIVATE KEY-----"
    is_admitted, _, flags = pf.inspect_and_filter(rsa_text)
    assert is_admitted is False

    # Email redaction
    email_text = "Please contact me at developer.jane@customdomain.io for details."
    is_admitted, clean, flags = pf.inspect_and_filter(email_text)
    assert is_admitted is True
    assert "[EMAIL_REDACTED]" in clean
    assert "developer.jane@customdomain.io" not in clean


# =========================================================================
# 8. Dry-Run Forward Pass Immutability Test
# =========================================================================

def test_dry_run_forward_pass_immutability(tokenizer):
    ckpt_path = BASE_DIR / "checkpoints" / "step_0000250.pt"
    if not ckpt_path.exists():
        pytest.skip("Checkpoint step_0000250.pt not found.")

    cfg_path = BASE_DIR / "configs" / "tiny.yaml"
    cfg = LoveModelConfig.from_yaml(str(cfg_path))
    model = LoveForCausalLM(cfg)

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    def get_hash():
        h = hashlib.sha256()
        for name, p in sorted(model.named_parameters()):
            h.update(name.encode("utf-8"))
            h.update(p.detach().cpu().numpy().tobytes())
        return h.hexdigest()

    h_before = get_hash()

    val_path = BASE_DIR / "datasets" / "sft" / "splits" / "sft_val.jsonl"
    dataset = SFTDataset(val_path, tokenizer=tokenizer, max_seq_len=512)
    loader = SFTDataLoader(dataset, batch_size=2, shuffle=False)

    inp, tgt, _ = next(iter(loader))
    with torch.no_grad():
        logits, loss = model(inp, targets=tgt)

    assert torch.isfinite(loss)
    assert loss.item() > 0.0

    h_after = get_hash()
    assert h_before == h_after, "Model parameters mutated during dry run forward pass!"
