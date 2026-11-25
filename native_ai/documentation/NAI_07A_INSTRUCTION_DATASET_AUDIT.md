# LOVE Native AI — Phase NAI-07A: Instruction Dataset Preparation & Training-Readiness Audit

**Project:** `F:\LOVE\native_ai`  
**Phase:** NAI-07A (Supervised Fine-Tuning Dataset Preparation & Pipeline Audit)  
**Starting Model Checkpoint:** `checkpoints/step_0000250.pt` (`love-native-tiny`, 5,507,328 parameters)  
**Date:** 2026-11-24  
**Status:** **PASS** (100% Pipeline Readiness Confirmed)  
**Automated Tests:** 90 / 90 tests passing (100%) in 31.33s  
**Storage Headroom:** 3.963 GB free on drive `F:` (Safety threshold $\ge 2.0\text{ GB}$)  

---

## Executive Summary

Phase NAI-07A successfully established the complete, reproducible, and mathematically rigorous instruction dataset engineering pipeline and Supervised Fine-Tuning (SFT) infrastructure for the LOVE Native AI architecture.

Starting from approved, permissively-licensed local sources (**OpenAssistant OASST1**, **OpenAI GSM8K**, and the **LOVE Curated Seed Corpus**), the pipeline extracted conversation candidates, reconstructed tree paths, applied quality filtering and PII sanitization, enforced context-window truncation safety, and generated deterministic, group-isolated dataset splits.

### Core Achievements

1. **Instruction Corpus Scale & Scope:**  
   Processed **17,021 candidate conversations**, admitting **13,716 high-quality instruction examples** grouped across **10,053 unique conversation trees**, representing **2,712,961 supervised assistant target tokens** ($4,341,793$ total tokens emitted).
2. **LOVE Instruction Format v1.0.0:**  
   Implemented a standardized conversation schema supporting system messages, multi-turn dialogues, role alternation validation, and turn-boundary markers without modifying the tokenizer vocabulary or adding new token IDs.
3. **Mathematically Strict Assistant-Only Loss Masking:**  
   Implemented causal next-token label alignment ($S[:-1] \to S[1:]$) with strict $-100$ masking across all system prompts, user turns, and role headers. Assistant response tokens and concluding `<eos>` tokens are the sole active targets. Automated tests prove that masked positions produce strictly **$0.000000$ gradient norm**.
4. **Group-Aware Tree Split Isolation:**  
   Partitioned data by conversation tree ID into Train (85%), Validation (10%), and an Evaluation Holdout Test split (5%). Automated assertions confirmed **zero tree leakage** and **zero content-hash leakage** across all three split pairs.
5. **Dry-Run Forward Pass Verification:**  
   Executed a forward pass using the pretrained `step_0000250.pt` checkpoint on CUDA. The model produced a finite loss of **5.1160** with 41.5% active targets. Bitwise comparison of all 38 parameter tensors before and after the forward pass confirmed **zero weight mutation** ($\Delta W = 0.0000000000$).
6. **Zero External API / Cloud Dependencies:**  
   Entire pipeline operated strictly locally on drive `F:`. Zero Git operations were performed.

---

## 1. Audit of Existing Instruction Data Sources

The raw external datasets and seed corpus stored in `F:\LOVE\native_ai\datasets\raw` were systematically audited:

### 1.1 Source Provenance & Licensing

| Source Name | Upstream Repository | Local File Path | License | Intended Role |
| :--- | :--- | :--- | :--- | :--- |
| **OpenAssistant OASST1** | `OpenAssistant/oasst1` | `datasets/raw/external/oasst1/` | Apache-2.0 | Multi-turn instruction dialogue, general Q&A, safety boundaries |
| **GSM8K** | `openai/gsm8k` | `datasets/raw/external/gsm8k/train.parquet` | MIT | Multi-step mathematical reasoning and arithmetic chain-of-thought |
| **LOVE Seed Corpus** | Native Project Seed | `datasets/raw/*.jsonl` | CC0-1.0 | Core persona fixtures, structured output, system task benchmarks |

### 1.2 OASST1 Raw Data & Filtering Telemetry

- **Total Raw Messages in Parquet:** 88,838 messages
- **Language Distribution:**
  - English (`en`): 41,305 messages (46.5%)
  - Spanish (`es`): 23,975 messages (27.0%)
  - Russian (`ru`): 7,611 messages (8.6%)
  - Chinese (`zh`): 3,448 messages (3.9%)
  - German (`de`): 3,195 messages (3.6%)
  - Other 35 languages: 9,304 messages (10.4%)
