"""
Coding-specific memory configuration optimizations for autonomous AI agents.
This module extends the base MemoryConfig with parameters tuned for coding contexts.
"""

import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from mem0.configs.base import MemoryConfig


class CodingMemoryConfig(MemoryConfig):
    """
    Enhanced memory configuration optimized for coding contexts and autonomous AI agents.
    """

    # Coding-specific fact extraction parameters
    coding_fact_extraction_prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt optimized for extracting coding-relevant facts",
    )

    # Enhanced deduplication parameters
    coding_similarity_threshold: float = Field(
        default=0.85,
        description="Higher threshold for coding contexts to reduce redundant storage",
    )

    # Context-aware storage prioritization
    coding_context_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "code_snippet": 1.0,
            "error_solution": 0.9,
            "architectural_decision": 0.8,
            "configuration": 0.7,
            "debugging_note": 0.6,
            "general_comment": 0.3,
        },
        description="Weights for different types of coding contexts",
    )

    # Autonomous usage parameters
    autonomous_storage_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_memories_per_session": 50,
            "context_window_size": 20,
            "relevance_decay_factor": 0.1,
            "auto_consolidation_threshold": 0.7,
        },
        description="Parameters for autonomous AI agent memory management",
    )

    # Coding-specific categories
    coding_categories: List[str] = Field(
        default_factory=lambda: [
            "code_implementation",
            "bug_fix",
            "architecture",
            "configuration",
            "debugging",
            "performance",
            "testing",
            "deployment",
            "documentation",
            "refactoring",
        ],
        description="Predefined categories for coding contexts",
    )

    # Enhanced metadata configuration
    coding_metadata_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "auto_tag_code_blocks": True,
            "extract_file_references": True,
            "track_solution_effectiveness": True,
            "store_context_relationships": True,
            "priority_boost_for_errors": 0.2,
        },
        description="Configuration for coding-specific metadata handling",
    )

    # Performance optimization parameters
    coding_performance_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "batch_size": 10,
            "parallel_processing": True,
            "cache_frequent_patterns": True,
            "optimize_for_retrieval_speed": True,
            "enable_predictive_caching": True,
        },
        description="Performance optimizations for coding contexts",
    )


class CodingFactExtractor:
    """
    Coding-specific fact extraction logic for autonomous AI agents.
    """

    @staticmethod
    def get_coding_fact_extraction_prompt() -> str:
        """
        Returns an optimized prompt for extracting coding-relevant facts.
        """
        return """You are an expert code analyst extracting key information from coding conversations.

        Focus on extracting facts that are valuable for autonomous AI coding agents:

        1. **Code Solutions**: Working implementations, algorithms, patterns
        2. **Bug Fixes**: Error descriptions, root causes, solutions
        3. **Architecture**: Design decisions, patterns, trade-offs
        4. **Configuration**: Setup instructions, environment details
        5. **Performance**: Optimization techniques, bottlenecks
        6. **Testing**: Test approaches, edge cases, validation methods

        Prioritize information that:
        - Provides actionable solutions
        - Prevents future errors
        - Improves code quality
        - Enhances development efficiency

        Format as JSON with 'facts' array containing extracted information.
        Each fact should be concise but complete for autonomous decision-making.

        Example:
        {
            "facts": [
                "React useEffect cleanup prevents memory leaks by returning cleanup function",
                "PostgreSQL JSONB indexing improves query performance for metadata searches",
                "Docker multi-stage builds reduce image size by 60% for Node.js applications"
            ]
        }
        """

    @staticmethod
    def categorize_coding_fact(fact: str) -> str:
        """
        Automatically categorize a coding fact based on its content.
        """
        fact_lower = fact.lower()

        # Pattern matching for automatic categorization
        if any(
            keyword in fact_lower
            for keyword in ["error", "bug", "fix", "crash", "exception"]
        ):
            return "bug_fix"
        elif any(
            keyword in fact_lower
            for keyword in ["architecture", "design", "pattern", "structure"]
        ):
            return "architecture"
        elif any(
            keyword in fact_lower
            for keyword in ["config", "setup", "environment", "deploy"]
        ):
            return "configuration"
        elif any(
            keyword in fact_lower
            for keyword in ["performance", "optimize", "speed", "memory"]
        ):
            return "performance"
        elif any(
            keyword in fact_lower
            for keyword in ["test", "testing", "validation", "verify"]
        ):
            return "testing"
        elif any(
            keyword in fact_lower
            for keyword in ["debug", "trace", "log", "investigate"]
        ):
            return "debugging"
        elif any(
            keyword in fact_lower
            for keyword in ["refactor", "cleanup", "improve", "restructure"]
        ):
            return "refactoring"
        else:
            return "code_implementation"

    @staticmethod
    def extract_coding_metadata(fact: str) -> Dict[str, Any]:
        """
        Extract coding-specific metadata from a fact.
        """
        metadata = {}

        # Extract file references
        import re

        file_patterns = [
            r"(\w+\.\w+)",  # filename.ext
            r"(/[\w/]+\.\w+)",  # /path/to/file.ext
            r"(\w+/[\w/]+\.\w+)",  # relative/path/file.ext
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, fact)
            if matches:
                metadata["file_references"] = list(set(matches))
                break

        # Extract code indicators
        if "```" in fact or "function" in fact.lower() or "class" in fact.lower():
            metadata["contains_code"] = True

        # Extract error indicators
        if any(
            keyword in fact.lower()
            for keyword in ["error", "exception", "failed", "crash"]
        ):
            metadata["error_related"] = True
            metadata["priority_boost"] = 0.2

        # Extract solution indicators
        if any(
            keyword in fact.lower()
            for keyword in ["solution", "fix", "resolved", "works"]
        ):
            metadata["solution_related"] = True
            metadata["priority_boost"] = 0.1

        return metadata


def create_coding_optimized_config(
    base_config: Optional[Dict[str, Any]] = None
) -> CodingMemoryConfig:
    """
    Create a coding-optimized memory configuration.

    Args:
        base_config: Optional base configuration to extend

    Returns:
        CodingMemoryConfig: Optimized configuration for coding contexts
    """
    config_dict = base_config or {}

    # Apply coding-specific optimizations
    coding_optimizations = {
        "custom_fact_extraction_prompt": CodingFactExtractor.get_coding_fact_extraction_prompt(),
        "api_version": "v1.1",  # Use latest API version
        "coding_similarity_threshold": 0.85,
        "coding_fact_extraction_prompt": CodingFactExtractor.get_coding_fact_extraction_prompt(),
    }

    # Merge with base configuration
    config_dict.update(coding_optimizations)

    return CodingMemoryConfig(**config_dict)


# Pre-configured coding contexts for common scenarios
CODING_CONTEXTS = {
    "bug_fixing": {
        "priority_weight": 0.9,
        "retention_days": 30,
        "similarity_threshold": 0.8,
        "categories": ["bug_fix", "debugging", "testing"],
    },
    "architecture": {
        "priority_weight": 0.8,
        "retention_days": 90,
        "similarity_threshold": 0.7,
        "categories": ["architecture", "design", "patterns"],
    },
    "performance": {
        "priority_weight": 0.7,
        "retention_days": 60,
        "similarity_threshold": 0.75,
        "categories": ["performance", "optimization", "profiling"],
    },
    "deployment": {
        "priority_weight": 0.6,
        "retention_days": 45,
        "similarity_threshold": 0.8,
        "categories": ["deployment", "configuration", "infrastructure"],
    },
}
