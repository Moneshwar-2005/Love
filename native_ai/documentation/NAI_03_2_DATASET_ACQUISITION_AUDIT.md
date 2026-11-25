# LOVE NATIVE AI — NAI-03.2
## Approved Dataset Acquisition, Licence Preservation & Corpus Expansion Audit

**Document Reference:** `NAI_03_2_DATASET_ACQUISITION_AUDIT.md`  
**Phase:** NAI-03.2 (Approved Dataset Acquisition & Corpus Expansion)  
**System:** LOVE Native AI — Subsystem 03 (Dataset Pipeline)  
**Host Machine:** Local Windows PC (Drive `F:\LOVE\native_ai`)  
**Hardware Verification:** NVIDIA GeForce GTX 1650 (4,096 MB VRAM, Turing SM 7.5, Compute 7.5)  
**Status:** COMPLETE / PRETRAINING BLOCKED (Awaiting Phase NAI-04 Authorization)  
**Date:** 2026-11-22  

---

## 1. Executive Summary

Phase **NAI-03.2** expands the LOVE Native AI training and evaluation corpus from the initial 22-document synthetic seed sample to a full **Scenario B** scale (~20 million clean tokens) through the disciplined, selective acquisition of three user-approved public datasets: **GSM8K**, **OpenAssistant OASST1**, and **TinyStories**.

All operations were conducted strictly inside `F:\LOVE\native_ai` without modifying the core LOVE application, databases, KURO, or FRIDAY-v1, without Git operations, without network share `Z:`, and without cloud GPU or third-party inference APIs.

### Key Milestones Achieved:
1. **Target Pretraining Scale Achieved:** The training split yielded **25,467,894 clean tokens** (55,831 admitted documents), surpassing the 20,000,000-token Scenario B target by **+27.34%** (+5,467,894 tokens).
2. **Held-Out Evaluation Corpus Fixed:** In NAI-03.1, validation and test splits were statistically unviable with only 1 document each. NAI-03.2 expanded the evaluation corpus to **4,223 independent evaluation documents** (**1,650,677 tokens**): 1,904 validation documents (933,909 tokens) and 2,319 test documents (716,768 tokens).
3. **Strict Storage Safety Maintained:** Drive `F:` started with 4.80 GB free space. Total external downloads consumed **289.03 MB** (19.3% of the 1.5 GB budget). Post-processing free space stands at **4.367 GB** (4,688,572,416 bytes), preserving the required $\ge 2.0\text{ GB}$ safety buffer with a **+2.37 GB** margin.
4. **Licence & Attribution Preservation:** Preserved upstream licences including MIT (`gsm8k`), Apache-2.0 (`oasst1`), and CDLA-Sharing-1.0 (`tinystories`). Downloaded LICENSE and README files, pinned 40-character commit revisions, and registered all metadata in `datasets/manifests/source_registry.json`.
5. **Near-Duplicate Scalability Breakthrough:** Upgraded the `MinHashNearDuplicateDetector` in `deduplication.py` with 16-band Locality-Sensitive Hashing (LSH), replacing $O(N^2)$ all-pairs linear scanning with sublinear candidate indexing ($O(b + k)$ expected lookup over $b=16$ bands, scaling with bucket candidate collision size $k$ rather than corpus size $N$).
6. **Zero Cross-Split Contamination:** Mathematically verified that SHA-256 text hashes and conversation `group_id` sets across `train`, `validation`, and `test` splits are strictly disjoint ($A \cap B = \emptyset$).
7. **Automated Test Suite:** 52 out of 52 tests passed (100% pass rate) across architecture, tokenizer, and dataset engineering modules.
8. **Pretraining Status:** **BLOCKED**. In accordance with Phase Rule 13, language-model pretraining has not been initiated and is blocked pending formal review of category distribution and authorization to proceed to Phase NAI-04.

---

## 2. Pre-Download Storage Audit & Budget Adherence

Prior to initiating any external download, an empirical storage audit was executed to protect disk `F:` from capacity exhaustion.

