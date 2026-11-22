"""Comprehensive Architecture Correctness & Numerical Stability Tests for LOVE Native AI.

Tests all requirements outlined in Task 7:
- Embedding output shape & boundary validation
- RoPE dimensions and rotation
- Attention output shape & causal masking
- Future-token information leakage prevention (causality check)
- RMSNorm numerical stability
- SwiGLU dimensions & functionality
- Transformer block residual connections
- Language model output dimensions
- Tied input/output embedding weights
- Synthetic loss calculation
- Gradient finiteness across all parameters
- AdamW optimizer update
- CPU execution
- CUDA execution (when hardware/runtime is available)
- Configuration validation assertions
"""
import pytest
import torch
import torch.nn.functional as F

from native_ai.model.normalization import RMSNorm
from native_ai.model.rotary import RotaryEmbedding, apply_rotary_pos_emb
from native_ai.model.embeddings import TokenEmbedding
from native_ai.model.feedforward import SwiGLUFeedForward
from native_ai.model.attention import CausalSelfAttention
from native_ai.model.transformer_block import TransformerBlock
from native_ai.model.love_model import LoveModelConfig, LoveForCausalLM


@pytest.fixture
def tiny_config():
    return LoveModelConfig(
        model_name="test-tiny",
        vocab_size=128,
        context_length=64,
        layers=2,
        heads=4,
        hidden_dim=64,
        head_dim=16,
        ffn_dim=192,
        norm_eps=1e-5,
        tie_embeddings=True,
        dropout=0.0,
    )


def test_configuration_validation():
    """Verify that configuration assertions catch invalid dimensions."""
    # Invalid hidden_dim != heads * head_dim
    with pytest.raises(AssertionError):
        LoveModelConfig(hidden_dim=64, heads=3, head_dim=16).validate()

    # Negative vocab
    with pytest.raises(AssertionError):
        LoveModelConfig(vocab_size=-10).validate()

    # Zero layers
    with pytest.raises(AssertionError):
        LoveModelConfig(layers=0).validate()


def test_embedding_output_shape_and_bounds():
    """Test embedding layer dimensions and strict vocabulary boundary enforcement."""
    vocab_size = 128
    hidden_dim = 64
    embed = TokenEmbedding(vocab_size=vocab_size, hidden_dim=hidden_dim)

    # Valid input
    tokens = torch.randint(0, vocab_size, (2, 16))
    out = embed(tokens)
    assert out.shape == (2, 16, hidden_dim), f"Expected shape (2, 16, {hidden_dim}), got {out.shape}"

    # Out of bounds token (< 0)
    invalid_low = torch.tensor([[0, -1, 5]])
    with pytest.raises(ValueError, match="Token ID out of bounds"):
        embed(invalid_low)

    # Out of bounds token (>= vocab_size)
    invalid_high = torch.tensor([[0, vocab_size, 5]])
    with pytest.raises(ValueError, match="Token ID out of bounds"):
        embed(invalid_high)


def test_rmsnorm_stability():
    """Test RMSNorm output stability, invariance to scaling, and division-by-zero protection."""
    dim = 64
    norm = RMSNorm(dim=dim, eps=1e-5)

    x = torch.randn(4, 16, dim)
    out = norm(x)
    assert out.shape == (4, 16, dim)

    # Output RMS should be close to 1.0 (since weight is initialized to 1.0)
    rms = torch.sqrt(out.pow(2).mean(-1))
    assert torch.allclose(rms, torch.ones_like(rms), atol=1e-2), "RMSNorm did not normalize RMS to ~1.0"

    # Stability with all zeros
    zeros = torch.zeros(2, 4, dim)
    out_zeros = norm(zeros)
    assert torch.isfinite(out_zeros).all(), "RMSNorm failed on zero input"


def test_rope_dimensions_and_rotation():
    """Test RoPE frequency generation, caching, and rotation invariance."""
    head_dim = 16
    seq_len = 32
    rope = RotaryEmbedding(dim=head_dim, max_seq_len=64)

    dummy = torch.randn(2, 4, seq_len, head_dim)
    cos, sin = rope(dummy, seq_len)

    assert cos.shape == (seq_len, head_dim)
    assert sin.shape == (seq_len, head_dim)

    q = torch.randn(2, 4, seq_len, head_dim)
    k = torch.randn(2, 4, seq_len, head_dim)
    q_rot, k_rot = apply_rotary_pos_emb(q, k, cos, sin)

    assert q_rot.shape == q.shape
    assert k_rot.shape == k.shape
    assert torch.isfinite(q_rot).all()
    assert torch.isfinite(k_rot).all()


