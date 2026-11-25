# LOVE Native AI — NAI-08A: Native Model Capability & Data Quality Improvement Plan

**Project:** `F:\LOVE\native_ai`  
**Phase:** NAI-08A (Capability Audit & Evidence-Based Improvement Plan)  
**Pretrained Baseline Audited:** `checkpoints/step_0000250.pt` (`love-native-tiny`, 5,507,328 parameters)  
**SFT Model Audited:** `experiments/nai_07b_sft_pilot/checkpoints/sft_best.pt` (Step 100)  
**Audit Artifacts Directory:** `experiments/nai_08a_capability_audit/`  
**Date:** 2026-11-25  
**Final Decision:** **PASS** (Investigation complete; evidence-based improvement roadmap delivered)  
**Automated Tests:** 117 / 117 tests passing (100%) in 60.83s  
**Storage Headroom:** 3.687 GB free on drive `F:` (Threshold $\ge 2.000\text{ GB}$)  

---

## 1. Executive Summary

Phase NAI-08A investigated why LOVE's native language model (`love-native-tiny`) demonstrates smooth, reproducible training and validation loss reductions (NAI-05 pretraining: $8.9172 \to 6.3024$; NAI-07B SFT: $5.0205 \to 4.6578$), yet produces repetitive, incoherent text (`"She was She was..."`) and fails to follow instructions.

**Core Finding:** There is **no software bug** in the Transformer architecture, loss masking, or optimizer loop. Instead, the capability gap is caused by **four compounding structural bottlenecks**, led overwhelmingly by **extreme undertraining** (1.005% of one pretraining epoch; 1.72% of one SFT epoch) combined with **severe pretraining domain imbalance** (46.79% TinyStories, 0% code, 0.0084% general English), **high subword fragmentation** under an 8,192-token vocabulary, and **unconstrained greedy decoding** without `<eos>` stopping or repetition penalties.

All measurements were collected in strict read-only mode (`torch.no_grad()`, zero optimizer steps, zero held-out test-split access, zero weight or dataset mutations).

---

## 2. Findings Ranked by Severity & Impact

| Rank | Finding | Severity | Measured Evidence | Primary Impact |
| :---: | :--- | :---: | :--- | :--- |
| **1** | **Extreme Token Undertraining** | **CRITICAL** | NAI-05 saw **256,000 tokens** (1.005% of 25.47M train tokens); NAI-07B saw **39,437 target tokens** (1.72% of 2.30M SFT tokens). | Model remains in unigram/bigram frequency acquisition; step-0 entropy is **5.91 nats** (top-1 prob 5.8%, `<eos>` prob $7\times 10^{-6}$). |
| **2** | **Pretraining Domain Imbalance & Missing Domains** | **HIGH** | `english_synthetic_stories` (TinyStories) is **46.79%** of train tokens (30,000 docs); `technical_code` is **0%** (0 docs); `general_english` is **0.0084%** (10 docs); `structured_tasks` is **0.0027%** (2 docs). | Top corpus bigrams (`"You are"`, `"was a"`, `"there was"`, `"Once upon"`) dominate logits; weighted sampling cannot invent missing documents. |
| **3** | **Validation Split Blind Spots** | **HIGH** | Pretraining `val.jsonl` (1,904 docs) contains **0** `reasoning_math`, **0** `general_english`, **0** `structured_tasks`, and **0** `technical_code` documents. | Validation perplexity measures only TinyStories + OASST1, masking regressions or gaps in math, general prose, and structured tasks. |
| **4** | **Inference Engine Decoding Deficits** | **MEDIUM** | `LoveForCausalLM.generate()` lacks `<eos>` early stopping, `repetition_penalty`, `top_p`, and KV caching. Greedy decoding yields **0.872** bigram repetition rate on SFT step 100. | Even if `<eos>` were predicted, generation loops until `max_new_tokens`; greedy decoding locks into `"She was"` attractor cycles. |
| **5** | **Tiny Capacity & High Embedding Overhead** | **MEDIUM** | `love-native-tiny` has 5.51M params, of which **38.08%** (2.10M) are embeddings and only **3.41M** are Transformer block weights across 4 layers. | Severely constrains multi-step reasoning, long-range syntax, and knowledge retention once pretraining saturates. |
| **6** | **8,192-Vocab Subword Fragmentation** | **MEDIUM** | Common English averages **1.92 tokens/word** (2.57 chars/token); digits/math average **3.69 tokens/word**; JSON averages **5.50 tokens/word**; top-20 tokens = **32.66%** of corpus. | Inflates sequence length, wastes the 512-token context window, and contributed to **3,293** SFT examples being rejected as $>512$ tokens. |
| **7** | **SFT Category Skew & Narrative Typo** | **LOW-MED** | `sft_train.jsonl` has **11,639** examples (52.4% math, 36.8% general conv, **0.58%** structured output, **1.16%** summarization). NAI-07C's "11,658" was a typo. | Under-trains structured JSON, summarization, and multi-turn tool/code formatting even at longer SFT schedules. |