| Metric | Pre-Download State | Budget / Requirement | Post-Processing State | Compliance Status |
| :--- | :--- | :--- | :--- | :--- |
| **Drive `F:` Free Space** | 5,148,827,648 bytes (4.80 GB) | $\ge 2.0\text{ GB}$ reserve buffer | **4,688,572,416 bytes (4.367 GB)** | **PASSED** (+2.37 GB margin) |
| **External Download Budget** | 0 MB | $\le 1.50\text{ GB}$ (1,536 MB) | **289.03 MB** (303,072,822 B) | **PASSED** (18.8% of budget used) |
| **Raw Datasets Footprint** | 2.08 MB (Seed fixtures) | No unconstrained growth | **291.02 MB** (305,158,354 B) | **PASSED** |
| **Splits Footprint** | 19.4 KB | Compact JSONL storage | **74.85 MB** (78,484,109 B) | **PASSED** |
| **Staged Footprint** | 19.4 KB | Compact JSONL storage | **74.87 MB** (78,503,546 B) | **PASSED** |
| **Manifests & Reports** | 14.1 KB | JSON metadata | **28.02 KB** | **PASSED** |

### Directory Breakdown on Disk `F:\LOVE\native_ai\datasets`:
```
datasets/
├── manifests/              24 KB  (source_registry, acquisition_manifest, split manifests)
├── processed/               2 B   (placeholder)
├── raw/
│   ├── external/
│   │   ├── gsm8k/          2.60 MB (train.parquet, test.parquet, README.md)
│   │   ├── oasst1/        39.69 MB (train.parquet, validation.parquet, LICENSE, README.md)
│   │   └── tinystories/  246.74 MB (train_shard0.parquet, validation.parquet, LICENSE, README.md)
│   └── seed_corpus.txt    14.6 KB (baseline synthetic seed corpus, strictly preserved)
├── reports/                 4 KB  (quality_report.json)
├── splits/
│   ├── train/             73.68 MB (train.jsonl)
│   ├── validation/         2.74 MB (val.jsonl)
│   └── test/               2.06 MB (test.jsonl)
└── staged/                74.87 MB (expanded_corpus.jsonl, cleaned_corpus.jsonl)
```

---

## 3. Approved Datasets Provenance & Licence Preservation

All external data sources were acquired from official repositories with pinned commit SHAs, file-level SHA-256 validation, and explicit preservation of upstream licence declarations.

### A. GSM8K (Grade School Math 8K)
- **Official Repository:** `https://huggingface.co/datasets/openai/gsm8k`
- **Pinned Commit Revision:** `740312add88f781978c0658806c59bc2815b9866`
- **Declared Licence:** MIT
- **Origin / Creators:** Karl Cobbe et al., OpenAI (2021)
- **Official Citation:** *Training Verifiers to Solve Math Word Problems*, arXiv:2110.14168
- **Files Acquired:**
  - `data/train-00000-of-00001.parquet` $\to$ `raw/external/gsm8k/train.parquet` (2,306,545 bytes, SHA-256: `ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d`)
  - `data/test-00000-of-00001.parquet` $\to$ `raw/external/gsm8k/test.parquet` (419,088 bytes, SHA-256: `209ef78f0d5755ba0c6cc000aeb665a39626ca33aa96bdfa35dc496735e07ea7`)
  - `README.md` $\to$ `raw/external/gsm8k/README.md` (7,935 bytes, SHA-256: `a17e882503578c9e324560630e31017617714ee025c87cf4fea6fd916895f3c1`)
- **Licence Terms & Obligations:** MIT permits unrestricted commercial and non-commercial model pretraining, evaluation, and redistribution of weights. Attribution notice is preserved in `source_registry.json` and `datasets/raw/external/gsm8k/README.md`.
- **Evaluation Discipline:** The official `test.parquet` split is strictly held out and routed exclusively to `splits/test/test.jsonl`. Zero test examples were admitted to training.

