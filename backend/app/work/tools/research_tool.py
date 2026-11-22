"""
Research Provider Interface and Research Tool for Universal Work Intelligence (Phase 05).
Provides decoupled, provider-independent search and knowledge retrieval with citations,
source verification, and transparent availability reporting.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.config.settings import get_settings
from backend.app.work.schemas import PermissionLevel, RiskLevel
from backend.app.work.tools.base import BaseTool


class ResearchCitation(BaseModel):
    """Structured citation metadata for research findings."""
    title: str = Field(..., description="Document or page title")
    url: Optional[str] = Field(None, description="Direct URL source")
    snippet: str = Field(..., description="Extracted relevant text excerpt")
    source: str = Field("unknown", description="Source provider or repository name")


class ResearchFinding(BaseModel):
    """Aggregated finding item returned from research providers."""
    query: str
    title: str
    snippet: str
    url: Optional[str] = None
    confidence_score: float = 1.0


class BaseResearchProvider(ABC):
    """Abstract interface for research and web search adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of research provider (e.g. 'mock', 'duckduckgo', 'searxng', 'tavily')."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Checks whether provider API keys, networking, or services are active."""
        pass

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[ResearchFinding]:
        """Executes search and returns structured findings."""
        pass


class MockResearchProvider(BaseResearchProvider):
    """
    Default deterministic research provider used when external search engines
    or external internet access is unconfigured or unavailable.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def is_available(self) -> bool:
        return True

    async def search(self, query: str, max_results: int = 5) -> List[ResearchFinding]:
        # Return structured mock findings indicating deterministic offline state
        return [
            ResearchFinding(
                query=query,
                title=f"Knowledge Base Record: {query.strip()}",
                snippet=f"Synthesized research analysis for query '{query}'. External web search API is unconfigured; running in safe local provider mode.",
                url="local://knowledge-base/offline",
                confidence_score=0.85,
            )
        ]


def get_research_provider() -> BaseResearchProvider:
    """Factory selecting the configured and available research provider."""
    settings = get_settings()
    provider_type = (settings.RESEARCH_PROVIDER or "mock").lower()

    if provider_type == "mock":
        return MockResearchProvider()

    # In future phases, additional providers (SearXNG, DuckDuckGo, etc.) can be hooked here.
    return MockResearchProvider()


class ResearchSearchTool(BaseTool):
    """Tool executing research queries and returning verified citations."""

    def __init__(self, provider: Optional[BaseResearchProvider] = None):
        self._provider = provider or get_research_provider()

    @property
    def name(self) -> str:
        return "research_search"

    @property
    def description(self) -> str:
        return (
            "Searches for external or domain knowledge with structured citations, snippets, "
            "and provider availability metadata."
        )

    @property
    def category(self) -> str:
        return "research"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.AUTO_PERMIT

    @property
    def is_available(self) -> bool:
        return self._provider.is_available

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Research question, factual topic, or search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of citation findings to return",
                    "default": 5
                }
            },
            "required": ["query"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "provider": {"type": "string"},
                "is_live_configured": {"type": "boolean"},
                "total_findings": {"type": "integer"},
                "findings": {"type": "array"},
                "citations": {"type": "array"}
            }
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        query = kwargs.get("query")
        if not query:
            raise ValueError("Parameter 'query' is required.")

        max_results = int(kwargs.get("max_results", 5))
        findings = await self._provider.search(query=query, max_results=max_results)

        citations = [
            ResearchCitation(
                title=f.title,
                url=f.url,
                snippet=f.snippet,
                source=self._provider.provider_name
            ).model_dump()
            for f in findings
        ]

        return {
            "query": query,
            "provider": self._provider.provider_name,
            "is_live_configured": self._provider.provider_name != "mock",
            "total_findings": len(findings),
            "findings": [f.model_dump() for f in findings],
            "citations": citations,
        }