---

## 3. Model Architecture Investigation

Inspection of `model/love_model.py`, `attention.py`, `feedforward.py`, `normalization.py`, `rotary.py`, `embeddings.py`, `transformer_block.py`, and `configs/{tiny,small}.yaml` confirms:

- **Core Layers (Verified Correct):**
  - **Embeddings & Tied Weights:** `TokenEmbedding` enforces strict `[0, vocab_size - 1]` bounds; `lm_head.weight` is tied directly (`=`) to `token_embeddings.embedding.weight`.
  - **Attention & Causal Masking:** `CausalSelfAttention` uses PyTorch `F.scaled_dot_product_attention(..., is_causal=True)` when `attention_mask is None`, and an explicit upper-triangular `-inf` mask otherwise.
  - **RMSNorm:** Casts to `float32` inside `_norm` for numerical stability before casting back.
  - **RoPE:** Precomputes `inv_freq` with `base=10000.0` up to `context_length=512` and dynamically rebuilds cache if `seq_len > max_seq_len`.
  - **SwiGLU & Pre-Norm Residuals:** Standard `x + attn(attn_norm(x))` and `x + ffn(ffn_norm(x))` with `SiLU(x W_gate) * (x W_up) W_down`.
  - **Initialization:** `normal_(mean=0.0, std=0.02)` on all `nn.Linear` and `nn.Embedding`, `ones_` on `RMSNorm`. (Observation: lacks GPT-2/LLaMA $1/\sqrt{2L}$ residual output scaling on `out_proj` and `w_down`, which is benign at 4 layers but advisable at 8+ layers.)
- **Generation Path Deficits (`LoveForCausalLM.generate()`):**
  - Hard-sliced sliding window (`generated[:, -context_length:]`) recomputes the entire prefix at every step (no KV cache).
  - **No `eos_token_id` stopping criterion** — always runs for `max_new_tokens` steps.
  - **No `top_p` (nucleus) sampling** and **no `repetition_penalty`**.

### Architecture Comparison: `love-native-tiny` vs. `love-native-small`

| Metric | `love-native-tiny` (`configs/tiny.yaml`) | `love-native-small` (`configs/small.yaml`) | Ratio (`small / tiny`) |
| :--- | :---: | :---: | :---: |
| **Layers / Heads / Hidden / FFN** | 4L / 4H / 256D / 768F | 8L / 8H / 512D / 1536F | $2\times$ depth & width |
| **Total Parameters (Tied)** | **5,507,328** (38 tensors) | **31,465,984** | $5.71\times$ |
| **Embedding Parameters (%)** | 2,097,152 (**38.08%**) | 4,194,304 (**13.33%**) | $2.00\times$ |
| **Non-Embedding Parameters (%)** | 3,410,176 (**61.92%**) | 27,271,680 (**86.67%**) | $8.00\times$ |
| **Context Length / Vocab** | 512 / 8,192 | 512 / 8,192 | $1.0\times$ |
| **Measured CUDA Eval Peak** | **46.64 MB** | **165.04 MB** | $3.54\times$ |

**Assessment:** `love-native-tiny` (3.41M non-embedding weights) is likely too small for robust multi-domain reasoning and instruction following, **but `love-native-small` is not automatically better right now**: at ~20 tokens/parameter (Chinchilla scaling), `small` wants ~630M tokens vs. the current 25.47M-token corpus. Training `small` on 25M tokens risks overfitting unless pretraining data is expanded or epochs are carefully regularized.

---

## 4. Tokenizer Investigation (`LoveTokenizer`)

Audited without modifying `tokenizer/artifacts/` (`vocab_size = 8,192`, Byte-Level BPE):

1. **Vocabulary Utilization & `<unk>`:**
   - Pretraining `train.bin` (25,467,894 tokens): **6,919 / 8,192 (84.46%)** unique IDs used; **0 `<unk>` tokens**.
   - Pretraining `validation.bin` (933,909 tokens): **4,513 / 8,192** unique IDs used; **0 `<unk>` tokens**.
   - SFT `sft_train` + `sft_val` (5,394,839 content tokens): **6,325 / 8,192 (77.21%)** unique IDs used; **12 `<unk>` tokens** (0.00022%).
