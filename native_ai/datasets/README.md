# Datasets Subsystem

Manages raw text corpora, preprocessing pipelines, and tokenized training manifests.

## Directories
- `raw/`: Unprocessed English text corpora.
- `processed/`: Cleaned, deduplicated, and filtered plain text documents.
- `manifests/`: Binary or memory-mapped token arrays ready for pretraining streaming.

## Isolation Rules
- Datasets must be curated and verified locally.
- Large data files and raw archives are git-ignored.