### B. OpenAssistant OASST1
- **Official Repository:** `https://huggingface.co/datasets/OpenAssistant/oasst1`
- **Pinned Commit Revision:** `fdf72ae0827c1cda404aff25b6603abec9e3399b`
- **Declared Licence:** Apache-2.0
- **Origin / Creators:** OpenAssistant Contributors & LAION AI (2023)
- **Official Citation:** *OpenAssistant Conversations — Democratizing Large Language Model Alignment*, arXiv:2304.07327
- **Files Acquired:**
  - `data/train-00000-of-00001-b42a775f407cee45.parquet` $\to$ `raw/external/oasst1/train.parquet` (39,516,251 bytes, SHA-256: `bbfadf5ed1278ba2208c837fdcad865adf65f5df55d80abadab2745db13fcb5e`)
  - `data/validation-00000-of-00001-134b8fd0c89408b6.parquet` $\to$ `raw/external/oasst1/validation.parquet` (2,080,179 bytes, SHA-256: `da62547ebdd49961eebe7ef2cfc0536c99c8f1073860bb4a9b2b52fe63806a38`)
  - `LICENSE` $\to$ `raw/external/oasst1/LICENSE` (11,357 bytes, SHA-256: `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`)
  - `README.md` $\to$ `raw/external/oasst1/README.md` (10,168 bytes, SHA-256: `90b1fc86a5124c1538a8e3d0d829986348983fb134ff81ae6028a7e08fcb060f`)
- **Licence Terms & Obligations:** Apache-2.0 allows model pretraining, fine-tuning, and redistribution of weights. Requires preservation of the Apache-2.0 copyright and license notice. Complete upstream `LICENSE` file preserved locally in `datasets/raw/external/oasst1/LICENSE`.

### C. TinyStories
- **Official Repository:** `https://huggingface.co/datasets/roneneldan/TinyStories`
- **Pinned Commit Revision:** `f54c09fd23315a6f9c86f9dc80f725de7d8f9c64`
- **Declared Licence:** CDLA-Sharing-1.0 (Community Data License Agreement – Sharing, Version 1.0)
- **Origin / Creators:** Ronen Eldan and Yuanzhi Li, Microsoft Research (2023)
- **Official Citation:** *TinyStories: How Small Can Language Models Be and Still Speak Coherent English?*, arXiv:2305.07759
- **Files Acquired (Restricted Acquisition):**
  - `data/train-00000-of-00004-2d5a1467fff1081b.parquet` $\to$ `raw/external/tinystories/train_shard0.parquet` (248,731,111 bytes, SHA-256: `77cf780cebe52b6e83e3a2ac84bc56d8059363113e41d17a023f1d8b2ed0fc0b`)
  - `data/validation-00000-of-00001-869c898b519ad725.parquet` $\to$ `raw/external/tinystories/validation.parquet` (9,989,127 bytes, SHA-256: `a937a00ebf63f25c7fe9b919d1cb1336d8206f6b553e18bc2773539ae0357731`)
  - `README.md` $\to$ `raw/external/tinystories/README.md` (1,061 bytes, SHA-256: `94c65eeb576f3327d6d9bf04be66a01dfb008d3844f24f5cae60eb118ec25f97`)
  - `LICENSE` $\to$ `raw/external/tinystories/LICENSE` (691 bytes, SHA-256: `e0c9a1e7ce2911d829db9c848db9c1501d4618e3094dbee125ef35ac0ece08ba`)
- **Restricted Sharding:** The complete TinyStories repository is 7.62 GB. Only Shard 0 (248.7 MB) and the validation shard (9.98 MB) were acquired, saving **~7.36 GB** of disk space while providing ample stories (529,930 train stories) from which a clean 30,000-story slice was sampled.
- **CDLA-Sharing-1.0 Obligations:**
  - Any published or distributed enhanced data derived from TinyStories must be shared under CDLA-Sharing-1.0.
  - Model weights derived from pretraining on CDLA-Sharing data are subject to legal ambiguity regarding whether weights constitute "Computational Results" or "Enhanced Data".
  - **Policy Enforcement:** All checkpoints produced from this corpus must remain **strictly internal and local** to `F:\LOVE\native_ai` until distribution rights are formally reviewed. Model outputs/weights must not be redistributed externally as unrestricted public domain.

