# LOVE Models Directory

## Storage Purpose
This directory stores AI model weights, tokenizers, and quantized formats used locally by the LOVE assistant.

### Planned Contents (Future Phases):
- Local LLM GGUF format weights for llama.cpp integration.
- Embedding model weights for persistent vector memory retrieval.
- Wake-word model files for "Hey Love" on-device acoustic detection.
- TTS voice model checkpoints for the Indian English female voice profile.

*Note: Large binary weights (`*.pt`, `*.gguf`, `*.bin`, `*.safetensors`) are ignored by `.gitignore` and managed via external download scripts in future development phases.*