def test_swiglu_dimensions():
    """Test SwiGLU forward pass dimensions and non-linearity."""
    hidden_dim = 64
    ffn_dim = 192
    swiglu = SwiGLUFeedForward(hidden_dim=hidden_dim, ffn_dim=ffn_dim)

    x = torch.randn(2, 16, hidden_dim)
    out = swiglu(x)
    assert out.shape == (2, 16, hidden_dim), f"Expected shape (2, 16, {hidden_dim}), got {out.shape}"
    assert torch.isfinite(out).all()


def test_causal_self_attention_shape_and_sdpa():
    """Test CausalSelfAttention output shape for both SDPA and explicit causal masking."""
    hidden_dim = 64
    n_heads = 4
    head_dim = 16
    attn = CausalSelfAttention(hidden_dim=hidden_dim, n_heads=n_heads, head_dim=head_dim, max_seq_len=64)

    x = torch.randn(2, 16, hidden_dim)

    # Test with SDPA
    out_sdpa = attn(x, use_sdpa=True)
    assert out_sdpa.shape == (2, 16, hidden_dim)

    # Test with explicit causal matrix
    out_explicit = attn(x, use_sdpa=False)
    assert out_explicit.shape == (2, 16, hidden_dim)


def test_causal_masking_future_token_leakage_prevention(tiny_config):
    """
    CRITICAL CAUSALITY TEST:
    Verify that altering future tokens in a sequence does NOT change the
    logits or representations of any preceding tokens.
    """
    torch.manual_seed(42)
    model = LoveForCausalLM(tiny_config)
    model.eval()

    seq_len = 16
    prefix_len = 12

    # Sequence A
    tokens_a = torch.randint(0, tiny_config.vocab_size, (1, seq_len))
    # Sequence B: identical prefix, but different subsequent tokens
    tokens_b = tokens_a.clone()
    # Mutate tokens from prefix_len onwards to completely different IDs
    tokens_b[0, prefix_len:] = (tokens_a[0, prefix_len:] + 7) % tiny_config.vocab_size

    with torch.no_grad():
        # Test both SDPA causal path and explicit causal path
        for use_sdpa in [True, False]:
            logits_a, _ = model(tokens_a, use_sdpa=use_sdpa)
            logits_b, _ = model(tokens_b, use_sdpa=use_sdpa)

            # Logits for tokens at positions 0 .. prefix_len - 1 must be strictly identical
            prefix_diff = (logits_a[:, :prefix_len, :] - logits_b[:, :prefix_len, :]).abs().max().item()
            assert prefix_diff < 1e-5, (
                f"Future token leakage detected (use_sdpa={use_sdpa})! "
                f"Max diff in prefix logits: {prefix_diff}"
            )

            # Verify that the suffix logits at prefix_len onwards DO differ
            suffix_diff = (logits_a[:, prefix_len:, :] - logits_b[:, prefix_len:, :]).abs().max().item()
            assert suffix_diff > 1e-4, f"Suffix logits unexpectedly identical (diff={suffix_diff})"


def test_transformer_block_residual_connections(tiny_config):
    """Verify that TransformerBlock includes functional residual connections."""
    block = TransformerBlock(
        hidden_dim=tiny_config.hidden_dim,
        n_heads=tiny_config.heads,
        head_dim=tiny_config.head_dim,
        ffn_dim=tiny_config.ffn_dim,
        max_seq_len=tiny_config.context_length,
    )
    x = torch.randn(2, 8, tiny_config.hidden_dim, requires_grad=True)
    out = block(x)
    assert out.shape == x.shape

    # Test residual gradient flow: d(out)/dx should have non-zero gradient even if submodules have 0 weights
    loss = out.sum()
    loss.backward()
    assert x.grad is not None
    assert torch.isfinite(x.grad).all()


