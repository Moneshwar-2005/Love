# Tokenizer Subsystem

This directory contains the custom tokenizer implementation for LOVE Native AI.
Scheduled for implementation in Phase NAI-02.

- Target Vocabulary: 8,192 tokens
- Character coverage: ASCII and standard English text
- Algorithm: Custom BPE (Byte-Pair Encoding) trained from scratch on raw LOVE training corpora
- No external pretrained tokenizer models (e.g. TikToken, HuggingFace AutoTokenizer) will be used.