2. **Token Concentration:** The top 20 tokens account for **32.66%** of all 25.47M pretraining tokens, dominated by single-byte/short fragments (`' '` 5.81%, `'.'` 3.29%, `' the'` 2.30%, `','` 2.26%, `'s'` 2.14%, `'\n'` 2.06%, `' w'` 1.37%, `'y'` 1.21%, `' s'` 1.17%, `' h'` 1.16%).
3. **Subword Fragmentation Probes:**

| Probe Domain | Words | Tokens | Tokens / Word | Chars / Token | Round-Trip Exact |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `common_english` | 12 | 23 | **1.92** | 2.57 | Yes |
| `assistant_dialog` | 10 | 24 | **2.40** | 2.54 | Yes |
| `numbers_and_math` | 13 | 48 | **3.69** | 1.10 | Yes |
| `code_python` | 15 | 54 | **3.60** | 1.65 | Yes |
| `json_structured` | 8 | 44 | **5.50** | 1.43 | Yes |
| `punctuation_unicode` | 9 | 44 | **4.89** | 1.41 | Yes |

4. **Special Token Handling:** Round-trip encoding/decoding of `<|system|>`, `<|user|>`, `<|assistant|>`, `<eos>` is exact (`skip_special_tokens=False` preserves them; `True` strips them cleanly).
5. **Root-Cause Assessment:** `LoveTokenizer` is **mechanically sound** (lossless byte-level round-trip, near-zero `<unk>`), so it is **not** the primary cause of incoherent output. However, the 8,192 vocabulary fragments common words (`qu-ic-k`, `b-row-n`) and splits JSON/code/digits into 3.6–5.5 tokens/word, consuming context budget prematurely.

---

## 5. Pretraining Data Quality & Diversity Audit (Train + Validation Only)

Scanned `datasets/splits/train/train.jsonl` (55,831 docs) and `datasets/splits/validation/val.jsonl` (1,904 docs), plus `data_cache/cache_manifest.json` and `data_cache/sampler.py`:

| Category | Train Docs | Train Tokens | Share of Corpus | Sampler Prob (`domain_weighted`) | Val Docs | Val Tokens |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `english_synthetic_stories` (TinyStories) | 30,000 | 11,917,089 | **46.79%** | 0.400 | 1,000 | 348,997 |
| `instruction_dialog` (OASST1 + 3 seed) | 18,342 | 11,501,502 | **45.16%** | 0.350 | 904 | 584,912 |
| `reasoning_math` (GSM8K + 4 seed) | 7,477 | 2,046,500 | **8.04%** | 0.230 | **0** | **0** |
| `general_english` (Seed only) | **10** | **2,128** | **0.0084%** | 0.015 | **0** | **0** |
| `structured_tasks` (Seed only) | **2** | **675** | **0.0027%** | 0.005 | **0** | **0** |
| `technical_code` | **0** | **0** | **0.0000%** | 0.000 | **0** | **0** |
| **Total** | **55,831** | **25,467,894** | **100%** | **1.000** | **1,904** | **933,909** |

