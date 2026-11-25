"""Domain-Weighted Dataset Sampling Engine for LOVE Native AI.

Implements Section 4 (NAI-04):
- Configurable sampling modes: domain_weighted, uniform, natural.
- Active domain categories:
  - english_synthetic_stories
  - instruction_dialog
  - reasoning_math
  - general_english
  - structured_tasks
  - technical_code (strictly absent until licensed source approved, weight 0.0)
- Reproducible random seed control.
- Sample repetition tracking and domain consumption statistics.
"""
import random
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from native_ai.data_cache.binary_cache import BinaryTokenDataset, CATEGORY_MAP, REV_CATEGORY_MAP

DEFAULT_DOMAIN_WEIGHTS = {
    "english_synthetic_stories": 0.40,
    "instruction_dialog": 0.35,
    "reasoning_math": 0.23,
    "general_english": 0.015,
    "structured_tasks": 0.005,
    "technical_code": 0.0,  # Strictly absent
}


class DomainWeightedSampler:
    """Configurable domain sampler supporting domain-weighted, uniform, and natural sampling."""

    def __init__(
        self,
        dataset: BinaryTokenDataset,
        mode: str = "domain_weighted",
        custom_weights: Optional[Dict[str, float]] = None,
        seed: int = 42,
    ):
        self.dataset = dataset
        self.mode = mode.lower()
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # Identify active categories (categories with > 0 documents in dataset)
        self.category_doc_map: Dict[str, np.ndarray] = {}
        self.active_categories: List[str] = []
        for cat_name, cat_code in CATEGORY_MAP.items():
            doc_indices = dataset.get_doc_indices_for_category(cat_name)
            self.category_doc_map[cat_name] = doc_indices
            if len(doc_indices) > 0:
                self.active_categories.append(cat_name)

        # Enforce that absent categories (e.g. technical_code) have 0 weight
        self.category_probabilities = self._compute_probabilities(custom_weights)

        # Tracking telemetry
        self.telemetry = {
            "samples_generated": 0,
            "tokens_generated": 0,
            "category_sample_counts": {k: 0 for k in CATEGORY_MAP},
            "category_token_counts": {k: 0 for k in CATEGORY_MAP},
            "doc_access_counts": {},  # doc_idx -> access_count
        }

    def _compute_probabilities(self, custom_weights: Optional[Dict[str, float]]) -> Dict[str, float]:
        """Calculates normalized sampling probabilities across active categories."""
        if self.mode == "uniform":
            n = len(self.active_categories)
            if n == 0:
                return {}
            prob = 1.0 / n
            return {c: prob if c in self.active_categories else 0.0 for c in CATEGORY_MAP}

        elif self.mode == "natural":
            # Probability proportional to total token count of each category
            total_tokens = len(self.dataset)
            probs = {}
            for c in CATEGORY_MAP:
                if c in self.active_categories:
                    doc_idxs = self.category_doc_map[c]
                    cat_tokens = sum(self.dataset.offsets[i, 1] for i in doc_idxs)
                    probs[c] = cat_tokens / total_tokens if total_tokens > 0 else 0.0
                else:
                    probs[c] = 0.0
            return probs

        elif self.mode == "domain_weighted":
            weights = dict(custom_weights or DEFAULT_DOMAIN_WEIGHTS)
            # Ensure absent categories have 0 weight
            for c in CATEGORY_MAP:
                if c not in self.active_categories:
                    weights[c] = 0.0

            active_sum = sum(weights.get(c, 0.0) for c in self.active_categories)
            if active_sum <= 0:
                raise ValueError("Sum of active category weights must be greater than 0")

            probs = {}
            for c in CATEGORY_MAP:
                if c in self.active_categories:
                    probs[c] = weights.get(c, 0.0) / active_sum
                else:
                    probs[c] = 0.0
            return probs

        else:
            raise ValueError(f"Unknown sampling mode: {self.mode}. Choose 'domain_weighted', 'uniform', or 'natural'")

    def sample_document(self) -> Tuple[int, np.ndarray, str]:
        """
        Samples a single document according to the active probability distribution.
        Returns: (doc_idx, token_array, category_name)
        """
        # Choose category according to probabilities
        categories = list(self.category_probabilities.keys())
        p_values = [self.category_probabilities[c] for c in categories]

        chosen_cat = self.rng.choice(categories, p=p_values)
        cat_doc_indices = self.category_doc_map[chosen_cat]
        if len(cat_doc_indices) == 0:
            raise RuntimeError(f"Cannot sample from category '{chosen_cat}' with 0 documents")

        # Uniformly choose a document within the chosen category
        doc_idx = int(self.rng.choice(cat_doc_indices))
        tokens, cat_name = self.dataset.get_document(doc_idx)

        # Update telemetry
        self.telemetry["samples_generated"] += 1
        self.telemetry["tokens_generated"] += len(tokens)
        self.telemetry["category_sample_counts"][chosen_cat] += 1
        self.telemetry["category_token_counts"][chosen_cat] += len(tokens)
        self.telemetry["doc_access_counts"][doc_idx] = self.telemetry["doc_access_counts"].get(doc_idx, 0) + 1

        return doc_idx, tokens, chosen_cat

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns sampling distribution statistics and repetition metrics."""
        total_samples = self.telemetry["samples_generated"]
        total_tokens = self.telemetry["tokens_generated"]

        sample_pcts = {
            k: round(v / total_samples * 100, 2) if total_samples > 0 else 0.0
            for k, v in self.telemetry["category_sample_counts"].items()
        }
        token_pcts = {
            k: round(v / total_tokens * 100, 2) if total_tokens > 0 else 0.0
            for k, v in self.telemetry["category_token_counts"].items()
        }

        # Repetition metrics
        access_values = list(self.telemetry["doc_access_counts"].values())
        max_rep = max(access_values) if access_values else 0
        avg_rep = round(np.mean(access_values), 2) if access_values else 0.0
        unique_docs = len(access_values)

        return {
            "mode": self.mode,
            "target_probabilities": self.category_probabilities,
            "samples_generated": total_samples,
            "tokens_generated": total_tokens,
            "unique_documents_accessed": unique_docs,
            "max_document_repetition": max_rep,
            "average_document_repetition": avg_rep,
            "actual_sample_percentages": sample_pcts,
            "actual_token_percentages": token_pcts,
        }
