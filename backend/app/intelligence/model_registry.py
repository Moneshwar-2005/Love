"""
Model Registry for the Universal Intelligence Layer (Phase 03).
"""

from typing import Dict, List, Optional
from backend.app.intelligence.schemas import ModelCapabilities, ModelInfo


class ModelRegistry:
    """
    Catalog of known models, capability profiles, and hardware compatibility mappings.
    Maintains verified baseline configurations and dynamically ingested provider models.
    """

    def __init__(self):
        self._models: Dict[str, ModelInfo] = {}
        self._initialize_default_catalog()

    def _initialize_default_catalog(self) -> None:
        """Initializes known model profiles with capability ratings."""
        known_models = [
            # --- Ollama Local Models (GTX 1650 4GB VRAM Friendly) ---
            ModelInfo(
                id="llama3.2:3b",
                name="Llama 3.2 3B (Local)",
                provider="ollama",
                is_local=True,
                context_window=8192,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    context_window=8192,
                    coding_score=7,
                    reasoning_score=7,
                    creative_score=7,
                    speed_tier="fast",
                ),
                description="Ultra-fast local model optimized for 4GB VRAM GPUs (GTX 1650)."
            ),
            ModelInfo(
                id="llama3.2:1b",
                name="Llama 3.2 1B (Local)",
                provider="ollama",
                is_local=True,
                context_window=8192,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    context_window=8192,
                    coding_score=5,
                    reasoning_score=5,
                    creative_score=6,
                    speed_tier="fast",
                ),
                description="Lightweight local model with minimal RAM/VRAM footprint."
            ),
            ModelInfo(
                id="qwen2.5-coder:1.5b",
                name="Qwen 2.5 Coder 1.5B (Local)",
                provider="ollama",
                is_local=True,
                context_window=32768,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    context_window=32768,
                    coding_score=8,
                    reasoning_score=7,
                    creative_score=5,
                    speed_tier="fast",
                ),
                description="Specialized local code assistant fitting comfortably in 4GB VRAM."
            ),
            ModelInfo(
                id="qwen2.5-coder:7b",
                name="Qwen 2.5 Coder 7B (Local)",
                provider="ollama",
                is_local=True,
                context_window=32768,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    context_window=32768,
                    coding_score=9,
                    reasoning_score=8,
                    creative_score=6,
                    speed_tier="medium",
                ),
                description="Powerful local coding model (best with partial GPU offload or CPU)."
            ),
            ModelInfo(
                id="mistral:7b",
                name="Mistral 7B (Local)",
                provider="ollama",
                is_local=True,
                context_window=8192,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    context_window=8192,
                    coding_score=7,
                    reasoning_score=8,
                    creative_score=8,
                    speed_tier="medium",
                ),
                description="Well-rounded local reasoning and instruction model."
            ),

            # --- OpenAI Cloud Models ---
            ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                provider="openai",
                is_local=False,
                context_window=128000,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_tools=True,
                    supports_vision=True,
                    context_window=128000,
                    coding_score=10,
                    reasoning_score=10,
                    creative_score=9,
                    speed_tier="fast",
                ),
                description="Flagship OpenAI omni model with high intelligence and vision."
            ),
            ModelInfo(
                id="gpt-4o-mini",
                name="GPT-4o Mini",
                provider="openai",
                is_local=False,
                context_window=128000,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_tools=True,
                    supports_vision=True,
                    context_window=128000,
                    coding_score=8,
                    reasoning_score=8,
                    creative_score=8,
                    speed_tier="fast",
                ),
                description="Cost-efficient, fast reasoning model for general tasks."
            ),

            # --- Anthropic Cloud Models ---
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                name="Claude 3.5 Sonnet",
                provider="anthropic",
                is_local=False,
                context_window=200000,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_tools=True,
                    supports_vision=True,
                    context_window=200000,
                    coding_score=10,
                    reasoning_score=10,
                    creative_score=10,
                    speed_tier="fast",
                ),
                description="Industry-leading coding, architectural reasoning, and nuanced prose."
            ),
            ModelInfo(
                id="claude-3-5-haiku-20241022",
                name="Claude 3.5 Haiku",
                provider="anthropic",
                is_local=False,
                context_window=200000,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_tools=True,
                    supports_vision=False,
                    context_window=200000,
                    coding_score=8,
                    reasoning_score=8,
                    creative_score=8,
                    speed_tier="fast",
                ),
                description="Ultra-fast, responsive model for high-throughput tasks."
            ),

            # --- Google Gemini Cloud Models ---
            ModelInfo(
                id="gemini-flash-lite-latest",
                name="Gemini Flash Lite Latest",
                provider="gemini",
                is_local=False,
                context_window=1048576,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_tools=True,
                    supports_vision=True,
                    context_window=1048576,
                    coding_score=9,
                    reasoning_score=9,
                    creative_score=9,
                    speed_tier="fast",
                ),
                description="Ultra-fast, high-availability Google Gemini flagship model."
            ),
            ModelInfo(
                id="gemini-3.1-flash-lite",
                name="Gemini 3.1 Flash Lite",
                provider="gemini",
                is_local=False,
                context_window=1048576,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_tools=True,
                    supports_vision=True,
                    context_window=1048576,
                    coding_score=9,
                    reasoning_score=9,
                    creative_score=9,
                    speed_tier="fast",
                ),
                description="Modern lightweight Gemini model optimized for quick reasoning."
            ),
            ModelInfo(
                id="gemini-2.0-flash",
                name="Gemini 2.0 Flash",
                provider="gemini",
                is_local=False,
                context_window=1048576,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_tools=True,
                    supports_vision=True,
                    context_window=1048576,
                    coding_score=9,
                    reasoning_score=9,
                    creative_score=9,
                    speed_tier="fast",
                ),
                description="Next-generation multimodal model with ultra-large context and speed."
            ),
            ModelInfo(
                id="gemini-1.5-pro",
                name="Gemini 1.5 Pro",
                provider="gemini",
                is_local=False,
                context_window=2097152,
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_tools=True,
                    supports_vision=True,
                    context_window=2097152,
                    coding_score=9,
                    reasoning_score=10,
                    creative_score=9,
                    speed_tier="medium",
                ),
                description="Massive context window powerhouse for in-depth document and code analysis."
            ),
        ]

        for model in known_models:
            self._models[f"{model.provider}:{model.id}"] = model

    def register_model(self, model: ModelInfo) -> None:
        """Registers or updates a model profile in the registry."""
        key = f"{model.provider}:{model.id}"
        self._models[key] = model

    def get_model(self, provider_id: str, model_id: str) -> Optional[ModelInfo]:
        """Lookup model by provider and model ID."""
        key = f"{provider_id}:{model_id}"
        return self._models.get(key)

    def list_models(
        self,
        provider: Optional[str] = None,
        local_only: bool = False,
        available_only: bool = False
    ) -> List[ModelInfo]:
        """Filter and list registered models."""
        results = []
        for model in self._models.values():
            if provider and model.provider != provider:
                continue
            if local_only and not model.is_local:
                continue
            if available_only and not model.is_available:
                continue
            results.append(model)
        return results

    def get_best_model_for_task(
        self,
        provider_id: str,
        requires_coding: bool = False,
        requires_reasoning: bool = False
    ) -> Optional[ModelInfo]:
        """Finds the most suitable registered model for a given provider and task requirements."""
        candidates = [m for m in self._models.values() if m.provider == provider_id and m.is_available]
        if not candidates:
            return None

        def score(m: ModelInfo) -> int:
            pts = 0
            if requires_coding:
                pts += m.capabilities.coding_score * 2
            if requires_reasoning:
                pts += m.capabilities.reasoning_score * 2
            pts += m.capabilities.creative_score
            return pts

        candidates.sort(key=score, reverse=True)
        return candidates[0]