- **Duplicates & Leakage:** Exact duplicates = 0, normalized duplicates = 0 in both `train.jsonl` and `val.jsonl`; normalized hash overlap between `train.jsonl` and `val.jsonl` = **0**.
- **Overexposure Evidence:**
  - Top bigrams in `train.jsonl`: `"You are"` (25,862), `"are LOVE,"` (25,814), `"LOVE, an"` (25,813) [prepended system prompts], followed immediately by TinyStories clichés: `"was a"` (22,123), `"there was"` (19,148), `"upon a"` (18,340), `"Once upon"` (18,229), `"One day,"` (16,645), `"a time,"` (14,654).
  - Weighted sampling **does not solve missing domain coverage**: giving `general_english` weight 0.015 or `structured_tasks` weight 0.005 merely repeats the same **10** and **2** seed documents hundreds of times.
  - Note: 1,860 OASST1 docs contain heuristic code snippets (` ``` ` / `def ` / `import `), but there is **no dedicated code corpus**.

---

## 6. SFT Data Quality & Reconciliation (Train + Validation Only)

### 6.1 Reconciliation: 11,639 vs. 11,658
- `datasets/sft/manifests/sft_manifest.json` records `splits.train.example_count = 11639` (8,545 trees).
- Line-by-line scan of `datasets/sft/splits/sft_train.jsonl` confirms **exactly 11,639** examples (and `sft_val.jsonl` = **1,387** examples across 1,005 trees).
- **Conclusion:** NAI-07A's figure (`11,639`) is exact. NAI-07C's Section 8.2 reference to `11,658` was a narrative typo (+19 examples) with no basis in the manifest or JSONL file.

### 6.2 SFT Composition & Quality Profile (`sft_train.jsonl`)
- **Sources:** `src_ext_gsm8k`: 5,856 (50.3%); `src_ext_oasst1`: 5,761 (49.5%); Seed corpus: 22 (0.19%).
- **Categories:** `reasoning_mathematics`: 6,099 (52.4%); `general_conversation`: 4,279 (36.8%); `instruction_following`: 799 (6.9%); `safe_refusal`: 259 (2.2%); `writing_summarization`: **135** (1.16%); `structured_output`: **68** (0.58%).
- **Turn Depth:** 1-turn: 7,431 (63.8%); 2-turn: 4,026 (34.6%); 3-turn: 182 (1.6%).
- **Token Lengths:** User turns mean **73.4** tokens (median 54, p95 169); Assistant turns mean **208.4** tokens (median 168, p95 495.6).
- **Code & Refusal Coverage:** 503 train examples contain code blocks (` ``` ` / `def `); 272 contain explicit refusal phrases.
- **Pipeline Attrition:** 3,293 / 17,021 candidates (19.3%) were rejected by `TruncationSafetyError` for exceeding the 512-token context limit, disproportionately dropping longer multi-turn OASST1 responses.
- **Duplicate Turn Note:** 4,179 duplicate user turns and 1,136 duplicate assistant turns reflect normal multi-turn tree branching (shared root prompts across sibling paths in OASST1).

---

## 7. Inference & Generation Diagnostics (Read-Only)

Evaluated `step_0000250.pt` vs. `sft_best.pt` across all 8 fixed prompts (48 generated tokens each) under 6 decoding configurations:

| Model & Decoding Config | Mean Bigram Rep Rate | Mean Trigram Rep Rate | Mean Unique Token Ratio | Step-0 Entropy (Max 9.01) | Step-0 Top-1 Prob | Step-0 `<eos>` Prob |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pretrained Step 250 — Greedy ($T=0$)** | 0.809 | 0.786 | 0.170 | 5.9301 | 0.0614 | 0.000007 |
| **Pretrained Step 250 — Greedy + RepPen 1.5** | 0.149 | 0.117 | 0.719 | 5.9301 | 0.0614 | 0.000007 |
| **Pretrained Step 250 — Sample ($T=0.7, p=0.9, \text{rp}=1.2$)** | 0.027 | 0.000 | 0.742 | 5.9301 | 0.0614 | 0.000007 |
| **SFT Best Step 100 — Greedy ($T=0$)** | **0.872** | **0.848** | **0.104** | **5.9062** | **0.0579** | **0.000007** |
| **SFT Best Step 100 — Greedy + RepPen 1.2** | 0.777 | 0.769 | 0.206 | 5.9062 | 0.0579 | 0.000007 |
| **SFT Best Step 100 — Greedy + RepPen 1.5** | 0.120 | 0.106 | 0.752 | 5.9062 | 0.0579 | 0.000007 |
| **SFT Best Step 100 — Sample ($T=0.7, k=40$)** | 0.186 | 0.054 | 0.575 | 5.9062 | 0.0579 | 0.000007 |
| **SFT Best Step 100 — Sample ($T=0.7, p=0.9, \text{rp}=1.2$)** | **0.024** | **0.000** | **0.781** | 5.9062 | 0.0579 | 0.000007 |

**Key Diagnostic Insights:**
- **High-Entropy Flat Logits:** Step-0 entropy is ~5.91 nats (top-1 probability only 5.8%, top-5 cumulative ~23.5%), proving the model has not yet formed sharp semantic predictions.
- **Zero `<eos>` Awareness:** `<eos>` probability at step 0 is `7e-6` (rank ~3,647 / 8,192), and **0 of 96** diagnostic runs emitted `<eos>`.
- **Decoding Adjustments Do Not Repair Capability:** Repetition penalty (`1.5`) or nucleus sampling (`p=0.9, rp=1.2`) eliminates the mechanical `"She was She was"` loop (bigram repetition $0.872 \to 0.024$), but the resulting text remains fragmented word salad because the underlying weights are undertrained.

---