- **Roles in Raw Parquet:** Assistant (55,668), Prompter (33,170)
- **Quality, Toxicity & Safety Filtering:**
  - Soft-deleted messages: 1,553 rejected
  - Unreviewed / failed human review: 2,066 rejected
  - PII flagged ($>0.5$): 13 rejected
  - Spam flagged ($>0.5$): 956 rejected
  - Toxic / Hate speech flagged ($>0.5$): 572 rejected
- **Clean English Messages Retained:** 39,334 messages across **3,683 unique conversation trees**
- **Conversation Path Reconstruction:**
  - Trees yielding valid alternating paths: 3,517 trees
  - Total reconstructable paths: 13,887 paths
  - Turn depth distribution:
    - 1 turn (2 messages: user $\to$ assistant): 3,257 paths (23.5%)
    - 2 turns (4 messages: user $\to$ asst $\to$ user $\to$ asst): 10,240 paths (73.7%)
    - 3 turns (6 messages: user $\to$ asst $\to$ user $\to$ asst $\to$ user $\to$ asst): 390 paths (2.8%)
  - *Branch Capping:* To prevent oversampling branches from dense trees, the pipeline selected up to 3 paths per tree (shortest, median, longest), admitting **9,520 high-diversity OASST1 candidates**.

### 1.3 GSM8K Raw Data

- **Total Training Problems:** 7,473 problems in `train.parquet`
- **Valid Question-Answer Pairs:** 7,473 (100.0%)
- **Target Formatting:** Each problem was mapped to an instruction pair:
  - User: `"Solve the following math word problem step-by-step:\n\n{question}"`
  - Assistant: `"Step-by-step Solution:\n{answer}"`
- **Tree Grouping:** Each problem assigned an isolated tree ID (`gsm8k_prob_{idx:05d}`).

### 1.4 Seed Corpus Tasks & Deduplication

- `instruction_dialog.jsonl`: 21 raw lines $\to$ 3 unique multi-turn dialogues (7× duplicate expansion in seed corpus)
- `structured_tasks.jsonl`: 10 raw lines $\to$ 2 unique structured extraction tasks (5× duplicate expansion)
- `reasoning_math.jsonl`: 20 raw lines $\to$ 20 unique problem instances (1× duplicate expansion)
- `technical_code.jsonl`: 16 raw lines $\to$ 3 unique algorithmic explanations, 1 test fixture containing an RSA private key (`fixture_secret_01`)
- **Deduplication:** Exact content-hash deduplication reduced seed candidates to 28 records. `fixture_secret_01` was detected and strictly rejected by the privacy filter.

---

## 2. LOVE Instruction Format Specification (v1.0.0)

The LOVE instruction dataset schema is designed for autoregressive language models, preserving conversation history while supporting metadata tracking.

### 2.1 Special Token Vocabulary Mapping

No special tokens were added, and the tokenizer vocabulary remained unmodified at exactly **8,192 tokens**:

```
+--------------------+----------+------------------------------------------------------+
| Token String       | Token ID | Semantic Function                                    |
+--------------------+----------+------------------------------------------------------+
| <pad>              |    0     | Batch padding token (always ignored with target=-100) |
| <unk>              |    1     | Unknown token fallback                               |
| <bos>              |    2     | Beginning of sequence marker                         |
| <eos>              |    3     | End of turn and end of sequence delimiter            |
| <|system|>         |    4     | System persona message header                        |
| <|user|>           |    5     | User conversational turn header                      |
| <|assistant|>      |    6     | Assistant response turn header                       |
| <|tool|>           |    7     | Reserved for tool-use execution                      |
+--------------------+----------+------------------------------------------------------+
```

### 2.2 Text Serialization

A complete dialogue is serialized into a deterministic string representation using explicit turn tags and `<eos>` delimiters:

$$\text{Sequence} = \texttt{<\|system\|>}\{\text{system\_prompt}\}\texttt{<eos><\|user\|>}\{\text{user\_query}\}\texttt{<eos><\|assistant\|>}\{\text{response}\}\texttt{<eos>}$$

For multi-turn dialogues, additional user-assistant pairs append sequentially:

$$\dots \texttt{<\|user\|>}\{\text{turn\_2\_query}\}\texttt{<eos><\|assistant\|>}\{\text{turn\_2\_response}\}\texttt{<eos>}$$

### 2.3 Structural Validation Rules

