"""Performance Benchmarks for LOVE Native AI Pretraining Engine (Audited & Rigorous).

Implements Section 13 (NAI-04) & NAI-04.1 Audit Verification:
- Tokenization throughput (tokens/second) with statistical variation.
- Binary cache memory-mapped loading throughput (MB/second, tokens/second).
- DataLoader sequence packing and batching throughput (sequences/second, tokens/second).
- Forward-pass latency (ms) and throughput (tokens/second) for both FP32 and AMP FP16.
- Backward-pass and full training step latency (ms) on bounded synthetic data (FP32 and AMP FP16).
- Strict CUDA synchronization (torch.cuda.synchronize()) before and after every timed GPU operation.
- Explicit warm-up iterations and multiple timed repetitions reporting median, mean, std, min, max, p50, p95.
- GTX 1650 VRAM telemetry: allocated, peak allocated, reserved, peak reserved, and safe headroom (< 3500 MB).
- System RAM RSS peak (MB).
- Atomic checkpoint write and SHA-256 generation latency (ms) across multiple repetitions.
- Formal dry-run suite execution (Modes A, B, C) confirming zero weight mutation on real data.
"""
import sys
import os
import time
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import psutil
import torch
import numpy as np

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from native_ai.model.love_model import LoveForCausalLM, LoveModelConfig
from native_ai.tokenizer.love_tokenizer import LoveTokenizer
from native_ai.data_cache.binary_cache import BinaryTokenDataset
from native_ai.data_cache.sampler import DomainWeightedSampler
from native_ai.data_cache.dataloader import CausalDataLoader
from native_ai.training.device_safety import DeviceSafetyManager
from native_ai.training.checkpoint_manager import CheckpointManager
from native_ai.training.trainer import Trainer, TrainingConfig


def compute_distribution_stats(values: List[float]) -> Dict[str, float]:
    """Computes median, mean, std, min, max, p50, p90, p95 for a list of measurements."""
    arr = np.array(values, dtype=np.float64)
    return {
        "median": round(float(np.median(arr)), 3),
        "mean": round(float(np.mean(arr)), 3),
        "std": round(float(np.std(arr)), 3),
        "min": round(float(np.min(arr)), 3),
        "max": round(float(np.max(arr)), 3),
        "p50": round(float(np.percentile(arr, 50)), 3),
        "p90": round(float(np.percentile(arr, 90)), 3),
        "p95": round(float(np.percentile(arr, 95)), 3),
        "count": len(values),
    }