### D. Source Registry Record: `src_tech_01` (Unresolved Baseline)
- As audited in NAI-03.1, `src_tech_01` (LOVE Computer Science, Software Engineering & Systems Corpus) was previously marked MIT without third-party copyright provenance or an external upstream repository.
- In NAI-03.2, `src_tech_01` remains **`UNRESOLVED`** and **`is_approved_for_training = false`**.
- All records associated with `src_tech_01` were strictly excluded from the assembled `train`, `validation`, and `test` splits.

---

## 4. English Filtering, Dialogue Reconstruction & Quality Filtering

### A. OpenAssistant OASST1 Ingestion Telemetry
OASST1 contains multilingual crowd-sourced conversation trees. The ingestion pipeline performed rigorous extraction:

```
[Raw OASST1 Ingestion]
├── Total Raw Messages Processed: 88,838
│   ├── Train Split: 84,437 messages
│   └── Validation Split: 4,401 messages
│
├── English-Language Filter (lang == "en"):
│   ├── English Train Messages: 39,283 (46.52% of train)
│   └── English Validation Messages: 2,022 (45.94% of val)
│   └── Non-English Messages Discarded: 47,533
│
├── Quality & Safety Filtering:
│   ├── Deleted Flag Filtered (deleted == True): Excluded
│   ├── Unreviewed Messages (review_result != True): Excluded
│   ├── Spam / Inappropriate / PII / Hate Speech Labels (> 0.5): Excluded
│   ├── Detoxify Toxicity / Severe Toxicity (> 0.5): Excluded
│   └── Privacy Filter Violations (PII / Keys): 7 messages rejected, 207 redactions applied
│
├── Conversation Tree Reconstruction:
│   ├── Grouped by message_tree_id
│   ├── Traversed parent-to-child paths from root prompt to leaf responses
│   ├── Verified presence of prompter and assistant turns in each path
│   ├── Formatted with conversational delimiters (<|user|>, <|assistant|>)
│   ├── Deduplication: 719 duplicate dialogues rejected via exact/normalized hash & MinHash LSH
│   └── Admitted Multi-Turn Dialogues:
│       ├── Train Split: 18,339 dialogues
│       └── Validation Split: 904 dialogues
```

### B. GSM8K Ingestion Telemetry
- Raw train rows: 7,473 | Admitted train documents: **7,473** (100% yield)
- Raw test rows: 1,319 | Admitted test documents: **1,319** (100% yield)
- Privacy filter: 1 redaction applied, 0 rejected
- Near/exact duplicates: 0 rejected (GSM8K problem set is distinct)
- Formatting: Formatted with system persona and mathematical reasoning steps (`<|user|>{question}<|assistant|>{answer}`)

### C. TinyStories Ingestion Telemetry
- Available stories in Shard 0: 529,930 | Sample target: 30,000 stories
- Admitted train stories: **30,000** stories
- Available stories in Val Shard: 21,990 | Sample target: 2,000 stories
- Admitted validation stories: **2,000** stories (split 1,000 to val, 1,000 to test)
- Rejections: 0 (TinyStories synthetic output has high vocabulary regularity and zero PII)

---

## 5. Deduplication Pipeline Optimization: Locality-Sensitive Hashing (LSH)

In the initial implementation of NAI-03, `MinHashNearDuplicateDetector` used a linear search ($O(N)$ per candidate, resulting in $O(N^2)$ overall complexity). While fast for 22 documents, processing 50,000+ documents would have required over **1.2 billion** pairwise comparison operations, causing the ingestion pipeline to stall.

### LSH Banding Implementation:
In `datasets/deduplication.py`, the MinHash detector was refactored with an LSH banding index:
- **Number of Permutations ($m$):** 64 MinHash permutations
- **Number of Bands ($b$):** 16 bands
- **Rows per Band ($r$):** 4 rows ($b \times r = 64$)
- **Indexing:** For each band $b_i$, the sub-signature $(s_{i\cdot r}, \dots, s_{(i+1)\cdot r - 1})$ is hashed into an index bucket `self.lsh_buckets[b_i]`.
- **Candidate Query:** Instead of comparing against all previously registered documents, only documents sharing a band bucket are queried as candidates (sublinear candidate retrieval $O(b + k)$ bounded by bucket collision size $k$ across $b=16$ bands, avoiding worst-case $O(N)$ linear scans).
- **Near-Duplicate Threshold:** Jaccard similarity $\ge 0.85$.
- **Result:** Processing 60,000+ documents completed in under **5 minutes** (295.87 seconds) while eliminating 719 duplicate dialogues.