The `LOVEInstructionFormatter.validate_conversation` engine enforces strict structural invariants:
1. Conversation must have $\ge 2$ messages.
2. System message, if present, must occupy index 0.
3. First conversational turn must be `user`.
4. Last message must be `assistant`.
5. Message roles must strictly alternate: $\text{user} \to \text{assistant} \to \text{user} \to \text{assistant}$.
6. Message contents must be non-empty strings.

---

## 3. SFT Loss Masking & Causal Alignment

In supervised fine-tuning, training on prompt tokens causes the model to memorize prompts rather than learning instruction-following dynamics. The LOVE SFT pipeline implements mathematically rigorous **assistant-only loss masking**.

### 3.1 Causal Shift and Target Label Construction

For an input sequence $S = [t_0, t_1, \dots, t_{N}]$, autoregressive next-token prediction shifts inputs and targets by 1 position:
- **Inputs:** $I = [t_0, t_1, \dots, t_{N-1}]$
- **Targets:** $T = [L_1, L_2, \dots, L_{N}]$

Where the label array $L$ is constructed as:

$$L_k = \begin{cases} -100 & \text{if } t_k \text{ belongs to system prompt, user prompt, or role header} \\ -100 & \text{if } t_k \text{ is a padding token } (\texttt{<pad>}) \\ t_k & \text{if } t_k \text{ belongs to assistant response content} \\ 3 & \text{if } t_k \text{ is the concluding } \texttt{<eos>} \text{ of an assistant turn} \end{cases}$$

### 3.2 Token-Level Alignment Diagram

```
Token Index:    0           1       2       3       4           5   6   7   8       9       10      11      12          13  14  15
full_tokens:   [<|system|>, Y,      ou,     ...,    <eos>,      <|user|>,  H,  i,  <eos>,  <|assistant|>,  I,      'm,     LOVE,   <eos>]
full_labels:   [-100,       -100,   -100,   ...,    -100,       -100,      -100, -100, -100,   -100,   ID_I,   ID_'m,  ID_LOVE, 3   ]

After 1-Token Causal Shift:
Inputs ([:-1]): [<|system|>, Y,      ou,     ...,    <eos>,      <|user|>,  H,  i,  <eos>,  <|assistant|>,  I,      'm,     LOVE]
Targets ([1:]): [-100,       -100,   -100,   ...,    -100,       -100,      -100, -100, -100,   ID_I,   ID_'m,  ID_LOVE, 3  ]
Loss Weight:     0.0         0.0     0.0     0.0     0.0         0.0        0.0  0.0  0.0     1.0     1.0     1.0     1.0
```

- When the model processes `<|assistant|>`, the target is `ID_I` (loss is active; model learns to initiate response).
- When the model processes `LOVE`, the target is `3` (`<eos>`, loss is active; model learns when to terminate response).
- When the model processes user or system tokens, target is `-100` (zero loss, zero gradient).

### 3.3 Gradient Isolation Proof

Automated test `test_zero_gradient_on_masked_positions` in `tests/test_sft_pipeline.py` verifies this mathematically:
$$\forall i \in \{i \mid T_i = -100\}, \quad \frac{\partial \mathcal{L}}{\partial z_i} = \mathbf{0.000000}$$
$$\forall i \in \{i \mid T_i \neq -100\}, \quad \left\|\frac{\partial \mathcal{L}}{\partial z_i}\right\| > 0$$

All positions with target $-100$ contribute strictly zero loss and zero gradient to backpropagation.

### 3.4 Context Window & Truncation Safety

Autoregressive models have a fixed context window ($512$ tokens for `love-native-tiny`).
- **Multi-Turn Sliding Window:** If a multi-turn conversation exceeds 512 tokens, older conversation turn pairs are progressively dropped from the left. The system prompt and the final turn pair (last user query + last assistant response) are strictly preserved.
- **Immediate Turn Pair Safety Check:** If even the system prompt plus a single user-assistant turn exceeds 512 tokens, partial truncation would corrupt the prompt or truncate the assistant target mid-sentence. The pipeline raises `TruncationSafetyError` and rejects the example during pre-filtering. Exactly **3,293 oversized examples** were safely rejected.

---

## 4. Dataset Splits & Leakage Prevention

To prevent conversation content and phrasing leakage between training and evaluation, splitting was performed at the **conversation tree level**.

### 4.1 Split Distribution

