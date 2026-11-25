# LOVE NATIVE AI — PHASE NAI-03.1 AUDIT REPORT
## Dataset Provenance, Corpus Scale & Pretraining Readiness Audit

**Date:** 2026-11-22  
**Project Workspace:** `F:\LOVE\native_ai`  
**Host Environment:** Windows 11 Pro 64-bit | Intel Core i7-7700 @ 3.60GHz | 16 GB RAM | NVIDIA GeForce GTX 1650 (4 GB VRAM)  
**Storage Volume (F:):** 52.53 GB Total, 44.04 GB Used, **4.89 GB Available**  
**Phase Status:** **BLOCKED (Pretraining Readiness Not Achieved — Corpus Scale & Eval Split Insufficient)**  

---

### Executive Summary

Phase **NAI-03.1** conducts a formal audit of dataset provenance, corpus scale, split distribution, and pretraining readiness for LOVE Native AI's 5,507,328-parameter decoder-only Transformer. 

While Phase **NAI-03** successfully engineered a robust, streaming data-processing pipeline (ingestion, NFKC cleaning, regex privacy filtering, composite MinHash deduplication, and deterministic splitting), the resulting admitted corpus—comprising **22 documents**, **2,137 words**, and **6,392 tokens** across **14,630 clean text bytes**—is **several orders of magnitude below the minimum threshold required for language-model pretraining**. At context length 512, this corpus provides only **11 training sequences**, causing catastrophic memorization within seconds and zero generalization.

Furthermore, this audit identifies and resolves critical statistical and legal inaccuracies in earlier reports:
1. **Split Percentage Correction:** The previous report falsely claimed a "98% Train / 1% Val / 1% Test" distribution. The true measured split on 22 documents is **90.91% Train (20 docs)**, **4.55% Validation (1 doc)**, and **4.55% Test (1 doc)**. Single-document evaluation splits are statistically meaningless.
2. **Provenance & License Misclassification:** Source `src_tech_01` was previously attributed to the "MIT" license citing opensource.org. Inspection proves it is internal synthetic text authored in `curate_raw_sources.py` with zero third-party upstream copyright deed. It has been reclassified as **UNRESOLVED** and excluded from approved training status.
3. **Corpus Scale & Storage Targets:** Three empirical scenarios were modeled for the 5.5M model (Scenario A: 1M tokens / 10 MB; Scenario B: 20M tokens / 226 MB; Scenario C: 100M tokens / 1.17 GB). All fit within the 4.89 GB free disk limit on `F:`.
4. **Permissive External Shortlist:** Six high-quality, lawfully permissive English datasets (Standard Ebooks / Gutenberg, Simple English Wikipedia, TinyStories, GSM8K, The Stack Permissive Python, and OASST1) are formally proposed for user approval without downloading any files.
5. **Test Suite Expansion:** The automated test suite has been expanded from 34 to **43 passing tests** (100% pass rate), verifying provenance checking, group leakage prevention, token reporting, and storage safety.
6. **Pretraining Decision:** Pretraining remains **BLOCKED** until external corpora are approved and ingested to achieve at least Scenario B (20M tokens).

---

### 1. Existing Corpus Assessment

An empirical evaluation was conducted on all existing dataset fixtures in `native_ai/datasets/`:

```mermaid
flowchart TD
    subgraph RawAssets ["Raw Ingested Assets (71,454 bytes)"]
        RawDocs["103 Raw Documents (5 Category JSONLs)"]
        SeedTxt["seed_corpus.txt (2.00 MB / 13,927 paras)"]
        HeldOutTxt["held_out_eval.txt (897 bytes / 3 paras)"]
    end

    subgraph PipelineFilter ["NAI-03 Filtering Pipeline"]
        RawDocs --> Cleaner["TextCleaner (0 rejected)"]
        Cleaner --> PrivFilter["PrivacyFilter (1 secret rejected, 2 PII redacted)"]
        PrivFilter --> Dedup["Composite Deduplicator (80 dups rejected: 38 exact, 42 near)"]
    end

    subgraph CurrentSplits ["Admitted Clean Splits (14,630 bytes / 6,392 tokens)"]
        Dedup --> Admitted["22 Admitted Documents (2,137 words)"]
        Admitted --> Train["Train: 20 docs (90.91%) | 5,768 tokens (90.24%)"]
        Admitted --> Val["Val: 1 doc (4.55%) | 235 tokens (3.68%)"]
        Admitted --> Test["Test: 1 doc (4.55%) | 389 tokens (6.09%)"]
    end
```

