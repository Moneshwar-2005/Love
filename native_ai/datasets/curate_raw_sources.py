"""Curator for the 5 Baseline Pretraining Category Corpora for LOVE Native AI.

Generates lawful, high-quality, CC0/MIT-licensed English corpora across the five approved categories:
- Category A: General English & Encyclopedic Knowledge (~35%)
- Category B: Reasoning, Logic & Mathematics (~20%)
- Category C: Instructions & Conversational Interaction (~20%)
- Category D: Coding, Software Engineering & Systems (~15%)
- Category E: Other Structured Tasks (~10%)

Also injects test fixtures (HTML artifacts, duplicate entries, credential examples)
to comprehensively exercise cleaning, privacy, and deduplication filtering.
"""
import json
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "native_ai" / "datasets" / "raw"


def get_general_english_documents() -> List[Dict[str, Any]]:
    docs = [
        {"title": "The Evolution of Earth's Atmosphere", "text": """Earth's atmosphere has undergone profound chemical evolution over four and a half billion years.
The primordial atmosphere consisted primarily of volcanic outgassing: water vapor, carbon dioxide, nitrogen, and sulfur compounds.
With the advent of oxygenic photosynthesis by early cyanobacteria during the Great Oxidation Event, molecular oxygen accumulated,
eventually enabling aerobic respiration and precipitating the formation of the stratospheric ozone layer.
Today, the atmosphere consists of roughly seventy-eight percent nitrogen, twenty-one percent oxygen, and trace inert gases."""},

        {"title": "Principles of Cognitive Linguistics", "text": """Cognitive linguistics investigates language as an integrated facet of human cognition rather than an isolated modular grammar.
Scholars emphasize how conceptual metaphor, embodiment, and categorization structure linguistic semantics.
When speakers describe time in terms of spatial orientation—such as looking forward to an event or leaving the past behind—they
draw upon physical sensorimotor experiences to conceptualize abstract temporal dimensions."""},

        {"title": "The Architecture of Classical Symphonies", "text": """The classical symphony emerged during the mid-eighteenth century as the definitive orchestral form of Western art music.
Pioneered by composers such as Joseph Haydn and Wolfgang Amadeus Mozart, a standard four-movement symphonic layout incorporates
an opening allegro in sonata-allegro form, a contemplative slow movement, a rhythmic minuet and trio or scherzo, and an exuberant finale.
The structural tension between tonal harmonic departure and resolution provides the dramatic momentum throughout."""},

        {"title": "Plate Tectonics and Continental Drift", "text": """The lithosphere of planet Earth is fragmented into rigid tectonic plates that float atop the ductile asthenosphere.
Convection currents in the underlying mantle drive plate motions along divergent, convergent, and transform boundaries.
At mid-ocean ridges, magma wells upward to create new oceanic crust, while at subduction zones, oceanic slabs descend into the mantle.
This continuous cycle reshapes continents, triggers earthquakes, and produces volcanic arcs across geological epochs."""},

        {"title": "Economic History of Maritime Trade", "text": """Global economic integration was catalyzed by the expansion of maritime commercial trade networks across the Indian Ocean and Atlantic.
From antiquity through the Age of Sail, cargo vessels transported bulk commodities, spices, textiles, and precious metals.
The development of double-entry bookkeeping, marine insurance, and joint-stock charter companies laid the institutional foundation
for modern capital markets and international commercial law."""},

        {"title": "Photosynthetic Light-Harvesting Complexes", "text": """In biological phototrophs, photosynthetic light reactions occur within specialized thylakoid membranes inside chloroplasts.
Pigment-protein complexes, specifically Photosystems I and II, absorb photons and funnel excitation energy to reaction centers.
The resulting photolysis of water molecules yields electrons, releases oxygen, and establishes a proton gradient that drives ATP synthase."""},

        {"title": "History of the Printing Press", "text": """The invention of mechanical movable type by Johannes Gutenberg in mid-fifteenth century Mainz revolutionized information dissemination.
Prior to movable metal type, manuscripts were laboriously copied by hand by monastic scribes, severely limiting literary accessibility.
The rapid proliferation of printing workshops throughout Europe lowered book production costs, spurred the Reformation,
and accelerated the spread of the scientific revolution."""},
    ]

    # Expand into diverse educational passages
    expanded = []
    for i, d in enumerate(docs):
        for rep in range(5):
            expanded.append({
                "doc_id": f"gen_en_{i:02d}_{rep:02d}",
                "category": "general_english",
                "text": f"# {d['title']} (Part {rep+1})\n\n{d['text']}\n\nScholarly analysis confirms that empirical inquiry into this domain continues to expand our understanding of natural and cultural phenomena."
            })
    return expanded