def run_all_benchmarks() -> Dict[str, Any]:
    print("=" * 80)
    print("  LOVE NATIVE AI: PRETRAINING ENGINE BENCHMARKS (AUDITED NAI-04.1)")
    print("=" * 80)

    base_dir = Path(__file__).resolve().parent.parent
    cache_dir = base_dir / "data_cache"
    tok_dir = base_dir / "tokenizer" / "artifacts"
    configs_dir = base_dir / "configs"

    is_cuda = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if is_cuda else "CPU"
    device_type = "cuda" if is_cuda else "cpu"

    results: Dict[str, Any] = {
        "benchmark_version": "2.0.0-audited",
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "device": device_type,
        "device_name": device_name,
        "cuda_synchronization_enforced": is_cuda,
    }

    # -------------------------------------------------------------------------
    # 1. Tokenization Throughput
    # -------------------------------------------------------------------------
    print("\n[Benchmark 1/8] Tokenization Throughput (LOVE Tokenizer v0.1)...")
    tok = LoveTokenizer.from_pretrained(tok_dir)
    sample_text = (
        "In the quiet forest, the young fox explored the hidden path behind the mossy oak tree. "
        "The mathematics of natural systems reveals intricate patterns of logarithmic growth. "
        "What is the derivative of x squared plus five times x with respect to x? "
    ) * 50  # ~1,500 words

    # Warmup
    for _ in range(5):
        _ = tok.encode(sample_text)

    # Repetitions
    tok_iterations = 40
    tok_latencies_ms = []
    tok_throughputs = []
    sample_tokens_count = len(tok.encode(sample_text))

    for _ in range(tok_iterations):
        t0 = time.perf_counter()
        _ = tok.encode(sample_text)
        dur = time.perf_counter() - t0
        tok_latencies_ms.append(dur * 1000.0)
        tok_throughputs.append(sample_tokens_count / dur)

    tok_stats = compute_distribution_stats(tok_throughputs)
    tok_lat_stats = compute_distribution_stats(tok_latencies_ms)
    print(f"  Sample tokens per encode: {sample_tokens_count}")
    print(f"  Latency (ms):    median={tok_lat_stats['median']}ms, min={tok_lat_stats['min']}ms, max={tok_lat_stats['max']}ms, std={tok_lat_stats['std']}ms")
    print(f"  Throughput:      median={tok_stats['median']:,.1f} tok/s, mean={tok_stats['mean']:,.1f} tok/s, p95={tok_stats['p95']:,.1f} tok/s")
    results["tokenization"] = {
        "sample_tokens": sample_tokens_count,
        "iterations": tok_iterations,
        "latency_ms": tok_lat_stats,
        "throughput_tokens_per_sec": tok_stats,
    }

    # -------------------------------------------------------------------------
    # 2. Binary Cache Loading Throughput (Memmap)
    # -------------------------------------------------------------------------
    print("\n[Benchmark 2/8] Binary Cache Memmap Throughput (train.bin)...")
    dataset = BinaryTokenDataset(cache_dir, split="train")
    slice_len = 512
    num_slices = 500

    # Warmup
    for i in range(20):
        start = (i * 1000) % (len(dataset) - slice_len)
        _ = dataset.get_token_slice(start, slice_len)

    # Timed repetitions (batches of 10 slices for timer resolution)
    slice_throughputs_tok = []
    slice_throughputs_mb = []
    slice_batch_size = 10
    num_batches = num_slices // slice_batch_size

    for b in range(num_batches):
        t0 = time.perf_counter()
        for i in range(slice_batch_size):
            start = ((b * slice_batch_size + i) * 5000) % (len(dataset) - slice_len)
            _ = dataset.get_token_slice(start, slice_len)
        dur = time.perf_counter() - t0
        tokens_batch = slice_batch_size * slice_len
        slice_throughputs_tok.append(tokens_batch / dur)
        slice_throughputs_mb.append((tokens_batch * 2) / (1024 * 1024 * dur))

    memmap_tok_stats = compute_distribution_stats(slice_throughputs_tok)
    memmap_mb_stats = compute_distribution_stats(slice_throughputs_mb)
    print(f"  Tokens Sliced:   {num_slices * slice_len:,} total ({num_slices} slices of len {slice_len})")
    print(f"  Throughput:      median={memmap_tok_stats['median']:,.1f} tok/s ({memmap_mb_stats['median']:.1f} MB/s)")
    print(f"                   p95={memmap_tok_stats['p95']:,.1f} tok/s ({memmap_mb_stats['p95']:.1f} MB/s)")
    results["binary_cache_memmap"] = {
        "slice_length": slice_len,
        "total_slices": num_slices,
        "throughput_tokens_per_sec": memmap_tok_stats,
        "throughput_mb_per_sec": memmap_mb_stats,
    }

    # -------------------------------------------------------------------------
    # 3. DataLoader Batching & Sequence Packing Throughput
    # -------------------------------------------------------------------------
    print("\n[Benchmark 3/8] DataLoader Packing & Batching Throughput...")
    sampler = DomainWeightedSampler(dataset, mode="domain_weighted", seed=42)
    loader = CausalDataLoader(dataset, batch_size=2, sequence_length=512, sampler=sampler, packing=True)

    # Warmup
    loader_iter = iter(loader)
    for _ in range(10):
        _ = next(loader_iter)

    # Timed repetitions
    dl_batches = 100
    dl_latencies_ms = []
    dl_throughputs_tok = []
    tokens_per_batch = 2 * 512

    for _ in range(dl_batches):
        t0 = time.perf_counter()
        _ = next(loader_iter)
        dur = time.perf_counter() - t0
        dl_latencies_ms.append(dur * 1000.0)
        dl_throughputs_tok.append(tokens_per_batch / dur)

    dl_lat_stats = compute_distribution_stats(dl_latencies_ms)
    dl_tok_stats = compute_distribution_stats(dl_throughputs_tok)
    batches_per_sec_median = 1000.0 / dl_lat_stats["median"]
    print(f"  Batch size: 2, Sequence length: 512 (1,024 tokens/batch)")
    print(f"  Batch latency:   median={dl_lat_stats['median']:.2f}ms, min={dl_lat_stats['min']:.2f}ms, max={dl_lat_stats['max']:.2f}ms, std={dl_lat_stats['std']:.2f}ms")
    print(f"  Throughput:      median={dl_tok_stats['median']:,.1f} tok/s ({batches_per_sec_median:.1f} batches/s)")
    results["dataloader"] = {
        "batch_size": 2,
        "sequence_length": 512,
        "tokens_per_batch": tokens_per_batch,
        "measured_batches": dl_batches,
        "batch_latency_ms": dl_lat_stats,
        "throughput_tokens_per_sec": dl_tok_stats,
        "median_batches_per_sec": round(batches_per_sec_median, 1),
    }

    # -------------------------------------------------------------------------
    # 4. Model Forward-Pass Latency (Synthetic Bounded Input)
    # -------------------------------------------------------------------------
    print("\n[Benchmark 4/8] Model Forward-Pass Latency (Synthetic Bounded)...")
    cfg = LoveModelConfig.from_yaml(str(configs_dir / "tiny.yaml"))
    device = torch.device(device_type)
    model = LoveForCausalLM(cfg).to(device)
    model.eval()

    test_input = torch.randint(0, cfg.vocab_size, (1, 512), dtype=torch.long, device=device)
    num_fwd_tokens = 512

    # A. Forward FP32
    if is_cuda:
        torch.cuda.synchronize()
    # Warmup
    with torch.no_grad():
        for _ in range(15):
            _ = model(test_input)
    if is_cuda:
        torch.cuda.synchronize()

    fwd_fp32_ms = []
    fwd_iters = 50
    with torch.no_grad():
        for _ in range(fwd_iters):
            if is_cuda:
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            _ = model(test_input)
            if is_cuda:
                torch.cuda.synchronize()
            dur = time.perf_counter() - t0
            fwd_fp32_ms.append(dur * 1000.0)

    fwd_fp32_stats = compute_distribution_stats(fwd_fp32_ms)
    fwd_fp32_tok_stats = compute_distribution_stats([(num_fwd_tokens / (ms / 1000.0)) for ms in fwd_fp32_ms])
    print(f"  FP32 Forward (batch=1, seq=512):")
    print(f"    Latency:       median={fwd_fp32_stats['median']:.2f}ms, mean={fwd_fp32_stats['mean']:.2f}ms, std={fwd_fp32_stats['std']:.2f}ms, min={fwd_fp32_stats['min']:.2f}ms, max={fwd_fp32_stats['max']:.2f}ms, p95={fwd_fp32_stats['p95']:.2f}ms")
    print(f"    Throughput:    median={fwd_fp32_tok_stats['median']:,.1f} tok/s")

    # B. Forward AMP FP16 (if CUDA available)
    fwd_amp_stats = None
    fwd_amp_tok_stats = None
    if is_cuda:
        with torch.no_grad():
            for _ in range(15):
                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    _ = model(test_input)
        torch.cuda.synchronize()

        fwd_amp_ms = []
        with torch.no_grad():
            for _ in range(fwd_iters):
                torch.cuda.synchronize()
                t0 = time.perf_counter()
                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    _ = model(test_input)
                torch.cuda.synchronize()
                dur = time.perf_counter() - t0
                fwd_amp_ms.append(dur * 1000.0)

        fwd_amp_stats = compute_distribution_stats(fwd_amp_ms)
        fwd_amp_tok_stats = compute_distribution_stats([(num_fwd_tokens / (ms / 1000.0)) for ms in fwd_amp_ms])
        print(f"  AMP FP16 Forward (batch=1, seq=512):")
        print(f"    Latency:       median={fwd_amp_stats['median']:.2f}ms, mean={fwd_amp_stats['mean']:.2f}ms, std={fwd_amp_stats['std']:.2f}ms, min={fwd_amp_stats['min']:.2f}ms, max={fwd_amp_stats['max']:.2f}ms, p95={fwd_amp_stats['p95']:.2f}ms")
        print(f"    Throughput:    median={fwd_amp_tok_stats['median']:,.1f} tok/s")

    results["forward_pass_synthetic"] = {
        "batch_size": 1,
        "sequence_length": 512,
        "tokens_processed": num_fwd_tokens,
        "repetitions": fwd_iters,
        "fp32_latency_ms": fwd_fp32_stats,
        "fp32_throughput_tokens_per_sec": fwd_fp32_tok_stats,
        "amp_fp16_latency_ms": fwd_amp_stats,
        "amp_fp16_throughput_tokens_per_sec": fwd_amp_tok_stats,
    }

    # -------------------------------------------------------------------------
    # 5. Full Training Step Latency (Forward + Backward + Optimizer) on Synthetic Data
    # -------------------------------------------------------------------------
    print("\n[Benchmark 5/8] Synthetic Full Training Step (Forward+Backward+AdamW)...")
    target = torch.randint(0, cfg.vocab_size, (1, 512), dtype=torch.long, device=device)
    train_step_iters = 30
    num_step_tokens = 512

    # A. Full Step FP32
    model.train()
    optimizer_fp32 = torch.optim.AdamW(model.parameters(), lr=1e-4)
    # Warmup
    for _ in range(10):
        optimizer_fp32.zero_grad()
        _, loss = model(test_input, targets=target)
        loss.backward()
        optimizer_fp32.step()
    if is_cuda:
        torch.cuda.synchronize()

    step_fp32_ms = []
    for _ in range(train_step_iters):
        if is_cuda:
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        optimizer_fp32.zero_grad()
        _, loss = model(test_input, targets=target)
        loss.backward()
        optimizer_fp32.step()
        if is_cuda:
            torch.cuda.synchronize()
        dur = time.perf_counter() - t0
        step_fp32_ms.append(dur * 1000.0)

    step_fp32_stats = compute_distribution_stats(step_fp32_ms)
    step_fp32_tok_stats = compute_distribution_stats([(num_step_tokens / (ms / 1000.0)) for ms in step_fp32_ms])
    print(f"  FP32 Full Step (batch=1, seq=512):")
    print(f"    Latency:       median={step_fp32_stats['median']:.2f}ms, mean={step_fp32_stats['mean']:.2f}ms, std={step_fp32_stats['std']:.2f}ms, min={step_fp32_stats['min']:.2f}ms, max={step_fp32_stats['max']:.2f}ms, p95={step_fp32_stats['p95']:.2f}ms")
    print(f"    Throughput:    median={step_fp32_tok_stats['median']:,.1f} tok/s")

    # B. Full Step AMP FP16 with GradScaler (if CUDA available)
    step_amp_stats = None
    step_amp_tok_stats = None
    if is_cuda:
        optimizer_amp = torch.optim.AdamW(model.parameters(), lr=1e-4)
        scaler = torch.amp.GradScaler(device="cuda")
        # Warmup
        for _ in range(10):
            optimizer_amp.zero_grad()
            with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                _, loss = model(test_input, targets=target)
            scaler.scale(loss).backward()
            scaler.step(optimizer_amp)
            scaler.update()
        torch.cuda.synchronize()

        step_amp_ms = []
        for _ in range(train_step_iters):
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            optimizer_amp.zero_grad()
            with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                _, loss = model(test_input, targets=target)
            scaler.scale(loss).backward()
            scaler.step(optimizer_amp)
            scaler.update()
            torch.cuda.synchronize()
            dur = time.perf_counter() - t0
            step_amp_ms.append(dur * 1000.0)

        step_amp_stats = compute_distribution_stats(step_amp_ms)
        step_amp_tok_stats = compute_distribution_stats([(num_step_tokens / (ms / 1000.0)) for ms in step_amp_ms])
        print(f"  AMP FP16 Full Step (batch=1, seq=512 with GradScaler):")
        print(f"    Latency:       median={step_amp_stats['median']:.2f}ms, mean={step_amp_stats['mean']:.2f}ms, std={step_amp_stats['std']:.2f}ms, min={step_amp_stats['min']:.2f}ms, max={step_amp_stats['max']:.2f}ms, p95={step_amp_stats['p95']:.2f}ms")
        print(f"    Throughput:    median={step_amp_tok_stats['median']:,.1f} tok/s")

    results["train_step_synthetic"] = {
        "batch_size": 1,
        "sequence_length": 512,
        "tokens_processed": num_step_tokens,
        "repetitions": train_step_iters,
        "fp32_step_latency_ms": step_fp32_stats,
        "fp32_step_throughput_tokens_per_sec": step_fp32_tok_stats,
        "amp_fp16_step_latency_ms": step_amp_stats,
        "amp_fp16_step_throughput_tokens_per_sec": step_amp_tok_stats,
    }

    # -------------------------------------------------------------------------
    # 6. Memory Telemetry (VRAM Allocated & Reserved, System RAM)
    # -------------------------------------------------------------------------
    print("\n[Benchmark 6/8] GTX 1650 VRAM & System Memory Telemetry...")
    if is_cuda:
        alloc_vram = torch.cuda.memory_allocated(0) / (1024 * 1024)
        peak_alloc_vram = torch.cuda.max_memory_allocated(0) / (1024 * 1024)
        res_vram = torch.cuda.memory_reserved(0) / (1024 * 1024)
        peak_res_vram = torch.cuda.max_memory_reserved(0) / (1024 * 1024)
        safe_headroom = 3500.0 - peak_res_vram
        print(f"  VRAM Allocated:        {alloc_vram:.2f} MB (Peak Allocated: {peak_alloc_vram:.2f} MB)")
        print(f"  VRAM Reserved:         {res_vram:.2f} MB (Peak Reserved:  {peak_res_vram:.2f} MB)")
        print(f"  GTX 1650 Capacity:     4,096.00 MB total | Safety Cap: 3,500.00 MB")
        print(f"  Safe Headroom:         {safe_headroom:.2f} MB headroom below safety cap")
        results["memory_telemetry"] = {
            "vram_allocated_mb": round(alloc_vram, 2),
            "vram_peak_allocated_mb": round(peak_alloc_vram, 2),
            "vram_reserved_mb": round(res_vram, 2),
            "vram_peak_reserved_mb": round(peak_res_vram, 2),
            "vram_total_capacity_mb": 4096.0,
            "vram_safety_cap_mb": 3500.0,
            "vram_safe_headroom_mb": round(safe_headroom, 2),
        }
    else:
        results["memory_telemetry"] = {
            "vram_allocated_mb": 0.0,
            "vram_peak_allocated_mb": 0.0,
            "vram_reserved_mb": 0.0,
            "vram_peak_reserved_mb": 0.0,
            "vram_total_capacity_mb": 0.0,
            "vram_safety_cap_mb": 3500.0,
            "vram_safe_headroom_mb": 3500.0,
        }

    process = psutil.Process()
    ram_mb = process.memory_info().rss / (1024 * 1024)
    print(f"  Process System RAM RSS: {ram_mb:.2f} MB")
    results["memory_telemetry"]["process_system_ram_rss_mb"] = round(ram_mb, 2)

    # -------------------------------------------------------------------------
    # 7. Checkpoint Write & SHA-256 Latency
    # -------------------------------------------------------------------------
    print("\n[Benchmark 7/8] Atomic Checkpoint Write & SHA-256 Latency...")
    ckpt_mgr = CheckpointManager(checkpoint_dir=base_dir / "checkpoints", max_to_keep=2)

    # Warmup write
    warmup_ckpt = ckpt_mgr.save_checkpoint(step=1, epoch=0, model=model, checkpoint_name="bm_warmup")
    if warmup_ckpt.exists():
        warmup_ckpt.unlink()
    if warmup_ckpt.with_suffix(".json").exists():
        warmup_ckpt.with_suffix(".json").unlink()

    # Repetitions
    ckpt_times_ms = []
    ckpt_sizes_mb = []
    ckpt_reps = 5
    for r in range(ckpt_reps):
        t0 = time.perf_counter()
        ckpt_path = ckpt_mgr.save_checkpoint(
            step=100 + r,
            epoch=0,
            model=model,
            optimizer=optimizer_fp32,
            checkpoint_name=f"benchmark_rep_{r}",
        )
        dur = time.perf_counter() - t0
        ckpt_times_ms.append(dur * 1000.0)
        ckpt_sizes_mb.append(ckpt_path.stat().st_size / (1024 * 1024))
        # Clean up immediately
        if ckpt_path.exists():
            ckpt_path.unlink()
        meta_p = ckpt_path.with_suffix(".json")
        if meta_p.exists():
            meta_p.unlink()

    ckpt_stats = compute_distribution_stats(ckpt_times_ms)
    avg_size_mb = float(np.mean(ckpt_sizes_mb))
    print(f"  Checkpoint Size: {avg_size_mb:.2f} MB")
    print(f"  Write Latency:   median={ckpt_stats['median']:.2f}ms, mean={ckpt_stats['mean']:.2f}ms, min={ckpt_stats['min']:.2f}ms, max={ckpt_stats['max']:.2f}ms, std={ckpt_stats['std']:.2f}ms")
    results["checkpoint_io"] = {
        "checkpoint_size_mb": round(avg_size_mb, 2),
        "write_latency_ms": ckpt_stats,
    }

    # -------------------------------------------------------------------------
    # 8. Formal Dry-Run Suite Execution (Synthetic vs Real Distinction)
    # -------------------------------------------------------------------------
    print("\n[Benchmark 8/8] Formal Dry-Run Suite (Strictly Isolated)...")
    safety = DeviceSafetyManager()
    trainer = Trainer(
        model=model,
        config=TrainingConfig(context_length=256, batch_size=1, device=device_type),
        safety_manager=safety,
        checkpoint_manager=ckpt_mgr,
    )

    cpu_smoke = trainer.run_cpu_synthetic_smoke_test(seq_len=128)
    print(f"  Mode A (CPU Synthetic Smoke Test):    {cpu_smoke['status']} (duration: {cpu_smoke['duration_seconds']:.3f}s)")
    results["dry_run_mode_a_synthetic"] = cpu_smoke

    cuda_smoke = trainer.run_cuda_synthetic_smoke_test(seq_len=256)
    print(f"  Mode B (CUDA Synthetic Smoke Test):   {cuda_smoke['status']} (duration: {cuda_smoke.get('duration_seconds', 0.0):.3f}s)")
    results["dry_run_mode_b_synthetic"] = cuda_smoke

    real_loader = CausalDataLoader(dataset, batch_size=1, sequence_length=256, packing=True)
    real_dry = trainer.run_bounded_real_dry_run(real_loader, num_batches=2)
    print(f"  Mode C (Real-Data Bounded Dry Run):   {real_dry['status']} (zero-mutation: {real_dry['zero_weight_mutation_verified']}, pretraining-blocked: {real_dry['real_pretraining_blocked']})")
    results["dry_run_mode_c_real_bounded"] = real_dry

    # Save audited results to experiments
    exp_dir = base_dir / "experiments"
    exp_dir.mkdir(parents=True, exist_ok=True)
    out_file = exp_dir / "nai_04_benchmarks.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"  AUDITED BENCHMARK SUITE COMPLETE — Results exported to {out_file}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_all_benchmarks()
