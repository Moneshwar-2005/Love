# LOVE Native AI — Phase NAI-07B: Controlled Supervised Fine-Tuning Pilot Report

**Project:** `F:\LOVE\native_ai`  
**Phase:** NAI-07B (Controlled Supervised Fine-Tuning Pilot)  
**Experiment ID:** `exp_nai07b_sft_pilot_001`  
**Starting Model Checkpoint:** `checkpoints/step_0000250.pt` (`love-native-tiny`, 5,507,328 parameters)  
**Date:** 2026-11-24  
**Final Decision:** **PASS** (Controlled Pilot Objectives & Integrity Constraints Fully Satisfied)  
**Automated Tests:** 100 / 100 tests passing (100%) in 34.32s  
**Storage Headroom:** 3.695 GB free on drive `F:` (Safety threshold $\ge 2.0\text{ GB}$)  

---

## Executive Summary

Phase NAI-07B successfully executed LOVE's first controlled Supervised Fine-Tuning (SFT) pilot experiment on the `love-native-tiny` architecture using the approved NAI-07A instruction dataset.

Training was performed locally on an NVIDIA GeForce GTX 1650 4GB GPU under strict single-process isolation, zero external API access, and zero modification to historical pretraining artifacts.

### Key Milestones & Quantitative Findings

1. **Strict Monotonic Validation Loss Reduction:**  
   Evaluated every 10 steps on a deterministic 50-batch subset of `sft_val.jsonl`, validation loss decreased monotonically from an initial baseline of **5.0205** (Perplexity: **151.49**) down to **4.6578** (Perplexity: **105.40**), representing an absolute reduction of **-0.3627 nats (-7.2%)** and a **$30.4\%$ reduction in perplexity**.
2. **Complete Integrity Gate Compliance:**  
   All 10 pre-training integrity gates passed before the first optimizer step. The starting checkpoint (`step_0000250.pt`) was confirmed bitwise unchanged post-training ($\Delta W = 0.0000000000$, SHA-256 verified).
3. **Hardware Efficiency on GTX 1650:**  
   The 100-step pilot executed in **12.71 seconds** (~127.1 ms/step), processing **39,437 supervised target tokens** at an average throughput of **3,102.6 tokens/sec**. Peak VRAM reserved was **322.0 MB** (<8% of GPU capacity), leaving $>3,700\text{ MB}$ of safe headroom.
4. **Checkpoint & Metadata Isolation:**  
   All experimental artifacts, metrics logs, and checkpoints (`sft_step_0000000.pt`, `sft_step_0000050.pt`, `sft_step_0000100.pt`, `sft_best.pt`, `sft_latest.pt`) were persisted atomically into `experiments/nai_07b_sft_pilot/checkpoints/` with companion SHA-256 `.json` sidecars.
5. **Automated Unit Regression:**  
   The complete native AI test suite expanded to **100 tests**, achieving a **100% pass rate** (0 failures, 0 errors, 0 warnings).

---

## 1. Pre-Training Integrity Gate

Before executing any optimizer steps or backward passes, the 10-point integrity gate was evaluated and verified:

| Gate Check | Specification / Target | Observed Result | Status |
| :--- | :--- | :--- | :---: |
| **1. Starting Checkpoint** | `checkpoints/step_0000250.pt` exists and matches SHA-256 | `dca206cbf535847ff6ccd58d80fb118c0e774ad2b44438edf7dcc96673743145` | **PASS** |
| **2. Manifest Validation** | `datasets/sft/manifests/sft_manifest.json` valid | Schema v1.0.0, format verified | **PASS** |
| **3. Split File Checksums** | `sft_train.jsonl` & `sft_val.jsonl` match manifest | `bf11ca1d...` and `a08ee39e...` confirmed | **PASS** |
| **4. Test Split Quarantine** | `sft_test.jsonl` physically isolated from loader | 690 examples strictly quarantined | **PASS** |
| **5. Group/Tree Isolation** | Zero tree & content overlap across all 3 split pairs | $\text{Tree} \cap = \emptyset$, $\text{Hash} \cap = \emptyset$ | **PASS** |
| **6. Tokenizer & Vocab** | Vocabulary size 8,192 matches architecture | 8,192 tokens confirmed | **PASS** |
| **7. Loss Masking Verification**| Prompt & pad masked to -100, assistant tokens active | Validated; concluding `<eos>` = 3 | **PASS** |
| **8. Hardware Safeguards** | NVIDIA GTX 1650 4GB available with safe VRAM | Detected, 0 MB initial reserved | **PASS** |
| **9. Disk Space Reserve** | Free storage on drive `F:` $\ge 2.0\text{ GB}$ | 3.962 GB free | **PASS** |
| **10. Baseline Loss Record** | Deterministic 50-batch subset validation loss | $\mathcal{L}_0 = 5.0205$, $\text{PPL}_0 = 151.49$ | **PASS** |

