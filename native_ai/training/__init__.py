"""Training subsystem for LOVE Native AI.

Implements native PyTorch training loop, optimization, learning rate schedules,
and checkpointing for NAI-04.
"""
from native_ai.training.trainer import Trainer, TrainingConfig, CosineWarmupScheduler
from native_ai.training.device_safety import DeviceSafetyManager, VRAMLimitExceededError
from native_ai.training.checkpoint_manager import CheckpointManager, CheckpointCorruptedError, DiskHeadroomError
from native_ai.training.experiment_tracker import ExperimentTracker
from native_ai.training.reproducibility import set_seed, generate_experiment_id, capture_hardware_metadata

__all__ = [
    "Trainer",
    "TrainingConfig",
    "CosineWarmupScheduler",
    "DeviceSafetyManager",
    "VRAMLimitExceededError",
    "CheckpointManager",
    "CheckpointCorruptedError",
    "DiskHeadroomError",
    "ExperimentTracker",
    "set_seed",
    "generate_experiment_id",
    "capture_hardware_metadata",
]