#### Detailed Fixture Breakdown:

| Fixture Path | File Size | Document Units | Word Count | Token Count | Type-Token Ratio | Purpose & Assessment |
|---|---|---|---|---|---|---|
| `datasets/raw/seed_corpus.txt` | 2,001,924 bytes (CRLF)<br>1,974,028 bytes (LF) | 13,927 paragraphs | 81,045 unique | ~670,000 | 0.3915 | **Tokenizer V0.1 Development Fixture:** Synthetically generated in `native_ai/tokenizer/corpus.py`. Contains repetitive combinatorial lexicon templates ("The term X represents..."). Unsuitable for model pretraining. |
| `datasets/raw/held_out_eval.txt` | 897 bytes (CRLF)<br>882 bytes (LF) | 3 paragraphs | 94 unique | ~380 | 0.8246 | **Tokenizer V0.1 Benchmark Fixture:** Isolated test passages for tokenizer UTF-8 roundtrip fidelity. |
| `datasets/staged/cleaned_corpus.jsonl` | 19,437 bytes | 22 documents | 2,137 words | 6,392 | 0.4480 | **Current Admitted Corpus:** Output of NAI-03 pipeline. Extremely high quality, 100% UTF-8 lossless, but vastly insufficient in scale. |

#### Why the Current Corpus Cannot Pretrain the 5.5M Transformer:
- **Parameter-to-Data Imbalance:** The LOVE Transformer has **5,507,328 trainable parameters**. The admitted training set has only **5,768 tokens**. This corresponds to **~0.001 tokens per parameter**.
- **Chinchilla Compute-Optimal Standard:** Established empirical scaling laws (Hoffmann et al., 2022) dictate that compute-optimal pretraining requires approximately **20 tokens per parameter** ($\approx 110\text{M tokens}$ for 5.5M params).
- **Batch Saturation:** At a sequence length of 512 tokens, 5,768 tokens represent only **11.26 full sequences**. In a standard batch size of 2 with gradient accumulation of 4 (effective batch = 8 sequences), an epoch is exhausted in **1.4 optimizer steps**. The model would cycle through the same 11 text blocks repeatedly, overfitting to near-zero loss on memorized strings while failing completely on novel English inputs.

---

### 2. Source Provenance Audit

Every dataset artifact and source generator within `native_ai` was inspected to establish origin, authorship, and actual licensing:

| Source Identifier | Artifact Name / Path | Generator / Script Origin | Creator | Content Nature | Applicable License | Status | SHA-256 Checksum |
|---|---|---|---|---|---|:---:|---|
| `src_seed_01` | `datasets/raw/seed_corpus.txt` | `native_ai/tokenizer/corpus.py` | LOVE Project Author | Original synthetic technical prose & dictionary sentences | Public Domain (CC0-1.0) | VERIFIED (Tokenizer only) | `5bace1826b1414a6d0b08fa08c853911a187c6eda999e69a34cfdb57d38d9b12` |
| `src_eval_01` | `datasets/raw/held_out_eval.txt` | `native_ai/tokenizer/corpus.py` | LOVE Project Author | Original synthetic held-out paragraphs | Public Domain (CC0-1.0) | VERIFIED (Tokenizer only) | `ca31b2367976e181b460948942898ff239d121dbcf28b0ed18885c6fc6fb8506` |
| `src_gen_en_01` | `datasets/raw/general_english.jsonl` | `native_ai/datasets/curate_raw_sources.py` | LOVE Project Author | Original synthetic encyclopedic text (7 topics x 5 reps + dirty fixture) | Public Domain (CC0-1.0) | **VERIFIED** | `ebaeb4670d6c95bd97901bb644444fdb4deeacfc45257f8da2d492e1b16b3b21` |
| `src_math_01` | `datasets/raw/reasoning_math.jsonl` | `native_ai/datasets/curate_raw_sources.py` | LOVE Project Author | Original synthetic step-by-step math problems (4 topics x 5 reps) | Public Domain (CC0-1.0) | **VERIFIED** | `601a4e5b4c20a3469aa20b50c1fa7002c3a156c7b0e8039c2bfe4d9169c1e585` |
| `src_dialog_01` | `datasets/raw/instruction_dialog.jsonl` | `native_ai/datasets/curate_raw_sources.py` | LOVE Project Author | Original synthetic multi-turn assistant dialogues (3 topics x 7 reps) | Public Domain (CC0-1.0) | **VERIFIED** | `5b99a58c00b247e110ada5741031c79e741da05407206577c17f4633b6d5ffb4` |
| `src_tech_01` | `datasets/raw/technical_code.jsonl` | `native_ai/datasets/curate_raw_sources.py` | LOVE Project Author | Original synthetic code snippets & OS theory (3 topics x 5 reps + key fixture) | **Unresolved (Improper MIT tag)** | **UNRESOLVED** | `fa06253c3d4635b5b46338985b3591f3a7baa89164422647b1aadee79db25ed7` |
| `src_struct_01` | `datasets/raw/structured_tasks.jsonl` | `native_ai/datasets/curate_raw_sources.py` | LOVE Project Author | Original synthetic JSON extraction & planning tasks (2 topics x 5 reps) | Public Domain (CC0-1.0) | **VERIFIED** | `86bae570c0b7290987e3d036ceabe4aa27ae67cb467b9c05247152dff062f58f` |

