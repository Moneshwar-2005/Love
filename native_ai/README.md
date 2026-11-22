# LOVE Native AI

Independent, from-scratch language model development for the LOVE ecosystem.

## Architecture Principles
1. **Decoder-Only Transformer**: Modern architecture utilizing RMSNorm, Rotary Position Embeddings (RoPE), and SwiGLU activation.
2. **Zero External Pretraining**: Initialized with random weights and trained strictly locally without third-party base models.
3. **Hardware-Conscious Design**: Built to run and train within strict local compute limits (4 GB VRAM on NVIDIA GeForce GTX 1650).
4. **Complete Project Isolation**: Resides entirely within `native_ai/`, maintaining complete separation from existing LOVE backend, databases, and authentication systems.

## Directory Structure
- `configs/`: Model and training configuration files (YAML).
- `model/`: Modular PyTorch implementations of Transformer components.
- `tokenizer/`: Custom tokenizer implementation and vocabulary storage (NAI-02).
- `datasets/`: Dataset curation pipeline, raw corpora, and pre-tokenized manifests.
- `training/`: Training engine, loop, optimizer, and learning rate schedulers.
- `evaluation/`: Benchmark harness, loss evaluation, and perplexity tracking.
- `inference/`: Autoregressive generation and sampling engine.
- `checkpoints/`: Local model checkpoints and weight archives.
- `experiments/`: Experiment logs, hyperparameter manifests, and metrics.
- `tests/`: Automated test suite for architecture correctness and numerical stability.
- `documentation/`: Architecture audits, hardware benchmarks, and phase reports.
- `scripts/`: Diagnostic, benchmarking, and helper utilities.
