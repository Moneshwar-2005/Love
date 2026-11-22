# Training Subsystem

Implements native training loops, optimizers, learning rate scheduling, gradient accumulation,
and checkpoint management.

Scheduled for initial activation in Phase NAI-03.
Constraints:
- Runs strictly on local hardware (GTX 1650 4GB VRAM / i7-7700 CPU).
- No cloud GPU training.
- Gradient accumulation & mixed precision memory optimization.