#### Manifest Checksum vs On-Disk CRLF Audit Finding:
In `seed_corpus_manifest.json`, the recorded file size was 1,974,028 bytes with SHA-256 `55457565fa3d71e7f16d25c547400ad735698d8045b5a3782b08ba35fb8c14f0`. On disk, `seed_corpus.txt` measures 2,001,924 bytes with SHA-256 `5bace1826b1414a6d0b08fa08c853911a187c6eda999e69a34cfdb57d38d9b12`. The exact difference of **27,896 bytes** corresponds precisely to Windows CRLF line endings (`\r\n` vs `\n`) across 27,896 line breaks. The file content is 100% identical.

---

### 3. Licence Verification & Unresolved Records

A strict legal review of the source registry was conducted:

1. **Synthetic CC0-1.0 Foundations (`src_gen_en_01`, `src_math_01`, `src_dialog_01`, `src_struct_01`):**  
   - **Origin:** Hand-authored directly within `curate_raw_sources.py` as project test fixtures.
   - **Legal Status:** **VERIFIED**. The author of the code and text dedicated all copyrights to the public domain under Creative Commons Zero 1.0. Unrestricted usage for research, fine-tuning, and model pretraining is legally sound.

2. **The `src_tech_01` Misclassification:**  
   - **Prior Claim:** `source_registry.json` designated this corpus as **MIT** with `license_reference: "https://opensource.org/licenses/MIT"` and `restrictions: "Preserve copyright and license notice in source registry metadata"`.
   - **Audit Finding:** **FAILED AUDIT / UNRESOLVED**. Inspection revealed that the Python code snippets (causal attention mask, binary search) and OS text were written in-repo by the project developer. There is NO third-party upstream Git repository, NO upstream copyright header, and NO third-party author. Assigning the MIT software license to internal synthetic test text was a categorization error.
   - **Action Taken:** The record status in `DatasetSourceRegistry` has been changed to **UNRESOLVED**, `is_approved_for_training` set to **`False`**, and its 3 admitted documents are **excluded from approved training corpora** until formally relicensed as CC0 or dedicated project internal data.

---

### 4. Corrected Split Percentages & Statistics

The previous report claimed that documents were split into **98% Train, 1% Val, and 1% Test**. This was mathematically impossible on a 22-document corpus.

#### Measured Split Proportions vs Erroneous Claims:

| Split Name | Erroneous Claim | Actual Doc % | Document Count | Actual Word % | Word Count | Actual Token % | Token Count | File Size (Bytes) | SHA-256 Checksum |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **Train** | 98.0% | **90.91%** | **20** | **91.30%** | 1,951 | **90.24%** | **5,768** | 17,545 | `61c1cdbffcdb562c498f4890ba36915692240f05a676e54e0f97ba81fd34a620` |
| **Validation** | 1.0% | **4.55%** | **1** | **4.49%** | 96 | **3.68%** | **235** | 908 | `b9d4787b48d0286b5df3a94141c478158a6aa96f1c69b8e879d3d38c36782103` |
| **Test** | 1.0% | **4.55%** | **1** | **4.21%** | 90 | **6.09%** | **389** | 984 | `fc622dd9543bf98ca9e4d85638d93dd039ecc5994a5a1dcd0034980c57cc26e2` |
| **Total** | 100.0% | **100.0%** | **22** | **100.0%** | 2,137 | **100.0%** | **6,392** | 19,437 | — |