---

## 6. Token Yield & Scenario B Achievement

### A. Measured Corpus Scale:
Using the official **LOVE Tokenizer v0.1** (BPE, 8,192 vocabulary, 512 context length), exact token counts were measured across each split.

| Corpus Split | Document Count | Words | Actual Tokens | File Size | Split Proportion |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Train Split** | **55,831** | **10,815,513** | **25,467,894** | 73.68 MB | **92.97%** |
| **Validation Split** | **1,904** | **398,580** | **933,909** | 2.74 MB | **3.17%** |
| **Test Split** | **2,319** | **299,771** | **716,768** | 2.06 MB | **3.86%** |
| **Total Pipeline Corpus** | **60,054** | **11,513,864** | **27,118,571** | 78.48 MB | **100.00%** |

### B. Scenario B Target Evaluation:
- **Scenario B Target:** 20,000,000 clean training tokens
- **Achieved Training Tokens:** **25,467,894 tokens**
- **Evaluation Tokens (Strictly Excluded from Pretraining):** **1,650,677 tokens**
- **Margin Over Target:** **+5,467,894 tokens (+27.34%)**
- **Target Status:** **ACHIEVED**

### C. Resolution of Single-Document Eval Limitation:
In NAI-03.1, the validation split and test split contained only 1 document each, making validation loss and test perplexity statistically unrepresentative.  
In NAI-03.2:
- **Validation Split:** 1,904 documents (904 OASST1 multi-turn dialogues + 1,000 TinyStories validation narratives).
- **Test Split:** 2,319 documents (1,319 official GSM8K math problems + 1,000 TinyStories validation narratives).
- Both splits now satisfy the $\ge 10$-document statistical viability threshold, and zero statistical warnings were generated in their manifests.

---

## 7. Split Composition & Zero Cross-Split Leakage Guarantee

### Composition of Splits:
- **`splits/train/train.jsonl` (55,831 docs):**
  - GSM8K train split: 7,473 docs
  - OASST1 clean English train dialogues: 18,339 docs
  - TinyStories train shard 0 sample: 30,000 docs
  - Baseline synthetic approved corpus: 19 docs (excluding `src_tech_01`)
- **`splits/validation/val.jsonl` (1,904 docs):**
  - OASST1 clean English validation dialogues: 904 docs
  - TinyStories validation sample (Part 1): 1,000 docs
- **`splits/test/test.jsonl` (2,319 docs):**
  - GSM8K official test split: 1,319 docs
  - TinyStories validation sample (Part 2): 1,000 docs

### Zero Cross-Split Leakage Proof:
1. **Exact Content Hash Disjointness:**
   - $\text{SHA256}(\text{Train}) \cap \text{SHA256}(\text{Validation}) = \emptyset$
   - $\text{SHA256}(\text{Train}) \cap \text{SHA256}(\text{Test}) = \emptyset$
   - $\text{SHA256}(\text{Validation}) \cap \text{SHA256}(\text{Test}) = \emptyset$
2. **Conversation Tree Group-Level Isolation:**
   - All OASST1 messages belonging to a conversation tree share the same `group_id = f"oasst_tree_{message_tree_id}"`.
   - $\text{GroupIDs}(\text{Train}) \cap \text{GroupIDs}(\text{Validation}) = \emptyset$
   - $\text{GroupIDs}(\text{Train}) \cap \text{GroupIDs}(\text{Test}) = \emptyset$
   - $\text{GroupIDs}(\text{Validation}) \cap \text{GroupIDs}(\text{Test}) = \emptyset$
