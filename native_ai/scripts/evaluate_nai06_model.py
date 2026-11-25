"""LOVE Native AI — Phase NAI-06: Model Evaluation & Capability Assessment.

Evaluates LOVE's first pretrained model (love-native-tiny, step 250):
- Checkpoint verification (SHA-256 sidecar, config, parameter count, finiteness).
- Full validation-set evaluation (all 1,904 documents, 933,909 tokens) comparing Step 0 vs Step 250.
- Category-level and source-level cross-entropy loss and perplexity.
- Text generation quality evaluation across 4 training domains (greedy & sampling).
- Numerical stability, causal attention masking, tokenizer round-trip, and inference telemetry.
- Strict parameter immutability verification (diff = 0.0 before and after evaluation).
- Export results to experiments/nai_06_evaluation/nai_06_evaluation_results.json.
"""
import sys
import os
import time
import json
import math
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import torch
import torch.nn.functional as F
import numpy as np

# Set project root on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR.parent))

from native_ai.model.love_model import LoveForCausalLM, LoveModelConfig
from native_ai.tokenizer.love_tokenizer import LoveTokenizer
from native_ai.data_cache.binary_cache import BinaryTokenDataset, CATEGORY_MAP, REV_CATEGORY_MAP
from native_ai.data_cache.dataloader import CausalDataLoader
from native_ai.training.checkpoint_manager import CheckpointManager