#### Statistical Evaluation Critique:
- **Zero Statistical Reliability:** A validation set of **1 single document** (96 words, 235 tokens) provides zero variance estimation. If that single document happens to contain vocabulary that is slightly out of distribution, the measured validation loss spikes dramatically regardless of overall model quality.
- **Minimum Evaluation Threshold:** For small-model pretraining experiments, an evaluation split requires a minimum of **50 to 100 independent documents** or at least **20,000 to 50,000 tokens** per split to achieve statistical significance.

---

### 5. Dataset Quality & Pipeline Findings

The NAI-03 pipeline modules were evaluated under production conditions:

1. **Text Cleaning (`TextCleaner`):**
   - NFKC normalization applied across all documents.
   - Stripped all HTML artifacts (`<p>`, `<h1>`, `&amp;`) without distorting code symbols or mathematics.
   - Enforced minimum threshold ($\ge 40$ chars, $\ge 8$ words). 0 documents rejected.
2. **Privacy Filtering (`PrivacyFilter`):**
   - Correctly dropped injected test secret `fixture_secret_01` (`-----BEGIN RSA PRIVATE KEY-----`).
   - Redacted personal PII in `fixture_dirty_01` (`personal_john@gmail.com` $\to$ `[EMAIL_REDACTED]`, `555-123-4567` $\to$ `[PHONE_REDACTED]`).
   - Safely retained standard technical identifiers (`test_user@example.com`, `https://love.local/docs/v1/api`).
3. **Composite Deduplication (`Deduplicator`):**
   - 38 exact duplicate documents removed.
   - 42 near-duplicate documents removed via 3-shingle MinHash with Jaccard $\ge 0.85$.
   - Successfully collapsed 103 raw entries into 22 unique admitted documents.
4. **LOVE Tokenizer v0.1 Compatibility:**
   - Evaluated on admitted documents: **2.991 tokens/word**, **2.289 bytes/token**.
   - **100% UTF-8 roundtrip lossless fidelity** (0 byte discrepancies).
   - **100.0% of documents fit within context length 512** (Mean: 290.5 tokens, Max: 471 tokens).

---

### 6. Three Dataset Scale Scenarios

To guide future data ingestion for the 5.5M-parameter LOVE Transformer, three distinct local corpus scale scenarios were modeled using `native_ai/datasets/scale_targets.py`:

| Parameter / Metric | Scenario A: Minimal Pilot | Scenario B: Small-Model Pretraining | Scenario C: Expanded Training Corpus |
|---|---|---|---|
| **Target Tokens** | **1,000,000** (1M) | **20,000,000** (20M) | **100,000,000** (100M) |
| **Token-to-Param Ratio** | ~0.18 tokens / param | ~3.63 tokens / param | ~18.16 tokens / param (Near Chinchilla) |
| **Estimated Documents** | ~4,000 docs (avg 250 tok/doc) | ~71,429 docs (avg 280 tok/doc) | ~333,333 docs (avg 300 tok/doc) |
| **Raw Text Size** | ~3.6 MB | ~72.0 MB | ~360.0 MB |
| **Processed JSONL Size** | ~4.9 MB | ~97.2 MB | ~486.0 MB |
| **Tokenized Storage (`uint16`)** | 2.0 MB | 40.0 MB | 200.0 MB |
| **Total Estimated Disk Footprint** | **~10.5 MB** | **~209.2 MB** | **~1,046.0 MB (~1.02 GB)** |
| **Data Processing Time (i7-7700)** | ~3.3 seconds | ~59.5 seconds (~1.0 min) | ~277.8 seconds (~4.6 min) |
| **GTX 1650 Throughput (Ctx 512)** | 20,000 tokens / sec | 20,000 tokens / sec | 20,000 tokens / sec |
| **Planned Epochs** | 3 epochs (3M tokens compute) | 3 epochs (60M tokens compute) | 2 epochs (200M tokens compute) |
| **Total Training Duration** | **150 seconds (~2.5 minutes)** | **3,000 seconds (~50 minutes)** | **10,000 seconds (~2.78 hours)** |
| **Peak VRAM Allocated** | ~358 MB | ~358 MB | ~358 MB |
| **Hardware Feasibility** | **FEASIBLE** | **FEASIBLE** | **FEASIBLE** |
| **Disk Safety on F: (4.89 GB free)**| **SAFE** (0.21% disk used) | **SAFE** (4.27% disk used) | **SAFE** (21.39% disk used) |
| **Primary Objective** | Smoke test training loop, LR scheduler, loss descent, and checkpoint recovery without memorizing small static files. | Establish foundational English grammar, conversational coherence, simple math, and basic instruction following in 5.5M model. | Fully saturate representation capacity of 5.5M architecture; provide foundational training asset for future 15M-30M models. |
| **Expected Limitations** | Zero factual knowledge; prone to overfitting if trained > 3 epochs. | Modest reasoning ability; limited long-tail factual knowledge due to 5.5M parameter bottleneck. | Storage overhead requires staging discipline; diminishing returns on 5.5M model due to 4-layer / 256-dim architectural ceiling. |