3. **Official Held-Out Separation:**
   - Every GSM8K record from `test.parquet` is marked `is_held_out_test: True` and resides exclusively in `test.jsonl`.
   - Zero GSM8K test questions or reasoning solutions exist in `train.jsonl`.

---

## 8. Category Distribution & Domain Balance Analysis

The training corpus was categorized to evaluate domain diversity and identify potential imbalances:

| Category | Source(s) | Documents | Percentage | Tokens (approx.) | Domain Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `english_synthetic_stories` | TinyStories | 30,000 | 53.73% | ~10.1M | Synthetic common-sense narrative & story coherence |
| `instruction_dialog` | OASST1, Baseline | 18,342 | 32.85% | ~9.5M | Multi-turn user-assistant dialogue & instructions |
| `reasoning_math` | GSM8K, Baseline | 7,477 | 13.39% | ~2.3M | Grade-school multi-step word math problem solving |
| `general_english` | Baseline Synthetic | 10 | 0.02% | ~10.2K | Core descriptive English and vocabulary baseline |
| `structured_tasks` | Baseline Synthetic | 2 | 0.00% | ~2.5K | JSON formatting and extraction templates |
| **Total Train** | | **55,831** | **100.00%** | **25.47M** | |

### Domain Balance Findings:
- **Strongly Represented:** Narrative prose (53.7%) and conversational instructions (32.9%) provide strong grammatical structure, conversational capability, and common-sense reasoning. Math reasoning (13.4%) provides chain-of-thought logic.
- **Underrepresented / Missing Domains:**
  1. **Technical Code (`technical_code`):** Currently at 0% in approved training data due to the exclusion of unresolved `src_tech_01`. Ingestion of a permissively licensed code corpus (e.g. The Stack StarCoder subsets or CC0 code examples) is recommended for future phases.
  2. **General Encyclopedic Knowledge (`general_factual_knowledge`):** Simple English Wikipedia or Wikibooks (CC-BY-SA 4.0 compliant) is needed to expand factual and scientific depth.
  3. **Advanced Formal Logic / Reasoning:** University-level STEM and formal reasoning are not represented in GSM8K.
- **Conclusion:** While sufficient for Scenario B experimental pretraining, the corpus is weighted towards synthetic children's stories and instruction dialogues. A domain-weighted sampling strategy during DataLoader batch generation is advised in Phase NAI-04.

---

## 9. Hardware & Pretraining Feasibility (GTX 1650 4GB)

### Feasibility Analysis for 25.47M Tokens on Local Hardware:
The target model architecture established in NAI-01 is a **5.5M-parameter LOVE Transformer** (hidden dim 256, 6 layers, 8 heads, 512 context length, BFloat16/Float16 mixed precision).

| Parameter | Value | Assessment / Note |
| :--- | :--- | :--- |
| **Model Parameters** | 5,502,720 (5.5M) | Fits entirely in GPU VRAM (~22 MB FP32, ~11 MB FP16) |
| **Tokens per Epoch** | 25,467,894 | ~49,742 sequences of length 512 |
| **Batch Size (VRAM constrained)** | 16 sequences (8,192 tokens/batch) | Peak activation VRAM: ~2.1 GB $\le$ 4.0 GB limit |
| **Gradient Accumulation** | 2 steps (effective batch: 32) | Stabilizes AdamW variance |
| **Steps per Epoch** | ~1,554 optimizer steps | Batch size 32 = 16,384 tokens/step |
| **GTX 1650 Throughput (estimated)** | ~2,500 – 3,500 tokens/second | Based on SDPA FP16 benchmark on Turing SM 7.5 |
| **Training Duration per Epoch** | ~2.0 – 2.8 hours | 25.5M tokens / 3,000 tok/sec $\approx$ 8,500 seconds |
| **Target Pretraining Run (3 epochs)** | ~6.0 – 8.5 hours | Feasible as an overnight local training job |
| **Thermal & Power Footprint** | 75W PCIe slot limit | No risk of thermal throttling or auxiliary power failure |

---

## 10. Automated Test Suite Verification

The automated test suite in `F:\LOVE\native_ai\tests` was executed against Python 3.11 using pytest.

