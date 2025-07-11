"""
Enhanced confidence scoring system for autonomous AI memory storage.
This module provides advanced confidence scoring optimized for coding contexts.
"""

import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

from mem0.configs.coding_config import CodingMemoryConfig
from mem0.memory.timezone_utils import (
    safe_datetime_now,
    safe_datetime_diff,
    get_memory_age_days,
)

logger = logging.getLogger(__name__)


class EnhancedConfidenceScorer:
    """
    Enhanced confidence scoring system for autonomous AI memory storage.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.coding_config = CodingMemoryConfig()

        # Confidence scoring parameters
        self.category_weights = {
            "bug_fix": 0.95,  # High confidence for bug fixes
            "error_solution": 0.98,  # Very high for error solutions
            "architecture": 0.85,  # Good for architectural decisions
            "performance": 0.90,  # High for performance optimizations
            "configuration": 0.88,  # High for configuration details
            "testing": 0.82,  # Medium-high for testing approaches
            "debugging": 0.87,  # High for debugging techniques
            "deployment": 0.85,  # Good for deployment procedures
            "documentation": 0.75,  # Lower for documentation
            "refactoring": 0.80,  # Medium for refactoring
            "code_implementation": 0.83,  # Medium-high for general code
            "general": 0.80,  # Default confidence
        }

        # Context-specific confidence factors
        self.context_factors = {
            "file_references": 0.15,  # Boost for file references
            "code_blocks": 0.12,  # Boost for code blocks
            "error_context": 0.18,  # Boost for error context
            "solution_context": 0.20,  # Boost for solution context
            "performance_metrics": 0.10,  # Boost for performance data
            "test_results": 0.08,  # Boost for test results
            "recent_activity": 0.15,  # Boost for recent activity
        }

        # Retrieval prioritization factors
        self.retrieval_factors = {
            "frequency_boost": 0.1,  # Boost for frequently accessed
            "recency_boost": 0.15,  # Boost for recently accessed
            "success_rate_boost": 0.12,  # Boost for high success rate
            "relevance_boost": 0.18,  # Boost for high relevance
        }

        # Performance tracking
        self.scoring_history = []
        self.accuracy_metrics = {
            "total_scores": 0,
            "correct_predictions": 0,
            "false_positives": 0,
            "false_negatives": 0,
        }

        logger.info("Enhanced confidence scorer initialized")

    def calculate_confidence(
        self,
        memory_content: str,
        metadata: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive confidence score for a memory.

        Args:
            memory_content: The memory content to score
            metadata: Memory metadata
            context: Optional context for scoring

        Returns:
            Dictionary containing confidence score and components
        """
        context = context or {}

        # Base confidence from category
        base_confidence = self._calculate_base_confidence(metadata)

        # Content quality assessment
        content_quality = self._assess_content_quality(memory_content, metadata)

        # Context-aware adjustments
        context_boost = self._calculate_context_boost(metadata, context)

        # Retrieval-specific factors
        retrieval_boost = self._calculate_retrieval_boost(metadata, context)

        # Temporal relevance
        temporal_factor = self._calculate_temporal_relevance(metadata)

        # Historical performance
        historical_factor = self._calculate_historical_factor(metadata)

        # Calculate final confidence
        final_confidence = min(
            (base_confidence + context_boost + retrieval_boost)
            * temporal_factor
            * historical_factor
            * content_quality,
            1.0,
        )

        # Record scoring
        self._record_scoring(final_confidence, metadata, context)

        return {
            "confidence": final_confidence,
            "components": {
                "base_confidence": base_confidence,
                "content_quality": content_quality,
                "context_boost": context_boost,
                "retrieval_boost": retrieval_boost,
                "temporal_factor": temporal_factor,
                "historical_factor": historical_factor,
            },
            "explanation": self._generate_explanation(
                final_confidence, metadata, context
            ),
        }

    def _calculate_base_confidence(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate base confidence from memory category.
        """
        category = metadata.get("category", "general")
        return self.category_weights.get(category, 0.80)

    def _assess_content_quality(self, content: str, metadata: Dict[str, Any]) -> float:
        """
        Assess the quality of memory content.
        """
        if not content or len(content.strip()) < 10:
            return 0.5  # Low quality for very short content

        quality_score = 0.7  # Base quality

        # Length factor (optimal length around 100-500 characters)
        length = len(content)
        if 50 <= length <= 1000:
            quality_score += 0.1
        elif length > 1000:
            quality_score += 0.05  # Diminishing returns for very long content

        # Specific content indicators
        quality_indicators = {
            "code_block": 0.15,  # Contains code
            "file_path": 0.10,  # Contains file paths
            "error_message": 0.12,  # Contains error messages
            "solution_steps": 0.18,  # Contains solution steps
            "configuration": 0.08,  # Contains configuration details
            "performance_data": 0.12,  # Contains performance metrics
        }

        content_lower = content.lower()
        for indicator, boost in quality_indicators.items():
            if any(
                keyword in content_lower
                for keyword in self._get_indicator_keywords(indicator)
            ):
                quality_score += boost

        return min(quality_score, 1.0)

    def _get_indicator_keywords(self, indicator: str) -> List[str]:
        """
        Get keywords for content quality indicators.
        """
        keywords = {
            "code_block": [
                "def ",
                "function",
                "class ",
                "import ",
                "from ",
                "{",
                "}",
                "()",
                "[]",
            ],
            "file_path": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", "/", "\\"],
            "error_message": [
                "error",
                "exception",
                "failed",
                "crash",
                "traceback",
                "stack trace",
            ],
            "solution_steps": [
                "step",
                "first",
                "then",
                "next",
                "finally",
                "solution",
                "fix",
            ],
            "configuration": [
                "config",
                "setting",
                "parameter",
                "option",
                "environment",
                "env",
            ],
            "performance_data": [
                "ms",
                "seconds",
                "memory",
                "cpu",
                "benchmark",
                "optimization",
            ],
        }
        return keywords.get(indicator, [])

    def _calculate_context_boost(
        self, metadata: Dict[str, Any], context: Dict[str, Any]
    ) -> float:
        """
        Calculate context-aware confidence boost.
        """
        boost = 0.0

        # File references boost
        if metadata.get("file_references"):
            boost += self.context_factors["file_references"]

        # Code blocks boost
        if metadata.get("code_blocks"):
            boost += self.context_factors["code_blocks"]

        # Error/solution context boost
        if metadata.get("error_related", False):
            boost += self.context_factors["error_context"]

        if metadata.get("solution_related", False):
            boost += self.context_factors["solution_context"]

        # Performance metrics boost
        if metadata.get("performance_metrics"):
            boost += self.context_factors["performance_metrics"]

        # Test results boost
        if metadata.get("test_results"):
            boost += self.context_factors["test_results"]

        # Recent activity boost
        if context.get("recent_activity", False):
            boost += self.context_factors["recent_activity"]

        return min(boost, 0.5)  # Cap boost at 0.5

    def _calculate_retrieval_boost(
        self, metadata: Dict[str, Any], context: Dict[str, Any]
    ) -> float:
        """
        Calculate retrieval-specific confidence boost.
        """
        boost = 0.0

        # Frequency boost
        access_count = metadata.get("access_count", 0)
        if access_count > 0:
            frequency_boost = min(
                math.log(access_count + 1) * 0.02,
                self.retrieval_factors["frequency_boost"],
            )
            boost += frequency_boost

        # Recency boost
        last_accessed = metadata.get("last_accessed")
        if last_accessed:
            recency_boost = self._calculate_recency_boost(last_accessed)
            boost += recency_boost

        # Success rate boost
        success_rate = metadata.get("success_rate", 0.0)
        if success_rate > 0:
            success_boost = success_rate * self.retrieval_factors["success_rate_boost"]
            boost += success_boost

        # Relevance boost from context
        relevance_score = context.get("relevance_score", 0.0)
        if relevance_score > 0:
            relevance_boost = (
                relevance_score * self.retrieval_factors["relevance_boost"]
            )
            boost += relevance_boost

        return min(boost, 0.4)  # Cap boost at 0.4

    def _calculate_recency_boost(self, last_accessed: str) -> float:
        """
        Calculate recency boost based on last access time.
        """
        try:
            last_time = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
            time_diff = safe_datetime_diff(
                safe_datetime_now(last_time), last_time
            ).total_seconds()

            # Exponential decay with half-life of 1 day
            decay_factor = math.exp(-time_diff / 86400)  # 86400 seconds in a day
            return decay_factor * self.retrieval_factors["recency_boost"]
        except Exception:
            return 0.0

    def _calculate_temporal_relevance(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate temporal relevance factor.
        """
        created_at = metadata.get("created_at")
        if not created_at:
            return 1.0

        try:
            created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age_days = get_memory_age_days(created_at)

            # Memories lose relevance over time, but level off
            if age_days <= 1:
                return 1.0
            elif age_days <= 7:
                return 0.95
            elif age_days <= 30:
                return 0.9
            elif age_days <= 90:
                return 0.85
            else:
                return 0.8
        except Exception:
            return 1.0

    def _calculate_historical_factor(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate historical performance factor.
        """
        # Use historical accuracy if available
        historical_accuracy = metadata.get("historical_accuracy", 0.8)

        # Use feedback scores if available
        feedback_scores = metadata.get("feedback_scores", [])
        if feedback_scores:
            avg_feedback = sum(feedback_scores) / len(feedback_scores)
            return (historical_accuracy + avg_feedback) / 2

        return historical_accuracy

    def _record_scoring(
        self, confidence: float, metadata: Dict[str, Any], context: Dict[str, Any]
    ):
        """
        Record confidence scoring for learning and adaptation.
        """
        self.scoring_history.append(
            {
                "confidence": confidence,
                "category": metadata.get("category", "general"),
                "timestamp": datetime.now().isoformat(),
                "context": context.copy(),
            }
        )

        # Keep only recent history
        if len(self.scoring_history) > 1000:
            self.scoring_history = self.scoring_history[-1000:]

        self.accuracy_metrics["total_scores"] += 1

    def _generate_explanation(
        self, confidence: float, metadata: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable explanation for confidence score.
        """
        category = metadata.get("category", "general")

        if confidence >= 0.9:
            level = "Very High"
        elif confidence >= 0.8:
            level = "High"
        elif confidence >= 0.7:
            level = "Medium"
        elif confidence >= 0.6:
            level = "Low"
        else:
            level = "Very Low"

        explanation = f"{level} confidence ({confidence:.2f}) for {category} memory"

        # Add specific reasons
        reasons = []
        if metadata.get("error_related", False):
            reasons.append("contains error context")
        if metadata.get("solution_related", False):
            reasons.append("contains solution context")
        if metadata.get("file_references"):
            reasons.append("has file references")
        if metadata.get("code_blocks"):
            reasons.append("contains code blocks")
        if context.get("recent_activity", False):
            reasons.append("recent activity")

        if reasons:
            explanation += f" due to: {', '.join(reasons)}"

        return explanation

    def update_feedback(self, memory_id: str, feedback_score: float):
        """
        Update confidence scoring based on feedback.
        """
        if not 0.0 <= feedback_score <= 1.0:
            raise ValueError("Feedback score must be between 0.0 and 1.0")

        # Update accuracy metrics
        if feedback_score >= 0.7:
            self.accuracy_metrics["correct_predictions"] += 1
        elif feedback_score < 0.3:
            self.accuracy_metrics["false_positives"] += 1

        logger.info(f"Updated feedback for memory {memory_id}: {feedback_score}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get confidence scoring performance metrics.
        """
        total_scores = self.accuracy_metrics["total_scores"]
        if total_scores == 0:
            return self.accuracy_metrics

        accuracy = self.accuracy_metrics["correct_predictions"] / total_scores

        return {
            **self.accuracy_metrics,
            "accuracy": accuracy,
            "avg_confidence": (
                sum(h["confidence"] for h in self.scoring_history)
                / len(self.scoring_history)
                if self.scoring_history
                else 0.0
            ),
            "category_distribution": self._get_category_distribution(),
        }

    def _get_category_distribution(self) -> Dict[str, int]:
        """
        Get distribution of scores by category.
        """
        distribution = {}
        for record in self.scoring_history:
            category = record["category"]
            distribution[category] = distribution.get(category, 0) + 1
        return distribution

    def adapt_scoring_parameters(self):
        """
        Adapt scoring parameters based on performance.
        """
        metrics = self.get_performance_metrics()
        accuracy = metrics.get("accuracy", 0.8)

        # Adapt category weights based on performance
        if accuracy < 0.7:
            # Lower all weights slightly
            for category in self.category_weights:
                self.category_weights[category] = max(
                    self.category_weights[category] * 0.95, 0.5
                )
        elif accuracy > 0.9:
            # Increase weights for high-performing categories
            for category in self.category_weights:
                self.category_weights[category] = min(
                    self.category_weights[category] * 1.02, 1.0
                )

        logger.info(f"Adapted scoring parameters based on accuracy: {accuracy:.3f}")

    def reset_metrics(self):
        """
        Reset performance metrics.
        """
        self.accuracy_metrics = {
            "total_scores": 0,
            "correct_predictions": 0,
            "false_positives": 0,
            "false_negatives": 0,
        }
        self.scoring_history.clear()
        logger.info("Confidence scoring metrics reset")


class ContextAwareConfidenceScorer:
    """
    Context-aware confidence scorer for autonomous AI agents.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_scorer = EnhancedConfidenceScorer(config)

        # Context-specific scoring profiles
        self.context_profiles = {
            "autonomous_coding": {
                "emphasize_accuracy": True,
                "boost_code_context": 0.2,
                "boost_error_solutions": 0.25,
                "penalize_uncertainty": 0.15,
            },
            "interactive_debugging": {
                "emphasize_recency": True,
                "boost_debug_context": 0.18,
                "boost_file_references": 0.15,
                "penalize_outdated": 0.1,
            },
            "knowledge_building": {
                "emphasize_completeness": True,
                "boost_documentation": 0.12,
                "boost_architecture": 0.15,
                "penalize_fragments": 0.08,
            },
        }

    def score_for_context(
        self,
        memory_content: str,
        metadata: Dict[str, Any],
        context_type: str = "autonomous_coding",
    ) -> Dict[str, Any]:
        """
        Score memory confidence for specific context.
        """
        # Get base confidence
        base_result = self.base_scorer.calculate_confidence(memory_content, metadata)

        # Apply context-specific adjustments
        context_profile = self.context_profiles.get(context_type, {})
        adjusted_confidence = self._apply_context_adjustments(
            base_result["confidence"], metadata, context_profile
        )

        return {
            **base_result,
            "context_adjusted_confidence": adjusted_confidence,
            "context_type": context_type,
            "context_profile": context_profile,
        }

    def _apply_context_adjustments(
        self, base_confidence: float, metadata: Dict[str, Any], profile: Dict[str, Any]
    ) -> float:
        """
        Apply context-specific adjustments to confidence score.
        """
        adjusted = base_confidence

        # Apply boosts
        if profile.get("boost_code_context") and metadata.get("code_blocks"):
            adjusted += profile["boost_code_context"]

        if profile.get("boost_error_solutions") and metadata.get("solution_related"):
            adjusted += profile["boost_error_solutions"]

        if profile.get("boost_debug_context") and metadata.get("error_related"):
            adjusted += profile["boost_debug_context"]

        if profile.get("boost_file_references") and metadata.get("file_references"):
            adjusted += profile["boost_file_references"]

        # Apply penalties
        if profile.get("penalize_uncertainty") and base_confidence < 0.6:
            adjusted -= profile["penalize_uncertainty"]

        if profile.get("penalize_outdated"):
            created_at = metadata.get("created_at")
            if created_at:
                try:
                    created_time = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    age_days = get_memory_age_days(created_at)
                    if age_days > 30:
                        adjusted -= profile["penalize_outdated"]
                except Exception:
                    pass

        return max(0.0, min(adjusted, 1.0))