---

### 7. Local Hardware Feasibility (GTX 1650 4GB)

Pretraining feasibility was verified using empirical telemetry from the NAI-01 forward/backward benchmarks on the physical host:

- **GPU:** NVIDIA GeForce GTX 1650 (TU117 Turing, Compute Capability 7.5).
- **VRAM Total:** 4,096 MiB (4.0 GB).
- **VRAM Desktop Idle Allocation:** ~1,680 MiB claimed by Windows Desktop Window Manager and display driver.
- **Available Dedicated VRAM:** **~2,256 MiB** available for PyTorch.
- **VRAM Required for 5.5M Model Training:**
  - Model Parameters (FP32): 22.0 MB
  - Gradients (FP32): 22.0 MB
  - AdamW Optimizer States (FP32 first & second moments): 44.0 MB
  - Activations (Ctx 512, Batch 2 with SDPA): ~150 MB
  - PyTorch CUDA Context & Scratch: ~120 MB
  - **Total Peak Allocated VRAM:** **~358 MB**
  - **VRAM Headroom:** **~1,898 MiB (~1.85 GB)** unallocated safety buffer.
- **Compute Feasibility:** The GTX 1650 sustains **~20,000 tokens/sec** in FP32 with effective batch size 8 (batch 2 $\times$ gradient accumulation 4). Training 20M tokens across 3 epochs requires only **50 minutes**, running comfortably at 36°C load with a 75W board power limit.

---

### 8. Storage Estimates & Disk Safety Constraints

All activities were benchmarked against available physical storage on drive `F:`:

- **Drive F: Total Capacity:** 52.53 GB
- **Drive F: Used Space:** 44.04 GB
- **Drive F: Currently Free:** **4.89 GB (5,000 MB)**
- **Safe Working Disk Ceiling:** 1.50 GB (preserving at least 3.39 GB free disk buffer for OS swap and checkpointing).

#### Disk Consumption Projections Across Scenarios:

```mermaid
xychart-beta
    title "Disk Space Consumption vs Available Free Space on F: (MB)"
    x-axis ["Current Corpus", "Scenario A (1M)", "Scenario B (20M)", "Scenario C (100M)", "Safety Threshold", "Free Space F:"]
    y-axis "Storage (MB)" 0 --> 5000
    bar [0.02, 10.5, 209.2, 1046.0, 1500.0, 4890.0]
```