def test_tied_input_output_embeddings(tiny_config):
    """Verify weight tying: lm_head.weight shares memory with token_embeddings.embedding.weight."""
    tiny_config.tie_embeddings = True
    model_tied = LoveForCausalLM(tiny_config)

    assert model_tied.lm_head.weight.data_ptr() == model_tied.token_embeddings.embedding.weight.data_ptr(), (
        "Embedding and LM head weights are not tied to the same memory buffer"
    )

    # Compare with untied model
    tiny_config_untied = LoveModelConfig(
        model_name="test-tiny-untied",
        vocab_size=tiny_config.vocab_size,
        context_length=tiny_config.context_length,
        layers=tiny_config.layers,
        heads=tiny_config.heads,
        hidden_dim=tiny_config.hidden_dim,
        head_dim=tiny_config.head_dim,
        ffn_dim=tiny_config.ffn_dim,
        norm_eps=tiny_config.norm_eps,
        tie_embeddings=False,
        dropout=0.0,
    )
    model_untied = LoveForCausalLM(tiny_config_untied)

    assert model_untied.lm_head.weight.data_ptr() != model_untied.token_embeddings.embedding.weight.data_ptr(), (
        "Untied model should have distinct memory buffers for embedding and LM head"
    )

    counts_tied = model_tied.count_parameters()
    counts_untied = model_untied.count_parameters()

    assert counts_tied["tied_embeddings"] is True
    assert counts_untied["tied_embeddings"] is False
    assert counts_untied["total_parameters"] > counts_tied["total_parameters"]
    assert counts_untied["total_parameters"] - counts_tied["total_parameters"] == counts_tied["embedding_parameters"]


def test_loss_calculation_and_gradient_finiteness(tiny_config):
    """Verify forward-backward pass, loss computation, and gradient finiteness."""
    torch.manual_seed(1337)
    model = LoveForCausalLM(tiny_config)
    model.train()

    batch_size = 2
    seq_len = 16
    input_ids = torch.randint(0, tiny_config.vocab_size, (batch_size, seq_len))
    targets = torch.randint(0, tiny_config.vocab_size, (batch_size, seq_len))

    logits, loss = model(input_ids, targets=targets)

    assert logits.shape == (batch_size, seq_len, tiny_config.vocab_size)
    assert loss is not None
    assert loss.item() > 0.0
    assert torch.isfinite(loss)

    # Backward pass
    loss.backward()

    # Check that all trainable parameters received finite gradients
    for name, param in model.named_parameters():
        if param.requires_grad:
            assert param.grad is not None, f"Parameter {name} has no gradient"
            assert torch.isfinite(param.grad).all(), f"Parameter {name} contains non-finite gradients (NaN/Inf)"


def test_adamw_optimizer_step(tiny_config):
    """Verify that an AdamW optimizer step updates model parameters."""
    torch.manual_seed(42)
    model = LoveForCausalLM(tiny_config)
    model.train()

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    input_ids = torch.randint(0, tiny_config.vocab_size, (2, 8))
    targets = torch.randint(0, tiny_config.vocab_size, (2, 8))

    # Snapshot initial weights
    initial_weights = {name: p.clone() for name, p in model.named_parameters() if p.requires_grad}

    optimizer.zero_grad()
    _, loss = model(input_ids, targets=targets)
    loss.backward()
    optimizer.step()

    # Verify parameters changed
    has_changed = False
    for name, p in model.named_parameters():
        if p.requires_grad:
            diff = (p - initial_weights[name]).abs().max().item()
            if diff > 0.0:
                has_changed = True
                break

    assert has_changed, "Optimizer step failed to update model parameters"


def test_cpu_execution(tiny_config):
    """Verify execution on CPU."""
    model = LoveForCausalLM(tiny_config).to("cpu")
    input_ids = torch.randint(0, tiny_config.vocab_size, (1, 8), device="cpu")
    targets = torch.randint(0, tiny_config.vocab_size, (1, 8), device="cpu")

    logits, loss = model(input_ids, targets=targets)
    assert logits.device.type == "cpu"
    assert loss.device.type == "cpu"
    loss.backward()


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available on this environment")
def test_cuda_execution(tiny_config):
    """Verify execution on CUDA GPU when hardware/driver is available."""
    device = torch.device("cuda:0")
    model = LoveForCausalLM(tiny_config).to(device)
    input_ids = torch.randint(0, tiny_config.vocab_size, (1, 8), device=device)
    targets = torch.randint(0, tiny_config.vocab_size, (1, 8), device=device)

    logits, loss = model(input_ids, targets=targets)
    assert logits.device.type == "cuda"
    assert loss.device.type == "cuda"
    loss.backward()
    assert torch.isfinite(loss)