---

## 2. Pilot Training Configuration

The experiment was conducted with conservative, numerically stable parameters:

- **Model Architecture:** `love-native-tiny` (4 layers, 4 heads, 256 hidden dim, 768 FFN dim, SwiGLU, RoPE, RMSNorm, tied embeddings)
- **Parameter Count:** 5,507,328 parameters (all trainable)
- **Precision:** Strict FP32 (Pure float32 execution)
- **Optimizer:** AdamW ($\beta_1 = 0.9$, $\beta_2 = 0.95$, $\epsilon = 1.0\times 10^{-8}$, weight decay $= 0.01$)
- **Learning Rate Schedule:** Linear warmup for 5 steps to peak lr $= 2.0\times 10^{-5}$, followed by cosine decay over 95 steps to min lr $= 2.0\times 10^{-6}$
- **Gradient Clipping:** Max norm $1.0$
- **Batching Parameters:**
  - Micro-batch size: 1 sequence
  - Gradient accumulation steps: 2
  - Effective batch size: 2 sequences
  - Sequence context length: 512 tokens
- **Loss Function:** Causal cross-entropy with assistant-only masking:
  $$\mathcal{L} = -\frac{1}{M} \sum_{i \in \text{Assistant Tokens}} \ln p(y_i \mid x_{<i})$$
  *(All system prompts, user turns, and batch padding tokens receive target $-100$ and are strictly excluded from the loss calculation).*
- **Maximum Optimizer Steps:** 100 steps (200 micro-steps total)

---

## 3. Validation & Training Progression

Validation was evaluated every 10 optimizer steps against the fixed 50-batch validation subset under `torch.no_grad()`.

### 3.1 Loss Progression Table

| Optimizer Step | Learning Rate | Train Loss | Grad Norm | Validation Loss | Validation Perplexity | Relative $\Delta \mathcal{L}$ |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0 (Baseline)** | `0.00e+00` | — | — | **5.0205** | **151.49** | Baseline |
| **10** | `1.99e-05` | 5.6539 | 1.775 | **4.9398** | **139.74** | -1.61% |
| **20** | `1.89e-05` | 5.8286 | 2.570 | **4.8585** | **128.84** | -3.23% |
| **30** | `1.71e-05` | 5.3208 | 2.083 | **4.7986** | **121.34** | -4.42% |
| **40** | `1.46e-05` | 4.6293 | 2.966 | **4.7543** | **116.09** | -5.30% |
| **50** | `1.17e-05` | 4.5600 | 2.962 | **4.7177** | **111.91** | -6.03% |
| **60** | `8.80e-06` | 4.5371 | 2.554 | **4.6946** | **109.36** | -6.49% |
| **70** | `6.10e-06` | 5.3335 | 2.320 | **4.6787** | **107.63** | -6.81% |
| **80** | `3.90e-06` | 5.4223 | 2.488 | **4.6709** | **106.80** | -6.96% |
| **90** | `2.50e-06` | 4.9225 | 2.048 | **4.6625** | **105.90** | -7.13% |
| **100** | `2.00e-06` | 4.5246 | 2.406 | **4.6578** | **105.40** | **-7.22%** |

### 3.2 Key Observations on the Loss Curve

1. **Monotonic Descent:** Validation loss decreased at every evaluation interval without a single reversal.
2. **Smooth Convergence:** The cosine decay schedule allowed the learning rate to taper smoothly from $2.0\times 10^{-5}$ down to $2.0\times 10^{-6}$, dampening gradient variance as the loss stabilized around 4.65.
3. **Zero Degradation:** At no point did validation loss exceed the degradation safety threshold ($>20\%$ above baseline $= 6.0246$).
4. **Best Model:** `sft_best.pt` was captured at Step 100 with a validation loss of **4.6578**.