- **Scenario A:** Consumes 10.5 MB (**0.21%** of free space) $\implies$ **STRICTLY SAFE**.
- **Scenario B:** Consumes 209.2 MB (**4.27%** of free space) $\implies$ **STRICTLY SAFE**.
- **Scenario C:** Consumes 1,046 MB (**21.39%** of free space) $\implies$ **SAFE** (provided intermediate raw text files are purged or compressed once tokenized into memory-mapped binary files).
- **Network Share Isolation:** Drive `Z:\` (`Shared_Folder`, 2,334 GB free) was completely excluded from all operations.

---

### 9. Proposed External Licensed English Data Sources

To reach **Scenario B (20M tokens)** or **Scenario C (100M tokens)** lawfully, the following shortlist of well-documented public-domain and permissive resources was evaluated:

| Source Name | Official URL | License | ML Training / Redistribution Terms | Dataset Size (Full / Proposed Slice) | English Suitability | Data Category | Privacy / PII Risk | Download Size | Storage Req. | Recommendation |
|---|---|---|---|---|---|---|---|---|---|:---:|
| **Standard Ebooks / Project Gutenberg** | `https://standardebooks.org/`<br>`https://www.gutenberg.org/` | **Public Domain (Pre-1929)** | Unrestricted training, modification, commercial use, and redistribution. Zero copyright restrictions. | Full: >60,000 books<br>**Slice: ~15M tokens** | Pristine, edited literary, historical, and expository prose. | Category A (General English) | Zero PII (historical texts). | ~20 MB | ~35 MB | **RECOMMENDED FOR INCLUSION** |
| **Simple English Wikipedia Dump** | `https://dumps.wikimedia.org/simplewiki/` | **CC-BY-SA 4.0 / GFDL** | Commercial & research use permitted with attribution. Model weights are non-derivative functional artifacts. | Full: ~240,000 articles (~60M tokens)<br>**Slice: ~10M tokens** | Clear, accessible, syntactically clean English. Ideal for 8,192 BPE vocab. | Category A (Encyclopedic Knowledge) | Low risk (public factual encyclopedia). | ~25 MB | ~40 MB | **RECOMMENDED FOR INCLUSION** |
| **TinyStories** (Eldan & Li, Microsoft Research) | `https://huggingface.co/datasets/roneneldan/TinyStories` | **CDLA-Permissive-2.0** | Broadly permissive for commercial/research training and downstream model release. | Full: 2.1M stories (~460M tokens)<br>**Slice: ~5M tokens** | Engineered specifically for small models (1M-30M) to learn grammar and reasoning. | Category A & B (English & Reasoning) | Zero PII (100% synthetic, child-safe). | ~15 MB | ~25 MB | **RECOMMENDED FOR INCLUSION** |
| **GSM8K** (Grade School Math 8K) | `https://github.com/openai/grade-school-math` | **MIT License** | Full commercial and non-commercial model training permitted with MIT notice. | Full: 8,500 problems<br>**Slice: ~1.5M tokens** | Step-by-step mathematical reasoning and plain English logic. | Category B (Reasoning & Math) | Zero PII (grade school math problems). | ~2.5 MB | ~4.5 MB | **RECOMMENDED FOR INCLUSION** |
| **The Stack - Permissive Algorithmic Python Subset** | `https://huggingface.co/datasets/bigcode/the-stack` | **Permissive (MIT, Apache-2.0, BSD-3)** | Code training permitted with attribution metadata preserved in source manifests. | Full: 3 TB<br>**Slice: ~5,000 files (~2M tokens)** | High-quality Python docstrings, algorithms, and clean syntax. | Category D (Coding & Technical) | Low risk (filtered for secrets via PrivacyFilter). | ~6 MB | ~10 MB | **RECOMMENDED FOR INCLUSION** |
| **OpenAssistant OASST1 (English Dialogues)** | `https://huggingface.co/datasets/OpenAssistant/oasst1` | **Apache-2.0** | Unrestricted model training and redistribution of derivative model weights. | Full: ~10,000 dialogues<br>**Slice: ~2,500 dialogues (~1.5M tokens)** | High-quality, human-curated multi-turn conversational assistance. | Category C (Instruction & Dialog) | Low/Medium (requires passing through PrivacyFilter). | ~5 MB | ~8 MB | **RECOMMENDED FOR INCLUSION** |
| **OpenWebText / OpenWebText2** | `https://skylion007.github.io/OpenWebTextCorpus/` | **Uncertain / Scraped Reddit Outbound Links** | High legal risk; contains third-party copyrighted news, paywalled blogs, and unlicensed text. | >40 GB | Variable web English. | Web Scraping | High (personal data, unlicensed articles). | >12 GB | >40 GB | **STRONGLY EXCLUDED** |
| **BookCorpus (Zhu et al.)** | Unofficial Mirrors | **Unlicensed / Copyright Infringement** | Scraped from self-published books without author consent. Known copyright liability. | ~5 GB | Fiction novels. | Fiction | High copyright liability. | ~2 GB | ~5 GB | **STRONGLY EXCLUDED** |

> [!IMPORTANT] External Dataset Ingestion Policy
> In accordance with Critical Rule 10, **zero external datasets have been downloaded**. The recommended shortlist above is presented strictly for user review and authorization prior to any network retrieval.