```
============================= test session starts =============================
platform win32 -- Python 3.11.16, pytest-9.2.0, pluggy-1.7.0
rootdir: F:\LOVE, configfile: pyproject.toml
plugins: anyio-4.16.0
collected 52 items

native_ai/tests/test_architecture.py::test_configuration_validation PASSED [  1%]
native_ai/tests/test_architecture.py::test_embedding_output_shape_and_bounds PASSED [  3%]
native_ai/tests/test_architecture.py::test_rmsnorm_stability PASSED      [  5%]
native_ai/tests/test_architecture.py::test_rope_dimensions_and_rotation PASSED [  7%]
native_ai/tests/test_architecture.py::test_swiglu_dimensions PASSED      [  9%]
native_ai/tests/test_architecture.py::test_causal_self_attention_shape_and_sdpa PASSED [ 11%]
native_ai/tests/test_architecture.py::test_causal_masking_future_token_leakage_prevention PASSED [ 13%]
native_ai/tests/test_architecture.py::test_transformer_block_residual_connections PASSED [ 15%]
native_ai/tests/test_architecture.py::test_tied_input_output_embeddings PASSED [ 17%]
native_ai/tests/test_architecture.py::test_loss_calculation_and_gradient_finiteness PASSED [ 19%]
native_ai/tests/test_architecture.py::test_adamw_optimizer_step PASSED   [ 21%]
native_ai/tests/test_architecture.py::test_cpu_execution PASSED          [ 23%]
native_ai/tests/test_architecture.py::test_cuda_execution PASSED         [ 25%]
native_ai/tests/test_dataset_pipeline.py::test_source_registry_and_license_validation PASSED [ 26%]
native_ai/tests/test_dataset_pipeline.py::test_text_cleaning_rules PASSED [ 28%]
native_ai/tests/test_dataset_pipeline.py::test_privacy_filter_redaction_and_rejection PASSED [ 30%]
native_ai/tests/test_dataset_pipeline.py::test_deduplication_exact_normalized_and_near PASSED [ 32%]
native_ai/tests/test_dataset_pipeline.py::test_deterministic_splitting_and_zero_cross_split_leakage PASSED [ 34%]
native_ai/tests/test_dataset_pipeline.py::test_streaming_ingestion_generator PASSED [ 36%]
native_ai/tests/test_dataset_pipeline.py::test_tokenizer_compatibility_on_splits PASSED [ 38%]
native_ai/tests/test_dataset_pipeline.py::test_source_provenance_validation PASSED [ 40%]
native_ai/tests/test_dataset_pipeline.py::test_license_evidence_completeness PASSED [ 42%]
native_ai/tests/test_dataset_pipeline.py::test_missing_source_attribution PASSED [ 44%]
native_ai/tests/test_dataset_pipeline.py::test_incorrect_document_split_percentages PASSED [ 46%]
native_ai/tests/test_dataset_pipeline.py::test_token_count_reporting PASSED [ 48%]
native_ai/tests/test_dataset_pipeline.py::test_group_level_leakage PASSED [ 50%]
native_ai/tests/test_dataset_pipeline.py::test_reproducible_source_manifests PASSED [ 51%]
native_ai/tests/test_dataset_pipeline.py::test_insufficient_validation_test_sample_warnings PASSED [ 53%]
native_ai/tests/test_dataset_pipeline.py::test_storage_capacity_estimation PASSED [ 55%]
native_ai/tests/test_dataset_pipeline.py::test_external_download_integrity_and_revision_pinning PASSED [ 57%]
native_ai/tests/test_dataset_pipeline.py::test_license_manifest_preservation PASSED [ 59%]
native_ai/tests/test_dataset_pipeline.py::test_parquet_dataset_parsing PASSED [ 61%]
native_ai/tests/test_dataset_pipeline.py::test_oasst1_english_filtering_and_tree_integrity PASSED [ 63%]
native_ai/tests/test_dataset_pipeline.py::test_gsm8k_train_test_separation PASSED [ 65%]
native_ai/tests/test_dataset_pipeline.py::test_tinystories_validation_preservation PASSED [ 67%]
native_ai/tests/test_dataset_pipeline.py::test_cross_split_zero_leakage_expanded PASSED [ 69%]
native_ai/tests/test_dataset_pipeline.py::test_tokenizer_compatibility_on_expanded_corpus PASSED [ 71%]
native_ai/tests/test_dataset_pipeline.py::test_storage_budget_enforcement PASSED [ 73%]
native_ai/tests/test_tokenizer.py::test_vocab_size_and_special_tokens PASSED [ 75%]
native_ai/tests/test_tokenizer.py::test_encode_decode_round_trip PASSED  [ 76%]
native_ai/tests/test_tokenizer.py::test_empty_and_whitespace_text PASSED [ 78%]
native_ai/tests/test_tokenizer.py::test_case_preservation PASSED         [ 80%]
native_ai/tests/test_tokenizer.py::test_punctuation_and_symbols PASSED   [ 82%]
native_ai/tests/test_tokenizer.py::test_numbers_and_formatting PASSED    [ 84%]
native_ai/tests/test_tokenizer.py::test_urls_and_identifiers PASSED      [ 86%]
native_ai/tests/test_tokenizer.py::test_unicode_and_uncommon_characters PASSED [ 88%]
native_ai/tests/test_tokenizer.py::test_repeated_text_and_long_input PASSED [ 90%]
native_ai/tests/test_tokenizer.py::test_special_token_boundaries_and_chat_template PASSED [ 92%]
native_ai/tests/test_tokenizer.py::test_save_and_reload_equivalence PASSED [ 94%]
native_ai/tests/test_tokenizer.py::test_deterministic_encoding PASSED    [ 96%]
native_ai/tests/test_tokenizer.py::test_batch_encode_padding_and_truncation PASSED [ 98%]
native_ai/tests/test_tokenizer.py::test_transformer_integration_compatibility PASSED [100%]

======================= 52 passed, 2 warnings in 23.71s =======================
```

