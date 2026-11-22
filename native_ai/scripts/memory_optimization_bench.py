"""Memory Optimization Research Benchmark for LOVE Native AI.

Implements Task 6:
Systematically evaluates and benchmarks:
1. FP32 baseline (CPU and CUDA)
2. FP16 Automatic Mixed Precision (torch.cuda.amp.autocast)
3. Activation Checkpointing (gradient checkpointing)
4. Context length scaling (128, 256, 512, 1024)
5. Micro-batch size scaling (1, 2, 4)
6. Gradient accumulation simulation
7. CPU fallback feasibility

Records peak GPU memory, execution speed, and numerical stability.
"""
import os
import sys
import time
import json
from pathlib import Path
import psutil
import torch
import torch.optim as optim
from torch.amp import autocast

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from native_ai.model.love_model import LoveModelConfig, LoveForCausalLM


def benchmark_configuration(
    name: str,
    device_name: str,
    precision: str = "fp32",
    use_checkpointing: bool = False,
    micro_batch_size: int = 1,
    context_length: int = 512,
    gradient_accumulation_steps: int = 1,
    num_steps: int = 4,
):
    device = torch.device(device_name)
    config = LoveModelConfig.from_yaml(str(PROJECT_ROOT / "native_ai" / "configs" / "tiny.yaml"))
    config.context_length = context_length
    config.use_activation_checkpointing = use_checkpointing

    torch.manual_seed(42)
    model = LoveForCausalLM(config).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=1e-4)
    scaler = torch.amp.GradScaler("cuda", enabled=(precision == "fp16" and device.type == "cuda"))

    # Reset peak stats
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()

    input_ids = torch.randint(0, config.vocab_size, (micro_batch_size, context_length), device=device)
    targets = torch.randint(0, config.vocab_size, (micro_batch_size, context_length), device=device)

    model.train()
    durations = []
    oom = False

    try:
        for step in range(num_steps):
            optimizer.zero_grad(set_to_none=True)
            if device.type == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()

            # Gradient accumulation loop
            for micro_step in range(gradient_accumulation_steps):
                if precision == "fp16" and device.type == "cuda":
                    with autocast(device_type="cuda", dtype=torch.float16):
                        logits, loss = model(input_ids, targets=targets)
                        loss = loss / gradient_accumulation_steps
                    scaler.scale(loss).backward()
                else:
                    logits, loss = model(input_ids, targets=targets)
                    loss = loss / gradient_accumulation_steps
                    loss.backward()

            if precision == "fp16" and device.type == "cuda":
                scaler.step(optimizer)
                scaler.update()
            else:
                optimizer.step()

            if device.type == "cuda":
                torch.cuda.synchronize()
            t1 = time.perf_counter()
            durations.append(t1 - t0)

    except torch.cuda.OutOfMemoryError:
        oom = True
        torch.cuda.empty_cache()

    if oom:
        print(f"[{name}] Result: OUT OF MEMORY (OOM)")
        return {
            "name": name,
            "status": "OOM",
            "device": device_name,
            "precision": precision,
            "checkpointing": use_checkpointing,
            "batch_size": micro_batch_size,
            "context_length": context_length,
            "grad_accum": gradient_accumulation_steps,
        }

    avg_step_ms = (sum(durations) / len(durations)) * 1000
    tokens_per_sec = (micro_batch_size * context_length * gradient_accumulation_steps) / (avg_step_ms / 1000)

    gpu_alloc_mb = torch.cuda.max_memory_allocated(device) / (1024 * 1024) if device.type == "cuda" else 0.0
    gpu_res_mb = torch.cuda.max_memory_reserved(device) / (1024 * 1024) if device.type == "cuda" else 0.0

    print(f"[{name:35s}] Step: {avg_step_ms:6.2f} ms | Tok/s: {tokens_per_sec:7.1f} | Peak Alloc: {gpu_alloc_mb:6.1f} MB | Peak Res: {gpu_res_mb:6.1f} MB")

    return {
        "name": name,
        "status": "SUCCESS",
        "device": device_name,
        "precision": precision,
        "checkpointing": use_checkpointing,
        "micro_batch_size": micro_batch_size,
        "context_length": context_length,
        "grad_accum_steps": gradient_accumulation_steps,
        "avg_step_ms": avg_step_ms,
        "tokens_per_sec": tokens_per_sec,
        "peak_allocated_mb": gpu_alloc_mb,
        "peak_reserved_mb": gpu_res_mb,
    }


def main():
    print("=" * 90)
    print("LOVE NATIVE AI: MEMORY & COMPUTATIONAL OPTIMIZATION MATRIX")
    print("=" * 90)

    benchmarks = []
    cuda_avail = torch.cuda.is_available()

    # 1. FP32 Baseline vs FP16 on CUDA (Micro-batch 1, Context 512)
    if cuda_avail:
        benchmarks.append(benchmark_configuration("CUDA_FP32_Baseline", "cuda:0", precision="fp32"))
        benchmarks.append(benchmark_configuration("CUDA_FP16_MixedPrecision", "cuda:0", precision="fp16"))
        benchmarks.append(benchmark_configuration("CUDA_FP32_ActivationCheckpointing", "cuda:0", precision="fp32", use_checkpointing=True))
        benchmarks.append(benchmark_configuration("CUDA_FP16_ActCheckpointing", "cuda:0", precision="fp16", use_checkpointing=True))

        # Context Scaling
        benchmarks.append(benchmark_configuration("CUDA_FP32_Ctx128", "cuda:0", context_length=128))
        benchmarks.append(benchmark_configuration("CUDA_FP32_Ctx256", "cuda:0", context_length=256))
        benchmarks.append(benchmark_configuration("CUDA_FP32_Ctx512", "cuda:0", context_length=512))
        benchmarks.append(benchmark_configuration("CUDA_FP32_Ctx1024", "cuda:0", context_length=1024))

        # Batch Size Scaling
        benchmarks.append(benchmark_configuration("CUDA_FP32_Batch1", "cuda:0", micro_batch_size=1))
        benchmarks.append(benchmark_configuration("CUDA_FP32_Batch2", "cuda:0", micro_batch_size=2))
        benchmarks.append(benchmark_configuration("CUDA_FP32_Batch4", "cuda:0", micro_batch_size=4))

        # Gradient Accumulation (Simulating Effective Batch 4 via Micro-batch 1 x 4 steps)
        benchmarks.append(benchmark_configuration("CUDA_FP32_GradAccum4", "cuda:0", micro_batch_size=1, gradient_accumulation_steps=4))

    # CPU Benchmarks
    benchmarks.append(benchmark_configuration("CPU_FP32_Baseline_Batch1", "cpu", precision="fp32", micro_batch_size=1, context_length=512))
    benchmarks.append(benchmark_configuration("CPU_FP32_Ctx128", "cpu", precision="fp32", micro_batch_size=1, context_length=128))

    # Save to experiments
    output_dir = PROJECT_ROOT / "native_ai" / "experiments"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "nai_01_memory_optimization_bench.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmarks, f, indent=2)
    print(f"\nOptimization matrix results saved to: {out_file}")


if __name__ == "__main__":
    main()