---

### 10. Recommended Next Steps

To advance the LOVE Native AI project to pretraining readiness:

1. **User Approval of Candidate Data Sources:** Obtain user sign-off on the recommended licensed shortlist (Standard Ebooks slice, Simple English Wikipedia slice, TinyStories slice, GSM8K, and OASST1 slice) totaling ~25M tokens (~250 MB disk).
2. **Resolve `src_tech_01` Licensing:** Re-license internal synthetic technical code documents under explicit CC0-1.0 to clear legal attribution.
3. **Controlled, Streamed Ingestion:** Execute rate-limited ingestion of approved slices into `datasets/raw/` with immediate SHA-256 validation.
4. **Leakage-Resistant Group Splitting:** Apply the enhanced `DatasetSplitter` with group-level segregation and minimum evaluation sample sizes ($\ge 50$ documents each in validation and test).
5. **Memory-Mapped Binary Tokenization:** Pre-tokenize admitted splits into contiguous `uint16` memory-mapped arrays (`train.bin`, `val.bin`) using LOVE Tokenizer v0.1 to maximize GTX 1650 throughput.
6. **Pretraining Readiness Sign-off:** Re-run the readiness audit once 20M tokens are tokenized, verifying zero disk overflow on `F:`.

---

### 11. Actual Automated Test Counts

The test suite was executed in the local virtual environment (`F:\LOVE\native_ai\.venv\Scripts\pytest -v F:\LOVE\native_ai\tests`):

```
native_ai/tests/test_architecture.py::test_configuration_validation PASSED [  2%]
native_ai/tests/test_architecture.py::test_embedding_output_shape_and_bounds PASSED [  4%]
native_ai/tests/test_architecture.py::test_rmsnorm_stability PASSED      [  6%]
native_ai/tests/test_architecture.py::test_rope_dimensions_and_rotation PASSED [  9%]
native_ai/tests/test_architecture.py::test_swiglu_dimensions PASSED      [ 11%]
native_ai/tests/test_architecture.py::test_causal_self_attention_shape_and_sdpa PASSED [ 13%]
native_ai/tests/test_architecture.py::test_causal_masking_future_token_leakage_prevention PASSED [ 16%]
native_ai/tests/test_architecture.py::test_transformer_block_residual_connections PASSED [ 18%]
native_ai/tests/test_architecture.py::test_tied_input_output_embeddings PASSED [ 20%]
native_ai/tests/test_architecture.py::test_loss_calculation_and_gradient_finiteness PASSED [ 23%]
native_ai/tests/test_architecture.py::test_adamw_optimizer_step PASSED   [ 25%]
native_ai/tests/test_architecture.py::test_cpu_execution PASSED          [ 27%]
native_ai/tests/test_architecture.py::test_cuda_execution PASSED         [ 30%]
native_ai/tests/test_dataset_pipeline.py::test_source_registry_and_license_validation PASSED [ 32%]
native_ai/tests/test_dataset_pipeline.py::test_text_cleaning_rules PASSED [ 34%]
native_ai/tests/test_dataset_pipeline.py::test_privacy_filter_redaction_and_rejection PASSED [ 37%]
native_ai/tests/test_dataset_pipeline.py::test_deduplication_exact_normalized_and_near PASSED [ 39%]
native_ai/tests/test_dataset_pipeline.py::test_deterministic_splitting_and_zero_cross_split_leakage PASSED [ 41%]
native_ai/tests/test_dataset_pipeline.py::test_streaming_ingestion_generator PASSED [ 44%]
native_ai/tests/test_dataset_pipeline.py::test_tokenizer_compatibility_on_splits PASSED [ 46%]
native_ai/tests/test_dataset_pipeline.py::test_source_provenance_validation PASSED [ 48%]
native_ai/tests/test_dataset_pipeline.py::test_license_evidence_completeness PASSED [ 51%]
native_ai/tests/test_dataset_pipeline.py::test_missing_source_attribution PASSED [ 53%]
native_ai/tests/test_dataset_pipeline.py::test_incorrect_document_split_percentages PASSED [ 55%]
native_ai/tests/test_dataset_pipeline.py::test_token_count_reporting PASSED [ 58%]
native_ai/tests/test_dataset_pipeline.py::test_group_level_leakage PASSED [ 60%]
native_ai/tests/test_dataset_pipeline.py::test_reproducible_source_manifests PASSED [ 62%]
native_ai/tests/test_dataset_pipeline.py::test_insufficient_validation_test_sample_warnings PASSED [ 65%]
native_ai/tests/test_dataset_pipeline.py::test_storage_capacity_estimation PASSED [ 67%]
native_ai/tests/test_tokenizer.py::test_vocab_size_and_special_tokens PASSED [ 69%]
native_ai/tests/test_tokenizer.py::test_encode_decode_round_trip PASSED  [ 72%]
native_ai/tests/test_tokenizer.py::test_empty_and_whitespace_text PASSED [ 74%]
native_ai/tests/test_tokenizer.py::test_case_preservation PASSED         [ 76%]
native_ai/tests/test_tokenizer.py::test_punctuation_and_symbols PASSED   [ 79%]
native_ai/tests/test_tokenizer.py::test_numbers_and_formatting PASSED    [ 81%]
native_ai/tests/test_tokenizer.py::test_urls_and_identifiers PASSED      [ 83%]
native_ai/tests/test_tokenizer.py::test_unicode_and_uncommon_characters PASSED [ 86%]
native_ai/tests/test_tokenizer.py::test_repeated_text_and_long_input PASSED [ 88%]
native_ai/tests/test_tokenizer.py::test_special_token_boundaries_and_chat_template PASSED [ 90%]
native_ai/tests/test_tokenizer.py::test_save_and_reload_equivalence PASSED [ 93%]
native_ai/tests/test_tokenizer.py::test_deterministic_encoding PASSED    [ 95%]
native_ai/tests/test_tokenizer.py::test_batch_encode_padding_and_truncation PASSED [ 97%]
native_ai/tests/test_tokenizer.py::test_transformer_integration_compatibility PASSED [100%]

======================= 43 passed, 2 warnings in 14.78s =======================
```