**Test Summary:**
- Architecture Module (`test_architecture.py`): 13/13 passed
- Dataset Pipeline Module (`test_dataset_pipeline.py`): 25/25 passed
- Tokenizer Module (`test_tokenizer.py`): 14/14 passed
- **Total:** **52 / 52 automated tests passed (100% pass rate)**

---

## 11. Pretraining Readiness Recommendation & Next Steps

### Formal Recommendation:
```
================================================================================
  PRETRAINING READINESS DECISION: BLOCKED
================================================================================
```

### Rationale:
1. **Corpus Volume Condition Met:** The training dataset contains **25,467,894 clean tokens** (exceeding Scenario B target of 20M tokens).
2. **Evaluation Set Condition Met:** The evaluation split has expanded to **4,223 documents** (1.65M tokens) with zero cross-split leakage and preserved official benchmarks.
3. **Storage Condition Met:** Free space on disk `F:` is **4.367 GB**, well above the 2.0 GB reserve threshold.
4. **Governing Rule Enforcement:** Under the critical rules of Phase NAI-03.2, model pretraining is strictly prohibited until Phase NAI-04 is formally approved and initiated.

### Prerequisites for Phase NAI-04:
- [ ] User review and acceptance of `NAI_03_2_DATASET_ACQUISITION_AUDIT.md`.
- [ ] Formal authorization to begin **Phase NAI-04: Pretraining Engine, Mixed-Precision Pipeline & Checkpoint Manager**.
- [ ] Implementation of memory-mapped binary sequence caching (`.bin` / `.npy` token streams) to eliminate on-the-fly string tokenization overhead during GPU training.
- [ ] Implementation of a domain-weighted DataLoader to balance `english_synthetic_stories` (53.7%), `instruction_dialog` (32.9%), and `reasoning_math` (13.4%).
- [ ] Implementation of gradient checkpointing and mixed-precision (FP16 AMP) training loop with AdamW optimizer and cosine learning rate scheduler.
- [ ] Implementation of an atomic checkpoint manager with rollback and disk-space pre-check routines to ensure training checkpoints do not exceed the remaining 4.36 GB on disk `F:`.