## 8. Training Methodology & Root-Cause Hypotheses

### Measured Evidence vs. Root-Cause Hypotheses

| Aspect | Measured Evidence (Fact) | Root-Cause Hypothesis (Inferred) |
| :--- | :--- | :--- |
| **Pretraining Exposure** | 250 steps $\times$ 1,024 tok/step = **256,000 tokens** (1.005% of 1 epoch). Val loss = 6.3024 (PPL 545.87). | **Primary Cause:** 256K tokens is ~400$\times$ too short to learn English grammar; model only learned high-frequency corpus priors (`"She was"`, `"The"`). |
| **SFT Exposure** | 100 steps $\times$ 2 seqs = **39,437 target tokens** (1.72% of 1 epoch). Val loss = 4.6578 (PPL 105.40). | **Primary Cause:** 100 steps at `lr=2e-5` nudged token priors toward assistant turns without overcoming pretraining undertraining. |
| **Optimizer & Stability** | Loss descended monotonically in NAI-05 and NAI-07B; 0 NaNs/Infs; grad norms 1.78–2.97; cosine warmup & clipping worked cleanly. | Training hyperparameters (AdamW, warmup, clipping, assistant-only `-100` masking) are **not** broken; they simply need full-scale step budgets. |
| **Capacity vs. Data** | `tiny` has 3.41M non-embedding params; 25.47M train tokens $\approx 4.6\times$ total params. | `tiny` is undertrained on the current data, not overfitting; `tiny` can still improve dramatically with 2,500–10,000+ pretraining steps before hitting its capacity ceiling. |

### Unresolved Questions
1. At what pretraining step count (e.g., 5,000 vs. 25,000 steps) does `love-native-tiny` hit its validation perplexity floor on `validation.bin`?
2. How much does adding a clean, permissively licensed Wikipedia / prose / code corpus reduce TinyStories narrative bias compared to merely training longer on the existing corpus?

---

## 9. Prioritized Improvement Roadmap

| Priority | Track | Concrete Action | Rationale / Prerequisite |
| :---: | :--- | :--- | :--- |
| **P0** | **D. Pretraining Strategy** | Run sustained pretraining on `love-native-tiny` (e.g., 5,000–25,000 steps, 5M–25M+ tokens) **before** scaling SFT, with validation gates at every 1,000 steps. | Fixes the #1 bottleneck (1.0% epoch exposure) at low VRAM cost (~146 MB) on GTX 1650. |
| **P1** | **C. Pretraining Data** | Acquire separately approved, permissively licensed **general English prose** (e.g., FineWeb-Edu / Wikipedia subset) and **code** (e.g., The Stack permissive / StarCoderData Python subset), and rebalance `val.jsonl` to cover all domains. | Eliminates 46.8% TinyStories bias, 0% code, and 0.008% general English; requires separate dataset approval & storage planning. |
| **P2** | **F. Inference** | Upgrade `LoveForCausalLM.generate()` to support `eos_token_id` stopping, `repetition_penalty`, `top_p` nucleus sampling, and optional KV caching. | Fixes infinite generation & greedy repetition loops without altering weights. |
| **P2** | **E. SFT Strategy** | Expand `structured_output` (currently 68), `writing_summarization` (currently 135), and `code` SFT examples; then scale SFT to 1–3 full epochs (~5,800–17,400 steps at eff. batch 2–4). | Balances assistant capabilities once the pretrained base has coherent English. |
| **P3** | **B. Model Architecture** | Keep `love-native-tiny` for NAI-08B baseline saturation; transition to `love-native-small` (31.5M) or a 15M–25M intermediate config **only after** pretraining data exceeds 100M+ tokens. Add $1/\sqrt{2L}$ residual scaling. | Avoids wasting compute on an under-saturated 31.5M model before data scale justifies it. |
| **P4** | **A. Tokenizer** | Retain 8,192 vocab for NAI-08B continuity; consider 16,384–32,768 BPE vocab **only** when starting a fresh `small`+ pretraining run with expanded prose/code corpora. | Changing vocab invalidates all existing binary caches and checkpoints; defer until major model reset. |
| **P2** | **G. Evaluation** | Adopt `experiments/nai_08a_capability_audit/proposed_benchmark_spec.json` as minimum release gates across all 8 domains. | Prevents equating falling loss with actual assistant readiness. |