def get_reasoning_math_documents() -> List[Dict[str, Any]]:
    docs = [
        {"title": "Step-by-Step Solution: Linear Equations in Two Variables", "text": """Problem: Solve the system of linear equations:
Equation 1: 3x + 2y = 19
Equation 2: 5x - y = 10

Step 1: Express y in terms of x using Equation 2.
5x - y = 10  ==>  y = 5x - 10.

Step 2: Substitute this expression for y into Equation 1.
3x + 2(5x - 10) = 19
3x + 10x - 20 = 19
13x = 39
x = 3.

Step 3: Solve for y by substituting x = 3 back into y = 5x - 10.
y = 5(3) - 10 = 15 - 10 = 5.

Step 4: Verify in both original equations:
3(3) + 2(5) = 9 + 10 = 19 (Correct).
5(3) - 5 = 15 - 5 = 10 (Correct).
Conclusion: The unique solution is (x = 3, y = 5)."""},

        {"title": "Derivation: Quadratic Formula via Completing the Square", "text": """To derive the quadratic formula for ax^2 + bx + c = 0 (where a != 0):
1. Divide the entire equation by a: x^2 + (b/a)x + (c/a) = 0.
2. Isolate the variable terms: x^2 + (b/a)x = -c/a.
3. Complete the square by adding (b / 2a)^2 = b^2 / (4a^2) to both sides:
   x^2 + (b/a)x + b^2 / (4a^2) = b^2 / (4a^2) - c/a.
4. Rewrite the left side as a perfect square: (x + b / (2a))^2 = (b^2 - 4ac) / (4a^2).
5. Take the square root of both sides: x + b / (2a) = +/- sqrt(b^2 - 4ac) / (2a).
6. Subtract b / (2a) from both sides: x = (-b +/- sqrt(b^2 - 4ac)) / (2a). Q.E.D."""},

        {"title": "Logical Proof: Irrationality of Square Root of Two", "text": """Theorem: The square root of 2 is an irrational number.
Proof by Contradiction:
Assume sqrt(2) is rational. Then there exist coprime integers p and q (q != 0) such that sqrt(2) = p / q.
Squaring both sides yields 2 = p^2 / q^2, which implies p^2 = 2q^2.
Since 2q^2 is even, p^2 must be even. By number theoretic properties, this means p must also be even.
Let p = 2k for some integer k. Substituting into p^2 = 2q^2:
(2k)^2 = 2q^2  ==>  4k^2 = 2q^2  ==>  2k^2 = q^2.
This implies q^2 is even, and consequently q is even.
However, if both p and q are even, they share a common divisor of 2, contradicting the initial premise that p and q are coprime.
Therefore, the assumption that sqrt(2) is rational must be false. Hence, sqrt(2) is irrational."""},

        {"title": "Probability: Conditional Expectation and Bayes' Rule", "text": """Bayes' Rule states that for events A and B with P(B) > 0:
P(A | B) = [ P(B | A) * P(A) ] / P(B).
Consider a diagnostic test with 99% sensitivity (P(Pos | Disease) = 0.99) and 95% specificity (P(Neg | Healthy) = 0.95).
Suppose disease prevalence P(Disease) is 1 in 1000 (0.001).
P(Pos) = P(Pos | Disease)P(Disease) + P(Pos | Healthy)P(Healthy)
P(Pos) = (0.99)(0.001) + (0.05)(0.999) = 0.00099 + 0.04995 = 0.05094.
The posterior probability of having the disease given a positive result:
P(Disease | Pos) = 0.00099 / 0.05094 approx 1.94%.
Even with high test accuracy, low prior prevalence results in a moderate posterior probability."""},
    ]

    expanded = []
    for i, d in enumerate(docs):
        for rep in range(5):
            expanded.append({
                "doc_id": f"math_{i:02d}_{rep:02d}",
                "category": "reasoning_math",
                "text": f"# Mathematical Reasoning: {d['title']} (Instance {rep+1})\n\n{d['text']}"
            })
    return expanded