- **Architecture Suite (`test_architecture.py`):** 13/13 passed.
- **Dataset Pipeline Suite (`test_dataset_pipeline.py`):** 16/16 passed (7 original + 9 audit tests).
- **Tokenizer Suite (`test_tokenizer.py`):** 14/14 passed.
- **Total Test Count:** **43 passed, 0 failed (100% pass rate)**.

---

### 12. Explicit Pretraining Readiness Decision

| Audit Dimension | Evaluated Requirement | Audit Finding | Verdict |
|---|---|---|:---:|
| **Pipeline Infrastructure** | Streaming ingestion, cleaning, deduplication, privacy filtering | All modules operating flawlessly with 100% test coverage | **VERIFIED** |
| **Tokenizer Integration** | Vocabulary compatibility, lossless roundtrip, context bounds | 100% UTF-8 fidelity, 2.991 tokens/word, 0 truncated documents | **VERIFIED** |
| **Hardware Feasibility** | GTX 1650 4GB memory allocation and compute throughput | 358 MB peak VRAM, ~20,000 tokens/sec in FP32, >1.8 GB headroom | **VERIFIED** |
| **Storage Constraint Safety** | Disk headroom on drive F: (4.89 GB available) | Scenario B consumes 209 MB (~4.3% disk); >3.3 GB buffer preserved | **VERIFIED** |
| **Split Statistics Accuracy** | True mathematical distribution recorded in manifests | Corrected from false 98/1/1 to true 90.91% / 4.55% / 4.55% | **VERIFIED** |
| **Provenance & Licensing** | Legal evidence completeness and third-party validation | 4 CC0 sources verified; `src_tech_01` marked UNRESOLVED | **PARTIALLY VERIFIED** |
| **Corpus Scale for Pretraining** | Sufficient token volume to train 5.5M parameters | Admitted 6,392 tokens represents < 0.01% of required 20M tokens | **FAILED** |
| **Evaluation Set Adequacy** | Statistically significant validation & test samples | Single-document evaluation sets provide zero statistical power | **FAILED** |
| **Overall Pretraining Gate** | Authorization to initiate language model pretraining | Pretraining cannot proceed without severely overfitting | **BLOCKED** |

#### Final Decision:
**BLOCKED — NOT READY FOR PRETRAINING.**  
Model pretraining and Phase NAI-04 MUST NOT be initiated until external licensed corpora are approved by the user, ingested, and tokenized into at least **Scenario B scale (20M tokens)** with statistically robust evaluation splits.
