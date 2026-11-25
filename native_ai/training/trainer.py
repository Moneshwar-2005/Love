"""Local Pretraining Engine and Validation Loop for LOVE Native AI.

Implements Section 6, 7, 8, 11, 12 (NAI-04):
- Forward pass, next-token cross-entropy loss, backpropagation.
- AdamW optimizer, warmup + cosine learning rate scheduling.
- Gradient accumulation and gradient clipping.
- Hardware safeguards for NVIDIA GTX 1650 4GB (VRAM telemetry, threshold protection).
- Mixed-precision execution (FP16 CUDA with GradScaler, FP32 CPU).
- Finite loss verification (NaN/Inf detection).
- Isolated validation engine with exact cross-entropy loss and perplexity.
- Formal dry-run verification modes:
  - Mode A: CPU synthetic smoke test (forward, loss, gradient, 1 optimizer step, checkpoint save/restore).
  - Mode B: CUDA synthetic smoke test (FP16 AMP, VRAM telemetry, gradient accum, checkpoint).
  - Mode C: Real-data bounded dry run (forward pass on real cache, zero weight updates, zero optimizer steps).
"""
import math
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, Iterator, List
from pathlib import Path

import torch
import torch.nn as nn
from torch.optim import AdamW

from native_ai.model.love_model import LoveForCausalLM, LoveModelConfig
from native_ai.training.device_safety import DeviceSafetyManager, VRAMLimitExceededError
from native_ai.training.checkpoint_manager import CheckpointManager
from native_ai.training.experiment_tracker import ExperimentTracker


@dataclass
class TrainingConfig:
    """Hyperparameters and configuration for local pretraining engine."""
    learning_rate: float = 3e-4
    min_learning_rate: float = 3e-5
    weight_decay: float = 0.1
    beta1: float = 0.9
    beta2: float = 0.95
    eps: float = 1e-8
    max_grad_norm: float = 1.0
    warmup_steps: int = 50
    max_steps: int = 1000
    gradient_accumulation_steps: int = 2
    batch_size: int = 1
    context_length: int = 512
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    use_amp: bool = True
    eval_interval: int = 100
    eval_steps: int = 20
    checkpoint_interval: int = 250
    seed: int = 42


class CosineWarmupScheduler:
    """Linear warmup followed by cosine learning rate decay."""

    def __init__(
        self,
        optimizer: torch.optim.Optimizer,
        warmup_steps: int,
        max_steps: int,
        base_lr: float,
        min_lr: float,
    ):
        self.optimizer = optimizer
        self.warmup_steps = max(1, warmup_steps)
        self.max_steps = max(self.warmup_steps + 1, max_steps)
        self.base_lr = base_lr
        self.min_lr = min_lr
        self.current_step = 0
        self.step(0)

    def step(self, step: Optional[int] = None) -> float:
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1

        if self.current_step < self.warmup_steps:
            # Linear warmup
            lr = self.base_lr * (self.current_step / self.warmup_steps)
        elif self.current_step > self.max_steps:
            lr = self.min_lr
        else:
            # Cosine decay
            progress = (self.current_step - self.warmup_steps) / (self.max_steps - self.warmup_steps)
            lr = self.min_lr + 0.5 * (self.base_lr - self.min_lr) * (1.0 + math.cos(math.pi * progress))

        for param_group in self.optimizer.param_groups:
            param_group["lr"] = lr
        return lr

    def get_lr(self) -> float:
        return self.optimizer.param_groups[0]["lr"]

    def state_dict(self) -> Dict[str, Any]:
        return {
            "current_step": self.current_step,
            "warmup_steps": self.warmup_steps,
            "max_steps": self.max_steps,
            "base_lr": self.base_lr,
            "min_lr": self.min_lr,
        }

    def load_state_dict(self, state: Dict[str, Any]) -> None:
        self.current_step = state["current_step"]
        self.warmup_steps = state["warmup_steps"]
        self.max_steps = state["max_steps"]
        self.base_lr = state["base_lr"]
        self.min_lr = state["min_lr"]
        self.step(self.current_step)