```
Total Admitted Trees: 10,053 unique conversation trees
├── SFT Train Split:      8,545 trees (85.00%) -> 11,639 examples (2,297,475 target tokens)
├── SFT Validation Split: 1,005 trees (10.00%) ->  1,387 examples (  274,979 target tokens)
└── SFT Test Split:         503 trees ( 5.00%) ->    690 examples (  140,507 target tokens)
```

### 4.2 Leakage Verification Results

Pairwise intersections were calculated across all three splits:

| Pairwise Comparison | Tree ID Intersection | Content Hash Intersection | Leakage Status |
| :--- | :---: | :---: | :---: |
| **Train $\cap$ Validation** | $\emptyset$ (0) | $\emptyset$ (0) | **CLEAN** |
| **Train $\cap$ Test** | $\emptyset$ (0) | $\emptyset$ (0) | **CLEAN** |
| **Validation $\cap$ Test** | $\emptyset$ (0) | $\emptyset$ (0) | **CLEAN** |

- Zero conversation trees cross split boundaries.
- Zero exact or normalized text hashes cross split boundaries.
- The SFT test split (`sft_test.jsonl`) is physically quarantined as a held-out benchmark and will not be accessed during SFT training or hyperparameter tuning.
- The pretraining test split (`datasets/splits/test/test.jsonl`) remains completely separate and untouched.

### 4.3 Split Manifest and Checksums

All split files and the master manifest are persisted in `F:\LOVE\native_ai\datasets\sft\`:

| Split File | Record Count | Target Tokens | Total Tokens | File Size | SHA-256 Checksum |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `sft_train.jsonl` | 11,639 | 2,297,475 | 3,682,862 | 18,191,983 B | `bf11ca1db109d5a608729e4c0c083280633b8fc03e286274b54bffefab004d54` |
| `sft_val.jsonl` | 1,387 | 274,979 | 438,343 | 2,126,905 B | `a08ee39e28555fb54a8948bd12a2abbb26dede71b776709ef52bb685e95dba99` |
| `sft_test.jsonl` | 690 | 140,507 | 220,588 | 1,097,037 B | `e2cfd6b10c6151d15a167227ca3d17d95a28d669689017ddd97694d397b89a87` |
| `sft_manifest.json` | — | — | — | 3,115 B | Master manifest in `datasets/sft/manifests/` |

---

## 5. Dataset Balance & Capability Analysis

Each conversation was analyzed by semantic intent and classified into one of the 6 core LOVE assistant capabilities:

### 5.1 Category Distribution Across Splits

```
+------------------------------------------------------------------------------------------------+
| Category                     | Train Examples | Val Examples | Test Examples | Total Admitted  |
+------------------------------------------------------------------------------------------------+
| reasoning_mathematics        |  6,099 (52.4%) |  696 (50.2%) |   356 (51.6%) |  7,151 (52.1%)  |
| general_conversation         |  4,279 (36.8%) |  554 (39.9%) |   245 (35.5%) |  5,078 (37.0%)  |
| instruction_following        |    799  (6.9%) |   86  (6.2%) |    48  (7.0%) |    933  (6.8%)  |
| safe_refusal                 |    259  (2.2%) |   32  (2.3%) |    29  (4.2%) |    320  (2.3%)  |
| writing_summarization        |    135  (1.2%) |    5  (0.4%) |     8  (1.2%) |    148  (1.1%)  |
| structured_output            |     68  (0.6%) |   14  (1.0%) |     4  (0.6%) |     86  (0.6%)  |
+------------------------------------------------------------------------------------------------+
| Total Examples               | 11,639 (100.0%)| 1,387 (100.0%)|   690 (100.0%)| 13,716 (100.0%) |
+------------------------------------------------------------------------------------------------+
```

### 5.2 Turn Depth Distribution

- **1-Turn Conversations (User $\to$ Assistant):** 8,749 examples (63.8%)
- **2-Turn Conversations (User $\to$ Asst $\to$ User $\to$ Asst):** 4,752 examples (34.6%)
- **3-Turn Conversations (User $\to$ Asst $\to$ User $\to$ Asst $\to$ User $\to$ Asst):** 215 examples (1.6%)

The dataset provides a balanced blend of single-turn direct problem solving and multi-turn conversational context tracking.

### 5.3 Transparent Gap Analysis: Coding Data

In compliance with project directives:
- **Current Coverage:** Coding is currently covered only through general conversational programming Q&A in OASST1 (debugging, conceptual explanations) and 3 algorithmic seed fixtures.
- **Identified Gap:** The approved corpus contains **no dedicated software engineering or repository-level programming dataset** (such as StarCoder, The Stack, or HumanEval).
- **Recommendation:** Do not attempt to synthesize fake code data. If production-grade coding capability is desired in future phases, explicitly acquire an approved, permissively-licensed code corpus (e.g., `bigcode/the-stack-smol` or `codeparrot/github-jupyter`) under a separate user authorization gate.

---

## 6. SFT Pipeline Readiness & Dry-Run Verification

### 6.1 SFT DataLoader Infrastructure

Implemented in `native_ai/datasets/sft/dataloader.py`:
- `SFTDataset`: Efficient PyTorch `Dataset` loading JSONL splits and pre-encoding shifted token pairs.
- `SFTCollator`: Dynamic batch padding to batch-max length, setting `input_ids = 0` and `targets = -100` on pad tokens.
- `SFTDataLoader`: Deterministic PyTorch `DataLoader` with fixed seed support.

### 6.2 Pretrained Checkpoint Dry-Run Forward Pass

Executed on `checkpoints/step_0000250.pt` on the local GTX 1650:
- **Loaded Parameters:** 5,507,328 parameters (Step 250)
- **Batch Specification:** 2 sequences collated to length 418 (836 total tokens)
- **Token Accounting:**
  - Masked Tokens (Prompt + Padding): 489 tokens (58.5%)
  - Supervised Target Tokens: 347 tokens (41.5%)
- **Model Output:**
  - Logits shape: `[2, 418, 8192]`
  - Cross-entropy loss: **5.1160** (finite, zero NaN/Inf)
- **Immutability Check:**
  - Initial Parameter State Hash: `67a1941241322979...`
  - Final Parameter State Hash: `67a1941241322979...`
  - Disk Checkpoint SHA-256: `dca206cbf535847ff6ccd58d80fb118c0e774ad2b44438edf7dcc96673743145` (Unchanged)
  - Parameter Shift: $\Delta W = \mathbf{0.0000000000}$

---

## 7. Automated Test Suite Results

The full test suite was executed using the isolated `pytest.ini` configuration:

```
platform win32 -- Python 3.11.16, pytest-9.2.0, pluggy-1.7.0
rootdir: F:\LOVE\native_ai
configfile: pytest.ini
plugins: anyio-4.16.0
collected 90 items

