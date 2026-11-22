"""Synthetic Forward-Pass Benchmark for LOVE Native AI.

Implements Task 5:
- Loads native_ai/configs/tiny.yaml
- Initialises model with random weights
- Measures parameter counts
- Executes forward pass, logit validation, cross-entropy loss, backprop, gradient check, AdamW step
- Measures execution timings and GPU/CPU memory profiles on both CPU and CUDA (if available)
- Saves benchmark metrics to JSON and outputs human-readable summary
"""
import os
import sys
import time
import json
from pathlib import Path
import psutil
import torch
import torch.optim as optim

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from native_ai.model.love_model import LoveModelConfig, LoveForCausalLM


def run_benchmark_on_device(device_name: str, config_path: str, micro_batch_size: int = 1, warmup_steps: int = 2, benchmark_steps: int = 5):
    device = torch.device(device_name)
    print(f"\n========================================================")
    print(f"  RUNNING BENCHMARK ON DEVICE: {device_name.upper()}")
    print(f"========================================================")

    config = LoveModelConfig.from_yaml(config_path)

    # 1. Model Initialization Timing
    init_start = time.perf_counter()
    torch.manual_seed(42)
    model = LoveForCausalLM(config).to(device)
    if device.type == "cuda":
        torch.cuda.synchronize()
    init_time = time.perf_counter() - init_start

    # 2. Parameter Counting
    param_counts = model.count_parameters()
    print(f"Model: {config.model_name}")
    print(f"Total Parameters (with tied head): {param_counts['total_parameters']:,}")
    print(f"Unique Trainable Parameters: {param_counts['unique_trainable_parameters']:,}")
    print(f"Non-embedding Parameters: {param_counts['non_embedding_parameters']:,}")
    print(f"Embedding Parameters: {param_counts['embedding_parameters']:,}")
    print(f"Initialization Time: {init_time * 1000:.2f} ms")

    # Optimizer
    optimizer = optim.AdamW(model.parameters(), lr=1e-4)

    # Synthetic Data: Batch of micro_batch_size, context_length
    B = micro_batch_size
    T = config.context_length
    vocab_size = config.vocab_size

    # Prepare synthetic input_ids and targets
    torch.manual_seed(100)
    input_ids = torch.randint(0, vocab_size, (B, T), device=device)
    targets = torch.randint(0, vocab_size, (B, T), device=device)

    # Warmup
    model.train()
    for _ in range(warmup_steps):
        optimizer.zero_grad(set_to_none=True)
        logits, loss = model(input_ids, targets=targets)
        loss.backward()
        optimizer.step()
    if device.type == "cuda":
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()

    # Process Memory (CPU RAM)
    process = psutil.Process(os.getpid())
    cpu_ram_before_mb = process.memory_info().rss / (1024 * 1024)

    # Step Benchmarking
    forward_times = []
    backward_times = []
    step_times = []
    tokens_per_sec_list = []

    for step in range(benchmark_steps):
        # Forward pass
        optimizer.zero_grad(set_to_none=True)
        if device.type == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        logits, loss = model(input_ids, targets=targets)
        if device.type == "cuda":
            torch.cuda.synchronize()
        t1 = time.perf_counter()

        # Validation
        assert logits.shape == (B, T, vocab_size), f"Invalid logit shape {logits.shape}"
        assert torch.isfinite(loss), f"Loss is not finite: {loss.item()}"

        # Backward pass
        t2 = time.perf_counter()
        loss.backward()
        if device.type == "cuda":
            torch.cuda.synchronize()
        t3 = time.perf_counter()

        # Gradient validation
        for name, p in model.named_parameters():
            if p.requires_grad:
                assert p.grad is not None, f"Missing gradient for {name}"
                assert torch.isfinite(p.grad).all(), f"Non-finite gradient in {name}"

        # Optimizer step
        t4 = time.perf_counter()
        optimizer.step()
        if device.type == "cuda":
            torch.cuda.synchronize()
        t5 = time.perf_counter()

        fwd_dur = t1 - t0
        bwd_dur = t3 - t2
        opt_dur = t5 - t4
        total_step_dur = fwd_dur + bwd_dur + opt_dur
        tokens_processed = B * T
        tok_s = tokens_processed / total_step_dur

        forward_times.append(fwd_dur)
        backward_times.append(bwd_dur)
        step_times.append(opt_dur)
        tokens_per_sec_list.append(tok_s)

    cpu_ram_after_mb = process.memory_info().rss / (1024 * 1024)

    # Memory statistics
    gpu_peak_alloc_mb = 0.0
    gpu_peak_reserved_mb = 0.0
    if device.type == "cuda":
        gpu_peak_alloc_mb = torch.cuda.max_memory_allocated(device) / (1024 * 1024)
        gpu_peak_reserved_mb = torch.cuda.max_memory_reserved(device) / (1024 * 1024)

    avg_fwd_ms = (sum(forward_times) / len(forward_times)) * 1000
    avg_bwd_ms = (sum(backward_times) / len(backward_times)) * 1000
    avg_opt_ms = (sum(step_times) / len(step_times)) * 1000
    avg_total_ms = avg_fwd_ms + avg_bwd_ms + avg_opt_ms
    avg_tok_s = sum(tokens_per_sec_list) / len(tokens_per_sec_list)

    print(f"Forward Pass: {avg_fwd_ms:.2f} ms")
    print(f"Backward Pass: {avg_bwd_ms:.2f} ms")
    print(f"Optimizer Step: {avg_opt_ms:.2f} ms")
    print(f"Total Iteration Time: {avg_total_ms:.2f} ms")
    print(f"Throughput: {avg_tok_s:.1f} tokens/second")
    print(f"CPU Process RAM: {cpu_ram_after_mb:.2f} MB (Delta: +{cpu_ram_after_mb - cpu_ram_before_mb:.2f} MB)")
    if device.type == "cuda":
        print(f"Peak GPU Allocated Memory: {gpu_peak_alloc_mb:.2f} MB")
        print(f"Peak GPU Reserved Memory: {gpu_peak_reserved_mb:.2f} MB")
        total_vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
        print(f"Total GPU VRAM: {total_vram_mb:.1f} MB (VRAM utilization: {gpu_peak_reserved_mb / total_vram_mb * 100:.1f}%)")

    metrics = {
        "device": device_name,
        "config": config_path,
        "micro_batch_size": B,
        "context_length": T,
        "parameters": param_counts,
        "init_time_ms": init_time * 1000,
        "avg_forward_ms": avg_fwd_ms,
        "avg_backward_ms": avg_bwd_ms,
        "avg_optimizer_step_ms": avg_opt_ms,
        "avg_total_iteration_ms": avg_total_ms,
        "tokens_per_second": avg_tok_s,
        "cpu_ram_mb": cpu_ram_after_mb,
        "gpu_peak_allocated_mb": gpu_peak_alloc_mb,
        "gpu_peak_reserved_mb": gpu_peak_reserved_mb,
    }
    return metrics


def main():
    config_file = str(PROJECT_ROOT / "native_ai" / "configs" / "tiny.yaml")
    results = {}

    # CPU Benchmark
    results["cpu"] = run_benchmark_on_device("cpu", config_file)

    # CUDA Benchmark (if available)
    if torch.cuda.is_available():
        results["cuda"] = run_benchmark_on_device("cuda:0", config_file)
    else:
        print("\nCUDA not available. Skipping GPU benchmark.")

    # Save to experiments directory
    output_dir = PROJECT_ROOT / "native_ai" / "experiments"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "nai_01_synthetic_benchmark.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved synthetic benchmark results to: {out_file}")


if __name__ == "__main__":
    main()