---

## 4. Hardware Telemetry & Performance Analysis

| Metric | Measured Value | Operational Safeguard Limit | Margin / Headroom |
| :--- | :---: | :---: | :---: |
| **Total Wall-Clock Training Time** | 12.71 seconds | — | Completed in <15s |
| **Average Step Latency** | 127.11 ms / step | — | ~7.87 optimizer steps/s |
| **Target Tokens Trained** | 39,437 tokens | — | — |
| **Training Throughput** | 3,102.6 tokens / sec | — | Highly optimized on FP32 |
| **Peak VRAM Allocated** | 159.34 MB | — | <4% of GPU memory |
| **Peak VRAM Reserved** | 322.0 MB | 3,500.0 MB | **3,178.0 MB safe headroom** |
| **Final Free Disk Space** | 3.695 GB | 2.000 GB | **1.695 GB safety margin** |

---

## 5. Checkpoint & Immutability Verification

All checkpoint artifacts and sidecars were saved in `experiments/nai_07b_sft_pilot/checkpoints/`:

```
experiments/nai_07b_sft_pilot/checkpoints/
├── sft_step_0000000.pt  (22.05 MB) + sft_step_0000000.json
├── sft_step_0000050.pt  (66.15 MB) + sft_step_0000050.json
├── sft_step_0000100.pt  (66.15 MB) + sft_step_0000100.json
├── sft_best.pt          (66.15 MB) + sft_best.json
└── sft_latest.pt        (66.15 MB) + sft_latest.json
```

### 5.1 Pretraining Checkpoint Immutability

- **Target:** `F:\LOVE\native_ai\checkpoints\step_0000250.pt`
- **Recorded SHA-256 Before Pilot:** `dca206cbf535847ff6ccd58d80fb118c0e774ad2b44438edf7dcc96673743145`
- **Recorded SHA-256 After Pilot:** `dca206cbf535847ff6ccd58d80fb118c0e774ad2b44438edf7dcc96673743145`
- **Result:** **100% Bitwise Identical**. The original pretraining model was strictly isolated.

### 5.2 Model Parameter Mutation

Comparing the trained SFT model (Step 100) to the Step 250 baseline:
- Mutated Parameter Tensors: **38 / 38 tensors**
- Maximum Parameter Shift: $\max |W_{\text{SFT}} - W_{250}| = \mathbf{0.001105}$
- Mean Parameter Shift: $\text{mean} |W_{\text{SFT}} - W_{250}| = \mathbf{0.000228}$
- Restoration Check: Fresh model loaded from `sft_best.pt` matched the trained model bitwise ($\Delta W = \mathbf{0.0000000000}$).

---

## 6. Qualitative Generation Assessment & Empirical Limitations

Qualitative evaluation was conducted across 4 distinct capability domains, comparing the pretrained Step 250 baseline against the SFT Step 100 model under Greedy ($T=0.0$) and Sampling ($T=0.7, k=40$) decoding:

### Prompt 1: Instruction Dialogue
- **Prompt:** `"User: What is the difference between synchronous and asynchronous execution?\nAssistant:"`
  - *Pretrained (Step 250):* `' She was a She was a She was a She was She was She w'`
  - *SFT Greedy (Step 100):* `' She was She was She was She was She She She She'`
  - *SFT Sampling (T=0.7):* `' Ilp I was Me the can The Man F She hisid.  = '`

### Prompt 2: Reasoning & Mathematics
- **Prompt:** `"Solve the following math word problem step-by-step:\n\nIf a book has 120 pages and Leo reads 15 pages per day, how many days will he take to finish the book?\nAssistant:"`
  - *Pretrained (Step 250):* `' She was a but She was a but She was a but She was a but'`
  - *SFT Greedy (Step 100):* `' She was She was She was She was She was She She '`
  - *SFT Sampling (T=0.7):* `' Ilp I was Me the can The Man the  She his have  = '`

### Prompt 3: Structured Output
- **Prompt:** `"Extract the person and location from the sentence: 'Dr. Jane Smith gave a keynote lecture in Zurich, Switzerland.'\nAssistant:"`
  - *Pretrained (Step 250):* `' She was She She She She She She She She She'`
  - *SFT Greedy (Step 100):* `' She She She She She She She She She She S'`
  - *SFT Sampling (T=0.7):* `' Ilp I was Me the can The Man the  She has hou are the S'`