def verify_checkpoint(
    ckpt_path: Path,
    expected_step: int,
) -> Tuple[LoveForCausalLM, Dict[str, Any]]:
    """
    Verifies checkpoint SHA-256 sidecar, loads into fresh model instance,
    verifies configuration, parameter count, finiteness, and returns model and payload.
    """
    print(f"Verifying checkpoint: {ckpt_path.name}...")
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")

    # 1. Verify SHA-256 sidecar
    meta_path = ckpt_path.with_suffix(".json")
    if not meta_path.exists():
        raise FileNotFoundError(f"Checkpoint metadata sidecar missing: {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta_info = json.load(f)

    actual_sha = hashlib.sha256(ckpt_path.read_bytes()).hexdigest()
    expected_sha = meta_info.get("sha256")
    if actual_sha != expected_sha:
        raise ValueError(f"Checkpoint SHA-256 mismatch for {ckpt_path.name}: expected {expected_sha}, got {actual_sha}")
    print(f"  [Pass] SHA-256 Checksum Verified: {actual_sha[:16]}...")

    # 2. Load into fresh model instance
    cfg_path = BASE_DIR / "configs" / "tiny.yaml"
    cfg = LoveModelConfig.from_yaml(str(cfg_path))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = LoveForCausalLM(cfg).to(device)

    ckpt_mgr = CheckpointManager(checkpoint_dir=ckpt_path.parent)
    payload = ckpt_mgr.load_checkpoint(ckpt_path, model, device=device)

    # 3. Verify step
    step = payload.get("step")
    if step != expected_step:
        raise ValueError(f"Step mismatch in {ckpt_path.name}: expected {expected_step}, got {step}")
    print(f"  [Pass] Checkpoint Step Confirmed: {step}")

    # 4. Verify parameter count
    total_params = sum(p.numel() for p in model.parameters())
    if total_params != 5507328:
        raise ValueError(f"Parameter count mismatch: expected 5,507,328, got {total_params}")
    print(f"  [Pass] Model Parameter Count: {total_params:,}")

    # 5. Verify finiteness
    for name, p in model.named_parameters():
        if not torch.isfinite(p).all():
            raise FloatingPointError(f"Non-finite parameter detected in {name}!")
    print(f"  [Pass] Parameter Finiteness: All 38 parameter tensors are completely finite (zero NaN / Inf).")

    return model, {
        "checkpoint_file": ckpt_path.name,
        "step": step,
        "sha256": actual_sha,
        "file_size_bytes": ckpt_path.stat().st_size,
        "experiment_id": payload.get("training_config", {}).get("experiment_id", "exp_nai05_pilot_001"),
    }


def evaluate_full_validation_set(
    model: LoveForCausalLM,
    val_ds: BinaryTokenDataset,
    device: torch.device,
    category_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates model across the validation split sequentially using sliding context windows of 512.
    Optionally filters by specific category.
    Runs strictly within torch.no_grad().
    """
    model.eval()
    if category_filter is not None:
        doc_indices = val_ds.get_doc_indices_for_category(category_filter)
    else:
        doc_indices = np.arange(val_ds.num_documents)

    total_loss_sum = 0.0
    total_tokens_evaluated = 0
    total_documents_evaluated = len(doc_indices)
    seq_len = model.config.context_length  # 512

    # Telemetry
    logit_mins = []
    logit_maxs = []
    logit_means = []

    t0 = time.perf_counter()
    if device.type == "cuda":
        torch.cuda.synchronize()

    with torch.no_grad():
        for doc_idx in doc_indices:
            tokens, cat_name = val_ds.get_document(int(doc_idx))
            num_tokens = len(tokens)
            if num_tokens < 2:
                continue

            # Process in non-overlapping chunks of up to 512 tokens
            # We predict each token causally: inputs = chunk[:-1], targets = chunk[1:]
            for start in range(0, num_tokens - 1, seq_len):
                end = min(start + seq_len + 1, num_tokens)
                chunk = tokens[start:end]
                if len(chunk) < 2:
                    continue

                inp = torch.tensor(chunk[:-1], dtype=torch.long, device=device).unsqueeze(0)
                tgt = torch.tensor(chunk[1:], dtype=torch.long, device=device).unsqueeze(0)

                logits, loss = model(inp, targets=tgt)
                eval_tokens = tgt.numel()
                total_loss_sum += loss.item() * eval_tokens
                total_tokens_evaluated += eval_tokens

                # Track logit telemetry sample
                if len(logit_means) < 100:
                    logit_mins.append(logits.min().item())
                    logit_maxs.append(logits.max().item())
                    logit_means.append(logits.mean().item())

    if device.type == "cuda":
        torch.cuda.synchronize()
    duration = time.perf_counter() - t0

    avg_loss = total_loss_sum / total_tokens_evaluated if total_tokens_evaluated > 0 else 0.0
    perplexity = math.exp(min(avg_loss, 20.0))
    throughput = total_tokens_evaluated / duration if duration > 0 else 0.0

    alloc_mb = torch.cuda.memory_allocated(0) / (1024 * 1024) if device.type == "cuda" else 0.0
    res_mb = torch.cuda.memory_reserved(0) / (1024 * 1024) if device.type == "cuda" else 0.0

    return {
        "category_filter": category_filter or "all_categories",
        "documents_evaluated": total_documents_evaluated,
        "tokens_evaluated": total_tokens_evaluated,
        "cross_entropy_loss": round(avg_loss, 4),
        "perplexity": round(perplexity, 2),
        "evaluation_duration_seconds": round(duration, 3),
        "throughput_tokens_per_sec": round(throughput, 1),
        "vram_allocated_mb": round(alloc_mb, 2),
        "vram_reserved_mb": round(res_mb, 2),
        "logit_stats": {
            "sample_min_logit": round(float(np.mean(logit_mins)), 3) if logit_mins else 0.0,
            "sample_max_logit": round(float(np.mean(logit_maxs)), 3) if logit_maxs else 0.0,
            "sample_mean_logit": round(float(np.mean(logit_means)), 3) if logit_means else 0.0,
        },
    }


def evaluate_generation_quality(
    model: LoveForCausalLM,
    tokenizer: LoveTokenizer,
    device: torch.device,
    prompts: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """
    Generates text continuations for a fixed collection of prompts under both
    Greedy (temperature=0.0) and Sampling (temperature=0.7, top_k=40, seed=42) configurations.
    """
    results = []

    for prompt_info in prompts:
        domain = prompt_info["domain"]
        prompt_text = prompt_info["prompt"]
        prompt_tokens = tokenizer.encode(prompt_text)
        prompt_tensor = torch.tensor(prompt_tokens, dtype=torch.long, device=device).unsqueeze(0)

        for mode, temp, top_k in [("greedy", 0.0, None), ("sampling_temp0.7_k40", 0.7, 40)]:
            # Fixed seed for sampling
            if mode != "greedy":
                torch.manual_seed(42)
                if device.type == "cuda":
                    torch.cuda.manual_seed(42)

            t0 = time.perf_counter()
            if device.type == "cuda":
                torch.cuda.synchronize()

            max_new = 48
            output_tensor = model.generate(
                prompt_tensor,
                max_new_tokens=max_new,
                temperature=temp,
                top_k=top_k,
            )

            if device.type == "cuda":
                torch.cuda.synchronize()
            gen_dur = time.perf_counter() - t0

            generated_ids = output_tensor[0, len(prompt_tokens):].tolist()
            full_text = tokenizer.decode(output_tensor[0].tolist())
            continuation_text = tokenizer.decode(generated_ids)

            # Check if EOS (<|endoftext|>, ID 2) was generated
            has_eos = (2 in generated_ids)
            eos_position = generated_ids.index(2) if has_eos else None

            # Detect repetition
            words = continuation_text.split()
            repetition_detected = False
            if len(words) >= 6:
                for w_idx in range(len(words) - 3):
                    ngram = words[w_idx : w_idx + 3]
                    if words.count(ngram[0]) > 4:
                        repetition_detected = True
                        break

            results.append({
                "domain": domain,
                "prompt": prompt_text,
                "decoding_mode": mode,
                "temperature": temp,
                "top_k": top_k,
                "prompt_token_count": len(prompt_tokens),
                "generated_token_count": len(generated_ids),
                "generation_latency_ms": round(gen_dur * 1000.0, 2),
                "per_token_latency_ms": round((gen_dur * 1000.0) / max_new, 2),
                "has_eos_token": has_eos,
                "eos_token_position": eos_position,
                "repetition_detected": repetition_detected,
                "continuation_text": continuation_text,
                "full_output_text": full_text,
            })

    return results


def run_numerical_and_architecture_checks(
    model: LoveForCausalLM,
    tokenizer: LoveTokenizer,
    device: torch.device,
) -> Dict[str, Any]:
    """
    Performs numerical stability, causal attention masking, tokenizer round-trip,
    and parameter immutability checks.
    """
    print("\nExecuting Numerical & Architecture Integrity Checks...")
    checks = {}

    # 1. Parameter Finiteness
    nan_count = 0
    inf_count = 0
    for name, p in model.named_parameters():
        nan_count += torch.isnan(p).sum().item()
        inf_count += torch.isinf(p).sum().item()
    checks["parameter_nans"] = nan_count
    checks["parameter_infs"] = inf_count
    print(f"  [Check 1/5] Parameter Finiteness: {nan_count} NaNs, {inf_count} Infs")

    # 2. Causal Masking Validation (Future Token Leakage Check)
    # Take input [A, B, C, D], compute logits for B.
    # Change D to D'. Logits for B must remain bitwise identical.
    seq_test_1 = torch.tensor([[100, 200, 300, 400]], dtype=torch.long, device=device)
    seq_test_2 = torch.tensor([[100, 200, 300, 7500]], dtype=torch.long, device=device)
    with torch.no_grad():
        logits_1, _ = model(seq_test_1)
        logits_2, _ = model(seq_test_2)
    # Compare position 1 (predicting after token 200)
    causal_diff = (logits_1[0, 1] - logits_2[0, 1]).abs().max().item()
    checks["causal_mask_future_leakage_diff"] = causal_diff
    print(f"  [Check 2/5] Causal Attention Masking: Future token mutation diff at past positions = {causal_diff:.10f}")

    # 3. Tokenizer Round-Trip Consistency
    sample_phrases = [
        "The quick brown fox jumps over the lazy dog.",
        "Maria has 5 apples, and she gives 2 to Lily: 5 - 2 = 3.",
        "User: How are you?\nAssistant: I am doing well, thank you!",
        "Special symbols: !@#$%^&*()_+-=[]{}|;':,.<>/?`~",
    ]
    round_trip_success = True
    for phrase in sample_phrases:
        enc = tokenizer.encode(phrase)
        dec = tokenizer.decode(enc)
        if dec != phrase:
            round_trip_success = False
            break
    checks["tokenizer_round_trip_passed"] = round_trip_success
    print(f"  [Check 3/5] Tokenizer Round-Trip Fidelity: {round_trip_success}")

    # 4. Max Length & Generation Termination Handling
    prompt = torch.tensor([[50, 150]], dtype=torch.long, device=device)
    gen_bounded = model.generate(prompt, max_new_tokens=16, temperature=0.0)
    checks["generation_length_correct"] = (gen_bounded.shape[1] == 18)
    print(f"  [Check 4/5] Generation Length Bounding: Expected 18 tokens, got {gen_bounded.shape[1]}")

    # 5. Inference Latency Benchmark
    t0 = time.perf_counter()
    if device.type == "cuda":
        torch.cuda.synchronize()
    for _ in range(10):
        _ = model.generate(prompt, max_new_tokens=32, temperature=0.0)
    if device.type == "cuda":
        torch.cuda.synchronize()
    infer_dur = (time.perf_counter() - t0) / 10.0
    ms_per_token = (infer_dur * 1000.0) / 32.0
    checks["inference_latency_ms_per_token"] = round(ms_per_token, 2)
    print(f"  [Check 5/5] Inference Latency: {ms_per_token:.2f} ms/token (Autoregressive Greedy)")

    return checks


def main():
    print("=" * 80)
    print("  LOVE NATIVE AI — PHASE NAI-06: MODEL EVALUATION & CAPABILITY AUDIT")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cache_dir = BASE_DIR / "data_cache"
    ckpt_dir = BASE_DIR / "checkpoints"
    results_dir = BASE_DIR / "experiments" / "nai_06_evaluation"
    results_dir.mkdir(parents=True, exist_ok=True)

    tok_dir = BASE_DIR / "tokenizer" / "artifacts"
    tokenizer = LoveTokenizer.from_pretrained(tok_dir)
    val_ds = BinaryTokenDataset(cache_dir, split="validation")

    # -------------------------------------------------------------------------
    # 1. Checkpoint Verification
    # -------------------------------------------------------------------------
    print("\n[Phase 1/5] Checkpoint Verification...")
    step250_path = ckpt_dir / "step_0000250.pt"
    step0_path = ckpt_dir / "step_0000000.pt"

    trained_model, step250_meta = verify_checkpoint(step250_path, expected_step=250)
    step0_model, step0_meta = verify_checkpoint(step0_path, expected_step=0)

    # Snapshot trained model weights to ensure immutability throughout evaluation
    weights_before_eval = {n: p.clone().detach().cpu() for n, p in trained_model.named_parameters()}

    # -------------------------------------------------------------------------
    # 2. Full Validation-Set Evaluation
    # -------------------------------------------------------------------------
    print("\n[Phase 2/5] Full Validation-Set Evaluation (All 1,904 Documents, 933,909 Tokens)...")

    # A. Trained Model (Step 250)
    print("  Evaluating Trained Model (Step 250) on entire validation split...")
    eval_250_all = evaluate_full_validation_set(trained_model, val_ds, device, category_filter=None)
    print(f"    Total Tokens: {eval_250_all['tokens_evaluated']:,} | Loss: {eval_250_all['cross_entropy_loss']} | Perplexity: {eval_250_all['perplexity']}")

    print("  Evaluating Trained Model (Step 250) on english_synthetic_stories (TinyStories)...")
    eval_250_stories = evaluate_full_validation_set(trained_model, val_ds, device, category_filter="english_synthetic_stories")
    print(f"    Stories Tokens: {eval_250_stories['tokens_evaluated']:,} | Loss: {eval_250_stories['cross_entropy_loss']} | Perplexity: {eval_250_stories['perplexity']}")

    print("  Evaluating Trained Model (Step 250) on instruction_dialog (OASST1)...")
    eval_250_dialog = evaluate_full_validation_set(trained_model, val_ds, device, category_filter="instruction_dialog")
    print(f"    Dialog Tokens: {eval_250_dialog['tokens_evaluated']:,} | Loss: {eval_250_dialog['cross_entropy_loss']} | Perplexity: {eval_250_dialog['perplexity']}")

    # B. Untrained Model (Step 0)
    print("\n  Evaluating Untrained Model (Step 0) on entire validation split...")
    eval_0_all = evaluate_full_validation_set(step0_model, val_ds, device, category_filter=None)
    print(f"    Total Tokens: {eval_0_all['tokens_evaluated']:,} | Loss: {eval_0_all['cross_entropy_loss']} | Perplexity: {eval_0_all['perplexity']}")

    print("  Evaluating Untrained Model (Step 0) on english_synthetic_stories (TinyStories)...")
    eval_0_stories = evaluate_full_validation_set(step0_model, val_ds, device, category_filter="english_synthetic_stories")
    print(f"    Stories Tokens: {eval_0_stories['tokens_evaluated']:,} | Loss: {eval_0_stories['cross_entropy_loss']} | Perplexity: {eval_0_stories['perplexity']}")

    print("  Evaluating Untrained Model (Step 0) on instruction_dialog (OASST1)...")
    eval_0_dialog = evaluate_full_validation_set(step0_model, val_ds, device, category_filter="instruction_dialog")
    print(f"    Dialog Tokens: {eval_0_dialog['tokens_evaluated']:,} | Loss: {eval_0_dialog['cross_entropy_loss']} | Perplexity: {eval_0_dialog['perplexity']}")

    # -------------------------------------------------------------------------
    # 3. Text Generation Quality Evaluation
    # -------------------------------------------------------------------------
    print("\n[Phase 3/5] Text Generation Quality Assessment across 4 Domains...")
    test_prompts = [
        {
            "domain": "general_english",
            "prompt": "The morning sun began to rise over the quiet town, and",
        },
        {
            "domain": "short_narrative_continuation",
            "prompt": "Once upon a time, a little girl named Lily found a small dog. The dog was",
        },
        {
            "domain": "instruction_dialog",
            "prompt": "User: How do you solve simple problems?\nAssistant:",
        },
        {
            "domain": "elementary_mathematics",
            "prompt": "Question: Maria has 5 apples. She gives 2 apples to her brother. How many apples does she have left?\nAnswer:",
        },
    ]

    print("  Generating continuations with Trained Model (Step 250)...")
    gen_results_step250 = evaluate_generation_quality(trained_model, tokenizer, device, test_prompts)

    print("  Generating continuations with Untrained Baseline (Step 0)...")
    gen_results_step0 = evaluate_generation_quality(step0_model, tokenizer, device, test_prompts)

    # -------------------------------------------------------------------------
    # 4. Numerical and Architecture Integrity Checks
    # -------------------------------------------------------------------------
    print("\n[Phase 4/5] Numerical and Architecture Integrity Checks...")
    num_arch_checks = run_numerical_and_architecture_checks(trained_model, tokenizer, device)

    # -------------------------------------------------------------------------
    # 5. Parameter Immutability Verification
    # -------------------------------------------------------------------------
    print("\n[Phase 5/5] Parameter Immutability Verification...")
    max_mutation = 0.0
    for name, p in trained_model.named_parameters():
        p_cpu = p.detach().cpu()
        diff = (p_cpu - weights_before_eval[name]).abs().max().item()
        max_mutation = max(max_mutation, diff)

    print(f"  Maximum parameter difference before vs after evaluation: {max_mutation:.12f}")
    if max_mutation != 0.0:
        raise RuntimeError("CRITICAL SAFETY FAULT: Model weights were mutated during evaluation!")
    print("  [Pass] Model parameters remained 100% immutable throughout evaluation.")

    # -------------------------------------------------------------------------
    # 6. Collate Results & Export
    # -------------------------------------------------------------------------
    report_data = {
        "evaluation_phase": "NAI-06",
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checkpoint_step_250": step250_meta,
        "checkpoint_step_0": step0_meta,
        "validation_dataset": {
            "total_documents": val_ds.num_documents,
            "total_tokens": len(val_ds),
            "stories_documents": len(val_ds.get_doc_indices_for_category("english_synthetic_stories")),
            "dialog_documents": len(val_ds.get_doc_indices_for_category("instruction_dialog")),
        },
        "step_250_metrics": {
            "overall": eval_250_all,
            "english_synthetic_stories": eval_250_stories,
            "instruction_dialog": eval_250_dialog,
        },
        "step_0_metrics": {
            "overall": eval_0_all,
            "english_synthetic_stories": eval_0_stories,
            "instruction_dialog": eval_0_dialog,
        },
        "comparison_deltas": {
            "overall_loss_delta": round(eval_250_all["cross_entropy_loss"] - eval_0_all["cross_entropy_loss"], 4),
            "overall_perplexity_delta": round(eval_250_all["perplexity"] - eval_0_all["perplexity"], 2),
            "stories_loss_delta": round(eval_250_stories["cross_entropy_loss"] - eval_0_stories["cross_entropy_loss"], 4),
            "dialog_loss_delta": round(eval_250_dialog["cross_entropy_loss"] - eval_0_dialog["cross_entropy_loss"], 4),
        },
        "generation_samples": {
            "step_250": gen_results_step250,
            "step_0": gen_results_step0,
        },
        "numerical_and_architecture_checks": num_arch_checks,
        "parameter_immutability_verified": True,
    }

    out_file = results_dir / "nai_06_evaluation_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print("\n" + "=" * 80)
    print(f"  NAI-06 EVALUATION COMPLETE — Report saved to {out_file}")
    print("=" * 80)
    return report_data


if __name__ == "__main__":
    main()