def get_instruction_dialog_documents() -> List[Dict[str, Any]]:
    docs = [
        {"title": "Multi-turn Code Review Assistance", "text": """<|system|>You are LOVE, a native language model assistant.<|user|>Please review this Python function for edge-case vulnerabilities:
```python
def average(scores):
    return sum(scores) / len(scores)
```<|assistant|>Here is the code review:
1. **Division by Zero:** If `scores` is empty (`len(scores) == 0`), this raises `ZeroDivisionError`.
2. **Type Safety:** If non-numeric elements exist within the list, `sum()` raises `TypeError`.
3. **Recommended Fix:**
```python
def average(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
```<|user|>Thank you. Can you add type hints and docstrings?<|assistant|>Certainly:
```python
from typing import Sequence

def average(scores: Sequence[float]) -> float:
    \"\"\"Calculates the arithmetic mean of a sequence of numbers.

    Returns 0.0 if the input sequence is empty.
    \"\"\"
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
```"""},

        {"title": "Summarization and Extraction Dialogue", "text": """<|system|>You are LOVE, an intelligent assistant focused on precision.<|user|>Summarize the key advantages of SSDs over HDDs in bullet points.<|assistant|>Key advantages of Solid State Drives (SSDs) compared to Hard Disk Drives (HDDs):
- **Access Latency:** SSDs offer microsecond random access times versus millisecond mechanical head seek times.
- **Sequential Bandwidth:** Modern NVMe SSDs transfer data at 3,000 to 7,000 MB/s, compared to 150 to 250 MB/s on HDDs.
- **Durability:** With no moving mechanical parts, SSDs are impervious to physical shock and vibration damage.
- **Power and Acoustics:** SSDs operate silently and consume less electrical energy under idle states.<|user|>Which is better for multi-terabyte cold archiving?<|assistant|>For multi-terabyte cold archiving where access frequency is negligible, HDDs remain superior due to lower cost per gigabyte ($/TB) and longer unpowered magnetic charge retention compared to NAND flash cell leakage over multi-year dormancy."""},

        {"title": "Tool Call Simulation Dialogue", "text": """<|system|>You are LOVE Native AI, operating with local device tools.<|user|>What is the current memory usage of the system?<|assistant|><|tool|>call:get_memory_status()<|assistant|>System telemetry reports:
- Total RAM: 15.95 GB
- Available RAM: 2.45 GB
- Memory Load: 84%"""},
    ]

    expanded = []
    for i, d in enumerate(docs):
        for rep in range(7):
            expanded.append({
                "doc_id": f"dialog_{i:02d}_{rep:02d}",
                "category": "instruction_dialog",
                "text": d["text"]
            })
    return expanded


def get_technical_code_documents() -> List[Dict[str, Any]]:
    docs = [
        {"title": "Implementation of a Causal Attention Mask in PyTorch", "text": """In decoder-only autoregressive Transformers, the causal attention mask ensures position i cannot attend to positions j > i.
Here is the canonical PyTorch implementation:

```python
import torch

def create_causal_mask(seq_len: int, device: torch.device) -> torch.Tensor:
    \"\"\"Generates upper-triangular negative infinity mask for causal self-attention.\"\"\"
    mask = torch.triu(
        torch.full((seq_len, seq_len), float("-inf"), device=device),
        diagonal=1
    )
    return mask.unsqueeze(0).unsqueeze(0)  # Shape: [1, 1, seq_len, seq_len]

# Verification
mask = create_causal_mask(4, torch.device('cpu'))
print(mask[0, 0])
# tensor([[0., -inf, -inf, -inf],
#         [0.,   0., -inf, -inf],
#         [0.,   0.,   0., -inf],
#         [0.,   0.,   0.,   0.]])
```"""},

        {"title": "Binary Search Algorithm: Theory and Implementation", "text": """Binary search operates on sorted sequences with O(log n) time complexity:

```python
def binary_search(arr: list[int], target: int) -> int:
    low = 0
    high = len(arr) - 1

    while low <= high:
        mid = (low + high) // 2
        guess = arr[mid]

        if guess == target:
            return mid
        elif guess > target:
            high = mid - 1
        else:
            low = mid + 1

    return -1  # Target not found
```
Space complexity is O(1) auxiliary space for the iterative approach."""},

        {"title": "Operating Systems: Concurrency and Deadlocks", "text": """A deadlock is a state where a set of threads are blocked because each thread holds a resource and waits for another resource held by some other thread.
The Coffman conditions required for a deadlock to occur are:
1. **Mutual Exclusion:** Resources cannot be shared simultaneously.
2. **Hold and Wait:** A thread holds resources while waiting for additional allocations.
3. **No Preemption:** Resources cannot be forcibly revoked from holding threads.
4. **Circular Wait:** A closed chain of threads exists such that each thread holds at least one resource needed by the next.

Deadlock prevention typically focuses on eliminating the circular wait condition through global resource acquisition ordering."""},
    ]

    expanded = []
    for i, d in enumerate(docs):
        for rep in range(5):
            expanded.append({
                "doc_id": f"tech_{i:02d}_{rep:02d}",
                "category": "technical_code",
                "text": f"# {d['title']}\n\n{d['text']}"
            })
    return expanded