### Prompt 4: General Conversation
- **Prompt:** `"User: How can I organize my daily study schedule effectively?\nAssistant:"`
  - *Pretrained (Step 250):* `' She was She was She was She was She She She She'`
  - *SFT Greedy (Step 100):* `' She was She was She was She She She She She S'`
  - *SFT Sampling (T=0.7):* `' I"TMd " Mk.\n\n The Man F She hisid.  = '`

### Critical Analysis of Generation Capabilities

1. **Quantitative vs. Qualitative Disconnect:**  
   While validation loss dropped smoothly by 0.36 nats and perplexity dropped by 30%, the generated text reveals that **100 optimizer steps (processing 39k tokens) is far too brief for emergent instruction adherence**.
2. **Argmax Bigram Repetition:**  
   Under greedy decoding, both the pretrained baseline and the SFT model remain trapped in common high-probability unigram/bigram repetition cycles (`"She was She was..."`). The model has not yet learned multi-token grammatical phrasing.
3. **Sampling Token Diversity:**  
   Sampling decoding ($T=0.7, k=40$) introduces token diversity, but sentences remain syntactically fragmented.
4. **Objective Clarity:**  
   In compliance with Section 1 and Section 7 directives: **A falling validation loss does NOT indicate robust instruction-following or general intelligence.** The 100-step pilot successfully validates the training harness, gradient accumulation, loss masking, and optimizer mechanics; meaningful instruction-following will require substantially longer training runs (e.g., 2,500 to 5,000 steps).

---

## 7. Automated Regression Test Suite

Automated testing was executed across the full test suite using `pytest.ini`:

```
============================= test session starts =============================
platform win32 -- Python 3.11.16, pytest-9.2.0, pluggy-1.7.0
rootdir: F:\LOVE\native_ai
configfile: pytest.ini
plugins: anyio-4.16.0
collected 100 items

native_ai\tests\test_architecture.py .............                       [ 13%]
native_ai\tests\test_dataset_pipeline.py .........................       [ 38%]
native_ai\tests\test_sft_pipeline.py ................                    [ 54%]
native_ai\tests\test_sft_training.py ..........                          [ 64%]
native_ai\tests\test_tokenizer.py ..............                         [ 78%]
native_ai\tests\test_training_engine.py ......................           [100%]

============================ 100 passed in 34.32s =============================
```

All 100 unit tests passed (100% pass rate) with 0 errors and 0 warnings.

---

## 8. Final Gate Decision

| Evaluation Criteria | Required Condition | Actual Observed Result | Status |
| :--- | :--- | :--- | :---: |
| **Pre-Training Gate** | 10 / 10 checks passed | All 10 gates confirmed | **PASS** |
| **Target Step Goal** | Complete exactly 100 optimizer steps | Exactly 100 steps completed | **PASS** |
| **Validation Monotonicity**| Validation loss does not degrade | Monotonic descent (5.0205 $\to$ 4.6578) | **PASS** |
| **Gradient Accumulation** | Optimizer advances only on full cycle | Verified (every 2 micro-steps) | **PASS** |
| **Loss Masking** | Prompt/pad positions have zero grad | Verified ($\text{grad} = 0.000000$) | **PASS** |
| **Hardware Safety** | VRAM $<3,500\text{ MB}$, Disk $\ge 2.0\text{ GB}$| Peak VRAM: 322 MB, Disk: 3.695 GB | **PASS** |
| **Checkpoint Immutability**| Original `step_0000250.pt` unchanged | Verified 100% bitwise identical | **PASS** |
| **Experiment Isolation** | Clean separate directory | `experiments/nai_07b_sft_pilot/` | **PASS** |
| **Test Suite Coverage** | 100% passing tests | 100 / 100 passed in 34.32s | **PASS** |

### Final Phase Decision: **PASS**

Phase NAI-07B has fully achieved its experimental objective. The SFT training engine, gradient accumulation mechanics, loss masking, safety monitoring, and checkpoint persistence are verified and functional.

In strict compliance with Section 10 completion boundaries:
- Training was halted immediately at step 100.
- No larger training runs or unauthorized phases have been launched.
- Awaiting user review and explicit instructions for next development steps.