native_ai\tests\test_architecture.py .............                       [ 14%]
native_ai\tests\test_dataset_pipeline.py .........................       [ 42%]
native_ai\tests\test_sft_pipeline.py ................                    [ 60%]
native_ai\tests\test_tokenizer.py ..............                         [ 75%]
native_ai\tests\test_training_engine.py ......................           [100%]

============================= 90 passed in 31.33s =============================
```

All 90 unit tests passed with 0 failures, 0 errors, and 0 warnings.

---

## 8. Training-Readiness Gate Decision

| Readiness Evaluation Criteria | Required Condition | Actual Observed Result | Status |
| :--- | :--- | :--- | :---: |
| **Dataset Completeness** | High-quality multi-source SFT dataset | 13,716 examples across 10,053 trees | **PASS** |
| **Format Compliance** | Standardized role markers & delimiters | Schema v1.0.0 validated across all splits | **PASS** |
| **Loss Masking Integrity** | Prompt & pad targets masked to -100 | Verified; zero gradient on masked positions | **PASS** |
| **Split Isolation** | Zero tree & content leakage | Tree $\cap = \emptyset$, Hash $\cap = \emptyset$ | **PASS** |
| **Context Window Safety** | No truncated prompts or targets | Oversized examples rejected cleanly | **PASS** |
| **Pretrained Model Safety** | Zero weight mutation during dry-run | $\Delta W = 0.0000000000$, SHA unchanged | **PASS** |
| **Storage Headroom** | Drive `F:` free space $\ge 2.0\text{ GB}$ | 3.963 GB free on drive `F:` | **PASS** |
| **Test Suite Coverage** | 100% passing automated regression suite | 90 / 90 tests passed in 31.33s | **PASS** |

### Final Phase Decision: **PASS**

The instruction dataset engineering pipeline and SFT execution infrastructure are verified and fully ready for supervised fine-tuning.

In strict adherence to project boundaries:
- Zero optimizer steps were executed.
- Zero model weights were mutated.
- Model checkpoint `step_0000250.pt` remains unmodified.
- SFT training will not begin without explicit authorization for **Phase NAI-07B**.