class Trainer:
    """Local modular training engine with GTX 1650 safeguards and strict dry-run enforcement."""

    def __init__(
        self,
        model: LoveForCausalLM,
        config: TrainingConfig,
        safety_manager: Optional[DeviceSafetyManager] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        tracker: Optional[ExperimentTracker] = None,
    ):
        self.config = config
        self.safety = safety_manager or DeviceSafetyManager(requested_device=config.device)
        self.device = self.safety.device
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.tracker = tracker

        # Move model to target device
        self.model = model.to(self.device)

        # Configure optimizer: separate weight decay for 2D weight matrices vs biases/RMSNorm
        decay_params = []
        no_decay_params = []
        for name, param in self.model.named_parameters():
            if not param.requires_grad:
                continue
            if param.ndim >= 2:
                decay_params.append(param)
            else:
                no_decay_params.append(param)

        optim_groups = [
            {"params": decay_params, "weight_decay": config.weight_decay},
            {"params": no_decay_params, "weight_decay": 0.0},
        ]
        self.optimizer = AdamW(
            optim_groups,
            lr=config.learning_rate,
            betas=(config.beta1, config.beta2),
            eps=config.eps,
        )

        # Learning rate scheduler
        self.scheduler = CosineWarmupScheduler(
            optimizer=self.optimizer,
            warmup_steps=config.warmup_steps,
            max_steps=config.max_steps,
            base_lr=config.learning_rate,
            min_lr=config.min_learning_rate,
        )

        # AMP GradScaler
        self.use_amp = config.use_amp and self.safety.is_cuda
        self.scaler = self.safety.get_grad_scaler(enabled=self.use_amp)

        self.global_step = 0
        self.epoch = 0

    def train_step(
        self,
        input_ids: torch.Tensor,
        targets: torch.Tensor,
        accum_step: int,
        total_accum_steps: int,
    ) -> Dict[str, Any]:
        """
        Executes one forward and backward micro-step with gradient accumulation.
        Performs optimizer step and gradient clipping when accum_step == total_accum_steps - 1.
        """
        self.model.train()
        input_ids = input_ids.to(self.device)
        targets = targets.to(self.device)

        # VRAM Safety Check
        self.safety.check_vram_safety()

        # Forward pass with mixed precision context
        with self.safety.get_autocast_context(enabled=self.use_amp):
            logits, loss = self.model(input_ids, targets=targets)
            scaled_loss = loss / total_accum_steps

        # Finite Loss Assertion
        self.safety.verify_finite_loss(loss, step=self.global_step)

        # Backward pass
        if self.scaler is not None:
            self.scaler.scale(scaled_loss).backward()
        else:
            scaled_loss.backward()

        grad_norm = 0.0
        step_completed = False

        # Optimizer step upon full gradient accumulation
        if (accum_step + 1) % total_accum_steps == 0:
            if self.scaler is not None:
                self.scaler.unscale_(self.optimizer)
                grad_norm = torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), max_norm=self.config.max_grad_norm
                ).item()
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                grad_norm = torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), max_norm=self.config.max_grad_norm
                ).item()
                self.optimizer.step()

            self.optimizer.zero_grad(set_to_none=True)
            current_lr = self.scheduler.step()
            self.global_step += 1
            step_completed = True
        else:
            current_lr = self.scheduler.get_lr()

        vram = self.safety.get_vram_telemetry()

        return {
            "loss": loss.item(),
            "grad_norm": grad_norm,
            "learning_rate": current_lr,
            "step_completed": step_completed,
            "global_step": self.global_step,
            "vram_allocated_mb": vram["allocated_mb"],
            "vram_peak_mb": vram["peak_allocated_mb"],
        }

    def evaluate_validation(
        self,
        val_loader: Iterator[Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]],
        max_eval_batches: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Evaluates model on validation data without updating weights or optimizer states.
        Uses torch.no_grad() and computes exact average cross-entropy loss and perplexity.
        """
        self.model.eval()
        total_loss = 0.0
        total_tokens = 0
        batches_evaluated = 0

        with torch.no_grad():
            for i, (input_ids, targets, _) in enumerate(val_loader):
                if max_eval_batches is not None and i >= max_eval_batches:
                    break

                input_ids = input_ids.to(self.device)
                targets = targets.to(self.device)

                with self.safety.get_autocast_context(enabled=self.use_amp):
                    logits, loss = self.model(input_ids, targets=targets)

                batch_tokens = targets.numel()
                total_loss += loss.item() * batch_tokens
                total_tokens += batch_tokens
                batches_evaluated += 1

        avg_loss = total_loss / total_tokens if total_tokens > 0 else 0.0
        perplexity = math.exp(min(avg_loss, 20.0))  # Cap exponent to prevent overflow

        return {
            "val_loss": round(avg_loss, 4),
            "perplexity": round(perplexity, 4),
            "val_tokens_evaluated": total_tokens,
            "batches_evaluated": batches_evaluated,
        }

    # =========================================================================
    # DRY-RUN VERIFICATION MODES (NO ACTUAL FULL PRETRAINING)
    # =========================================================================

    def run_cpu_synthetic_smoke_test(self, seq_len: int = 128) -> Dict[str, Any]:
        """
        Mode A: CPU Synthetic Smoke Test.
        Runs synthetic forward pass, loss calculation, gradients, and 1 optimizer step.
        Saves and reloads checkpoint, asserting deterministic output equivalence.
        """
        t0 = time.perf_counter()
        cpu_safety = DeviceSafetyManager(requested_device="cpu")
        cpu_model = LoveForCausalLM(self.model.config).to("cpu")

        cpu_trainer = Trainer(
            model=cpu_model,
            config=TrainingConfig(
                device="cpu",
                use_amp=False,
                gradient_accumulation_steps=1,
                context_length=seq_len,
            ),
            safety_manager=cpu_safety,
            checkpoint_manager=self.checkpoint_manager,
        )

        # Synthetic batch
        synth_inputs = torch.randint(0, cpu_model.config.vocab_size, (1, seq_len), dtype=torch.long)
        synth_targets = torch.randint(0, cpu_model.config.vocab_size, (1, seq_len), dtype=torch.long)

        # Step
        res = cpu_trainer.train_step(synth_inputs, synth_targets, accum_step=0, total_accum_steps=1)
        assert res["step_completed"] is True
        assert math.isfinite(res["loss"])

        # Save Checkpoint
        ckpt_path = self.checkpoint_manager.save_checkpoint(
            step=1,
            epoch=0,
            model=cpu_trainer.model,
            optimizer=cpu_trainer.optimizer,
            scheduler=cpu_trainer.scheduler,
            checkpoint_name="cpu_smoke_test",
        )

        # Reload into fresh model and verify output equivalence
        model_reload = LoveForCausalLM(self.model.config).to("cpu")
        self.checkpoint_manager.load_checkpoint(ckpt_path, model_reload)

        with torch.no_grad():
            out_orig, _ = cpu_trainer.model(synth_inputs)
            out_reloaded, _ = model_reload(synth_inputs)

        diff = (out_orig - out_reloaded).abs().max().item()
        assert diff == 0.0, f"Reloaded checkpoint outputs diverge: max diff {diff}"

        # Clean up temporary test checkpoint
        if ckpt_path.exists():
            ckpt_path.unlink()
        meta_p = ckpt_path.with_suffix(".json")
        if meta_p.exists():
            meta_p.unlink()

        duration = time.perf_counter() - t0
        return {
            "mode": "CPU_SYNTHETIC_SMOKE_TEST",
            "status": "PASSED",
            "duration_seconds": round(duration, 4),
            "loss": res["loss"],
            "gradient_norm": res["grad_norm"],
            "deterministic_diff": diff,
        }

    def run_cuda_synthetic_smoke_test(self, seq_len: int = 256) -> Dict[str, Any]:
        """
        Mode B: CUDA Synthetic Smoke Test.
        Tests FP16 mixed precision, GradScaler, gradient accumulation, and VRAM telemetry on GTX 1650.
        """
        if not torch.cuda.is_available():
            return {
                "mode": "CUDA_SYNTHETIC_SMOKE_TEST",
                "status": "SKIPPED",
                "reason": "CUDA is not available on this host.",
            }

        t0 = time.perf_counter()
        self.safety.clean_vram()
        vram_before = self.safety.get_vram_telemetry()

        cuda_config = TrainingConfig(
            device="cuda",
            use_amp=True,
            gradient_accumulation_steps=2,
            context_length=seq_len,
        )
        cuda_trainer = Trainer(
            model=self.model,
            config=cuda_config,
            safety_manager=self.safety,
            checkpoint_manager=self.checkpoint_manager,
        )

        synth_inputs = torch.randint(0, self.model.config.vocab_size, (1, seq_len), dtype=torch.long)
        synth_targets = torch.randint(0, self.model.config.vocab_size, (1, seq_len), dtype=torch.long)

        # Micro-step 0 (gradient accumulation)
        step0 = cuda_trainer.train_step(synth_inputs, synth_targets, accum_step=0, total_accum_steps=2)
        assert step0["step_completed"] is False

        # Micro-step 1 (optimizer step + scaler update)
        step1 = cuda_trainer.train_step(synth_inputs, synth_targets, accum_step=1, total_accum_steps=2)
        assert step1["step_completed"] is True
        assert math.isfinite(step1["loss"])

        vram_after = self.safety.get_vram_telemetry()

        # Save test checkpoint
        ckpt_path = self.checkpoint_manager.save_checkpoint(
            step=1,
            epoch=0,
            model=cuda_trainer.model,
            optimizer=cuda_trainer.optimizer,
            scheduler=cuda_trainer.scheduler,
            scaler=cuda_trainer.scaler,
            checkpoint_name="cuda_smoke_test",
        )
        # Verify load back
        cuda_trainer.checkpoint_manager.load_checkpoint(ckpt_path, cuda_trainer.model, device=torch.device("cuda"))

        # Clean up temporary test checkpoint
        if ckpt_path.exists():
            ckpt_path.unlink()
        meta_p = ckpt_path.with_suffix(".json")
        if meta_p.exists():
            meta_p.unlink()

        self.safety.clean_vram()
        duration = time.perf_counter() - t0

        return {
            "mode": "CUDA_SYNTHETIC_SMOKE_TEST",
            "status": "PASSED",
            "duration_seconds": round(duration, 4),
            "loss": step1["loss"],
            "gradient_norm": step1["grad_norm"],
            "vram_initial_mb": vram_before["allocated_mb"],
            "vram_peak_mb": vram_after["peak_allocated_mb"],
            "vram_safe_headroom_mb": 3500.0 - vram_after["peak_allocated_mb"],
            "amp_scaler_scale": cuda_trainer.scaler.get_scale() if cuda_trainer.scaler else None,
        }

    def run_bounded_real_dry_run(
        self,
        data_loader: Iterator[Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]],
        num_batches: int = 2,
    ) -> Dict[str, Any]:
        """
        Mode C: Real Dataset Pipeline Bounded Dry Run.
        Loads bounded sample from actual training cache.
        Runs forward pass and loss computation.
        DOES NOT call optimizer.step().
        DOES NOT update weights.
        DOES NOT start an epoch or consume full dataset.
        Proves weights remain bitwise identical before and after.
        """
        t0 = time.perf_counter()
        self.model.eval()

        # Snapshot weights before forward pass
        weights_before = {name: p.clone().detach() for name, p in self.model.named_parameters()}

        losses = []
        batch_shapes = []

        with torch.no_grad():
            for i, (input_ids, targets, _) in enumerate(data_loader):
                if i >= num_batches:
                    break
                input_ids = input_ids.to(self.device)
                targets = targets.to(self.device)

                with self.safety.get_autocast_context(enabled=self.use_amp):
                    logits, loss = self.model(input_ids, targets=targets)

                self.safety.verify_finite_loss(loss)
                losses.append(loss.item())
                batch_shapes.append(list(input_ids.shape))

        # Verify zero weight mutation
        weights_after = {name: p.clone().detach() for name, p in self.model.named_parameters()}
        for name in weights_before:
            diff = (weights_before[name] - weights_after[name]).abs().max().item()
            assert diff == 0.0, f"Weight mutation detected during bounded dry run in '{name}'"

        duration = time.perf_counter() - t0
        vram = self.safety.get_vram_telemetry()

        return {
            "mode": "REAL_DATA_BOUNDED_DRY_RUN",
            "status": "PASSED",
            "duration_seconds": round(duration, 4),
            "batches_evaluated": len(losses),
            "batch_shapes": batch_shapes,
            "measured_losses": losses,
            "average_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
            "zero_weight_mutation_verified": True,
            "optimizer_steps_executed": 0,
            "real_pretraining_blocked": True,
            "vram_peak_mb": vram["peak_allocated_mb"],
        }