### Proposed Minimum Evaluation Gates (`proposed_benchmark_spec.json` Summary)
*(Proposed targets only — none are claimed achieved by NAI-05 or NAI-07B)*:
- **English Coherence:** Pretrain val PPL $\le 35.0$; greedy bigram rep $\le 0.15$, trigram rep $\le 0.05$.
- **Basic Conversation:** $\ge 90\%$ `<eos>` termination; $\ge 80\%$ on-topic relevance (20 prompts).
- **Instruction Adherence:** $\ge 70\%$ pass rate on verifiable formatting/length constraints (20 prompts).
- **Arithmetic Reasoning:** $\ge 15\%$ exact answer accuracy on 50 non-training GSM8K problems (baseline gate; $\ge 35\%$ target).
- **Summarization:** $\ge 85\%$ length compliance, $\le 10\%$ hallucination (15 prompts).
- **Structured Output:** $\ge 85\%$ valid JSON parse rate, $\ge 80\%$ schema key match (20 prompts).
- **Coding:** Blocked until licensed code corpus is approved; target $\ge 80\%$ Python AST parse, $\ge 25\%$ pass@1 (20 prompts).
- **Safety & Refusal:** $\ge 95\%$ unsafe refusal, $\le 10\%$ benign over-refusal, $\ge 80\%$ prompt-injection resistance (20 prompts).

---

## 10. Hardware & Storage Feasibility (GTX 1650 4GB)

| Configuration (Micro-Batch = 1, Seq = 512) | `love-native-tiny` (5.51M) | `love-native-small` (31.47M) | GTX 1650 (4,095.56 MB, Safe Limit 3,500 MB) |
| :--- | :---: | :---: | :--- |
| **Measured Eval Peak VRAM** | **46.64 MB** | **165.04 MB** | Measured directly on CUDA |
| **Estimated Static (Weights + Grads + AdamW FP32)** | 84.04 MB | 480.13 MB | Analytical (`16 * P` bytes) |
| **Estimated Activations (FP32 Standard / Checkpointed)** | 62.0 MB / 29.5 MB | 200.0 MB / 47.0 MB | Analytical |
| **Estimated Total Train VRAM (FP32 Standard)** | **146.04 MB** | **680.13 MB** | Both fit under 3,500 MB; `small` benefits from `use_activation_checkpointing=True` (~527 MB) |
| **Estimated Total Train VRAM (FP16 AMP)** | **121.24 MB** | **600.13 MB** | Analytical; AMP saves activation memory |
| **Throughput & Time Feasibility** | ~11.7k tok/s (NAI-05 measured) | ~6$\times$ slower (~2k tok/s est.) | 25M tokens on `tiny` $\approx 36\text{ min}$ local; 630M tokens on `small` $\approx 87\text{ hrs}$ (would justify rented GPU) |
| **Host Disk Space (`F:`)** | **3.687 GB free** | Requires $\ge 2.0\text{ GB}$ reserve | Only ~1.69 GB usable headroom; large new corpora (>1 GB) would require cleanup or external storage. |

---

## 11. Automated Verification & Integrity Audit

- **Pytest Configuration Review:** Reviewed `pytest.ini` (`testpaths = tests`, `pythonpath = . ..`) and `tests/conftest.py` (adds `F:\LOVE` and `F:\LOVE\native_ai` to `sys.path`). Confirmed test discovery, module imports, and isolation operate cleanly.
- **New Read-Only Audit Tests:** Added `tests/test_nai08a_audit.py` (7 tests) verifying checkpoint hashes, tokenizer checksums, manifest counts, zero test-split access in `run_nai08a_diagnostics.py`, deterministic read-only inference with zero weight mutation, artifact schema validity, and pytest import config.
- **Full Suite Result:** `117 passed in 60.83s` (0 failures, 0 skipped).
- **Bitwise Integrity Confirmed:**
  - `checkpoints/step_0000250.pt`: `dca206cbf535847ff6ccd58d80fb118c0e774ad2b44438edf7dcc96673743145` (unchanged)
  - `experiments/nai_07b_sft_pilot/checkpoints/sft_best.pt`: `31ad59611b23710fb9d759e3c5c059a352b9cbd53338734911dc39cdf0fd8bdb` (unchanged)
  - `tokenizer/artifacts/{vocab.json, merges.txt, tokenizer.json}`: all 3 checksums unchanged.

---

## 12. Final Decision

**PASS** — Investigation is complete, all integrity and test-isolation boundaries were upheld, and an evidence-based improvement roadmap is ready for review. No training, dataset acquisition, or code modification beyond read-only audit scripts/tests was executed. Awaiting explicit authorization before starting any next phase (e.g., NAI-08B).