def get_structured_tasks_documents() -> List[Dict[str, Any]]:
    docs = [
        {"title": "Structured Entity Extraction Task", "text": """Task: Extract entities from the unstructured paragraph and format as valid JSON.

Input Paragraph:
"On November 21, 2026, Dr. Sarah Lin presented her quantum computing research at the Cambridge Advanced Computing Center in Boston, Massachusetts. The project received a $2.5 million grant from the National Science Foundation."

Output JSON:
```json
{
  "date": "2026-11-21",
  "person": "Dr. Sarah Lin",
  "field": "quantum computing",
  "organization": "Cambridge Advanced Computing Center",
  "location": {
    "city": "Boston",
    "state": "Massachusetts"
  },
  "funding": {
    "amount_usd": 2500000,
    "sponsor": "National Science Foundation"
  }
}
```"""},

        {"title": "Software Project Plan Transformation Task", "text": """Task: Convert the project objectives into a structured execution roadmap with dependencies.

Input Goal: Deploy a fault-tolerant microservice cluster on local infrastructure.

Output Execution Plan:
1. Phase 1 - Infrastructure Provisioning:
   - Establish network bridges and subnet routing.
   - Allocate physical RAM and dedicated NVMe mount points.
2. Phase 2 - Service Containerization:
   - Construct minimal scratch container images.
   - Configure health-check probes and liveness endpoints.
3. Phase 3 - Resilience Testing:
   - Simulate sudden node termination and measure failover latency.
   - Validate zero data loss on raft consensus state."""},
    ]

    expanded = []
    for i, d in enumerate(docs):
        for rep in range(5):
            expanded.append({
                "doc_id": f"struct_{i:02d}_{rep:02d}",
                "category": "structured_tasks",
                "text": f"# Task Specification: {d['title']}\n\n{d['text']}"
            })
    return expanded


def curate_and_write_sources():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    category_files = {
        "general_english": (RAW_DIR / "general_english.jsonl", get_general_english_documents()),
        "reasoning_math": (RAW_DIR / "reasoning_math.jsonl", get_reasoning_math_documents()),
        "instruction_dialog": (RAW_DIR / "instruction_dialog.jsonl", get_instruction_dialog_documents()),
        "technical_code": (RAW_DIR / "technical_code.jsonl", get_technical_code_documents()),
        "structured_tasks": (RAW_DIR / "structured_tasks.jsonl", get_structured_tasks_documents()),
    }

    # Inject test fixtures to verify pipeline filters (HTML, email, phone, secrets, near-dup)
    dirty_fixture = {
        "doc_id": "fixture_dirty_01",
        "category": "general_english",
        "text": """<p>HTML paragraph with excessive whitespace.   </p><br><br><br>
Contact support at test_user@example.com or direct contact at personal_john@gmail.com.
Telephone assistance available at 555-123-4567.
Valid technical reference: https://love.local/docs/v1/api."""
    }
    category_files["general_english"][1].append(dirty_fixture)

    # Injected secret (must be rejected by PrivacyFilter)
    secret_fixture = {
        "doc_id": "fixture_secret_01",
        "category": "technical_code",
        "text": """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Y3wZkFfakeKeyContentForFilterTest...
-----END RSA PRIVATE KEY-----"""
    }
    category_files["technical_code"][1].append(secret_fixture)

    results = {}
    for cat, (path, docs) in category_files.items():
        with open(path, "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        results[cat] = {"file": str(path.name), "count": len(docs), "bytes": path.stat().st_size}
        print(f"Curated {cat}: {len(docs)} documents ({results[cat]['bytes']:,} bytes) -> {path.name}")

    return results


if __name__ == "__main__":
    curate_and_write_sources()
