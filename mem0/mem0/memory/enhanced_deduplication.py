"""
Enhanced deduplication algorithms for autonomous AI memory storage.
This module provides advanced deduplication logic optimized for coding contexts.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


from mem0.configs.coding_config import CodingFactExtractor
from mem0.memory.timezone_utils import safe_datetime_diff

logger = logging.getLogger(__name__)


class EnhancedDeduplicator:
    """
    Enhanced deduplication system for autonomous AI memory storage.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.fact_extractor = CodingFactExtractor()

        # Deduplication parameters
        self.similarity_thresholds = {
            "bug_fix": 0.9,  # High threshold for critical bug fixes
            "error_solution": 0.92,  # Very high for error solutions
            "architecture": 0.8,  # Medium for architectural decisions
            "performance": 0.85,  # High for performance optimizations
            "configuration": 0.88,  # High for configuration details
            "testing": 0.82,  # Medium-high for testing approaches
            "debugging": 0.85,  # High for debugging techniques
            "deployment": 0.88,  # High for deployment procedures
            "documentation": 0.75,  # Lower for documentation
            "refactoring": 0.8,  # Medium for refactoring
            "code_implementation": 0.83,  # Medium-high for general code
            "general": 0.85,  # Default threshold
        }

        # Semantic similarity patterns
        self.semantic_patterns = {
            "error_patterns": [
                "error",
                "exception",
                "crash",
                "fail",
                "bug",
                "issue",
                "problem",
                "fault",
                "defect",
                "malfunction",
            ],
            "solution_patterns": [
                "fix",
                "solve",
                "resolve",
                "solution",
                "answer",
                "workaround",
                "patch",
                "correct",
                "repair",
            ],
            "implementation_patterns": [
                "implement",
                "create",
                "build",
                "develop",
                "code",
                "write",
                "add",
                "construct",
                "make",
            ],
            "optimization_patterns": [
                "optimize",
                "improve",
                "enhance",
                "speed",
                "performance",
                "efficient",
                "faster",
                "better",
                "reduce",
            ],
        }

        # Context-aware deduplication cache
        self.dedup_cache = {}
        self.pattern_cache = {}

        logger.info("Enhanced deduplicator initialized")

    def should_deduplicate(
        self,
        new_fact: str,
        existing_memories: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Tuple[bool, Optional[str], float]:
        """
        Determine if a new fact should be deduplicated against existing memories.

        Args:
            new_fact: The new fact to check
            existing_memories: List of existing memories to compare against
            metadata: Metadata for the new fact

        Returns:
            Tuple of (should_deduplicate, duplicate_id, similarity_score)
        """
        if not existing_memories:
            return False, None, 0.0

        # Get category-specific threshold
        category = metadata.get("category", "general")
        threshold = self.similarity_thresholds.get(category, 0.85)

        # Apply context-aware deduplication
        for memory in existing_memories:
            similarity = self._calculate_enhanced_similarity(
                new_fact,
                memory.get("memory", memory.get("text", "")),
                metadata,
                memory.get("metadata", {}),
            )

            if similarity >= threshold:
                # Check if this is a meaningful duplicate
                if self._is_meaningful_duplicate(new_fact, memory, metadata, similarity):
                    return True, memory.get("id"), similarity

        return False, None, 0.0

    def _calculate_enhanced_similarity(
        self,
        fact1: str,
        fact2: str,
        metadata1: Dict[str, Any],
        metadata2: Dict[str, Any],
    ) -> float:
        """
        Calculate enhanced similarity between two facts using multiple methods.
        """
        # Base similarity (would normally use vector embeddings)
        base_similarity = self._calculate_text_similarity(fact1, fact2)

        # Context-aware adjustments
        context_boost = self._calculate_context_similarity(metadata1, metadata2)

        # Semantic pattern matching
        semantic_boost = self._calculate_semantic_similarity(fact1, fact2)

        # Temporal relevance (newer facts are less likely to be duplicates)
        temporal_factor = self._calculate_temporal_factor(metadata1, metadata2)

        # Combine all factors
        enhanced_similarity = (base_similarity * 0.6 + context_boost * 0.2 + semantic_boost * 0.2) * temporal_factor

        return min(enhanced_similarity, 1.0)

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate basic text similarity (simplified version).
        In production, this would use actual vector embeddings.
        """
        # Simple Jaccard similarity for demonstration
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _calculate_context_similarity(self, metadata1: Dict[str, Any], metadata2: Dict[str, Any]) -> float:
        """
        Calculate context similarity between two memories.
        """
        context_score = 0.0

        # Category similarity
        cat1 = metadata1.get("category", "general")
        cat2 = metadata2.get("category", "general")
        if cat1 == cat2:
            context_score += 0.5

        # File reference similarity
        files1 = set(metadata1.get("file_references", []))
        files2 = set(metadata2.get("file_references", []))
        if files1 and files2:
            file_similarity = len(files1.intersection(files2)) / len(files1.union(files2))
            context_score += file_similarity * 0.3

        # Error/solution relationship
        error1 = metadata1.get("error_related", False)
        error2 = metadata2.get("error_related", False)
        solution1 = metadata1.get("solution_related", False)
        solution2 = metadata2.get("solution_related", False)

        if error1 == error2 and solution1 == solution2:
            context_score += 0.2

        return min(context_score, 1.0)

    def _calculate_semantic_similarity(self, fact1: str, fact2: str) -> float:
        """
        Calculate semantic similarity using pattern matching.
        """
        fact1_lower = fact1.lower()
        fact2_lower = fact2.lower()

        semantic_score = 0.0

        # Check for semantic patterns
        for pattern_type, patterns in self.semantic_patterns.items():
            count1 = sum(1 for pattern in patterns if pattern in fact1_lower)
            count2 = sum(1 for pattern in patterns if pattern in fact2_lower)

            if count1 > 0 and count2 > 0:
                # Both facts contain patterns from the same category
                semantic_score += 0.25

        return min(semantic_score, 1.0)

    def _calculate_temporal_factor(self, metadata1: Dict[str, Any], metadata2: Dict[str, Any]) -> float:
        """
        Calculate temporal relevance factor.
        """
        # If we don't have timestamps, assume they're recent
        created1 = metadata1.get("created_at")
        created2 = metadata2.get("created_at")

        if not created1 or not created2:
            return 1.0

        try:
            # Parse timestamps
            time1 = datetime.fromisoformat(created1.replace("Z", "+00:00"))
            time2 = datetime.fromisoformat(created2.replace("Z", "+00:00"))

            # Calculate time difference
            time_diff = abs(safe_datetime_diff(time1, time2).total_seconds())

            # Apply decay factor (memories from the same session are more likely duplicates)
            if time_diff < 300:  # Within 5 minutes
                return 1.0
            elif time_diff < 3600:  # Within 1 hour
                return 0.9
            elif time_diff < 86400:  # Within 1 day
                return 0.8
            else:  # Older than 1 day
                return 0.7

        except Exception:
            return 1.0

    def _is_meaningful_duplicate(
        self,
        new_fact: str,
        existing_memory: Dict[str, Any],
        metadata: Dict[str, Any],
        similarity: float,
    ) -> bool:
        """
        Determine if a high similarity score represents a meaningful duplicate.
        """
        # Check for exact duplicates
        if new_fact.strip() == existing_memory.get("memory", "").strip():
            return True

        # Check for trivial differences
        if self._is_trivial_variation(new_fact, existing_memory.get("memory", "")):
            return True

        # Check for complementary information
        if self._is_complementary_information(new_fact, existing_memory, metadata):
            return False  # Don't deduplicate complementary info

        # Check for progressive refinement
        if self._is_progressive_refinement(new_fact, existing_memory, metadata):
            return False  # Don't deduplicate refinements

        return similarity >= 0.9  # High threshold for meaningful duplicates

    def _is_trivial_variation(self, fact1: str, fact2: str) -> bool:
        """
        Check if two facts are trivial variations of each other.
        """
        # Remove common variations
        variations = [
            ("the ", ""),
            ("a ", ""),
            ("an ", ""),
            (" is ", " "),
            (" are ", " "),
            (" was ", " "),
            (" were ", " "),
            (".", ""),
            (",", ""),
            ("!", ""),
            ("?", ""),
        ]

        normalized1 = fact1.lower().strip()
        normalized2 = fact2.lower().strip()

        for old, new in variations:
            normalized1 = normalized1.replace(old, new)
            normalized2 = normalized2.replace(old, new)

        # Check if they're identical after normalization
        return normalized1 == normalized2

    def _is_complementary_information(
        self, new_fact: str, existing_memory: Dict[str, Any], metadata: Dict[str, Any]
    ) -> bool:
        """
        Check if new fact provides complementary information to existing memory.
        """
        existing_memory.get("memory", "")

        # Check for error-solution pairs
        new_error = metadata.get("error_related", False)
        existing_error = existing_memory.get("metadata", {}).get("error_related", False)
        new_solution = metadata.get("solution_related", False)
        existing_solution = existing_memory.get("metadata", {}).get("solution_related", False)

        # If one is error and other is solution, they're complementary
        if (new_error and existing_solution) or (new_solution and existing_error):
            return True

        # Check for different file references
        new_files = set(metadata.get("file_references", []))
        existing_files = set(existing_memory.get("metadata", {}).get("file_references", []))

        if new_files and existing_files and not new_files.intersection(existing_files):
            return True  # Different files = complementary

        return False

    def _is_progressive_refinement(
        self, new_fact: str, existing_memory: Dict[str, Any], metadata: Dict[str, Any]
    ) -> bool:
        """
        Check if new fact is a progressive refinement of existing memory.
        """
        existing_fact = existing_memory.get("memory", "")

        # Check if new fact is longer and contains existing fact
        if len(new_fact) > len(existing_fact) * 1.5:
            if existing_fact.lower() in new_fact.lower():
                return True

        # Check for version improvements
        version_indicators = [
            "improved",
            "enhanced",
            "optimized",
            "better",
            "updated",
            "refined",
            "advanced",
            "upgraded",
            "modified",
        ]

        if any(indicator in new_fact.lower() for indicator in version_indicators):
            return True

        return False

    def get_deduplication_stats(self) -> Dict[str, Any]:
        """
        Get statistics about deduplication performance.
        """
        return {
            "thresholds": self.similarity_thresholds,
            "cache_size": len(self.dedup_cache),
            "pattern_cache_size": len(self.pattern_cache),
            "semantic_patterns": len(self.semantic_patterns),
        }

    def update_threshold(self, category: str, threshold: float):
        """
        Update similarity threshold for a specific category.
        """
        if 0.0 <= threshold <= 1.0:
            self.similarity_thresholds[category] = threshold
            logger.info(f"Updated threshold for {category} to {threshold}")
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")

    def clear_cache(self):
        """
        Clear deduplication cache.
        """
        self.dedup_cache.clear()
        self.pattern_cache.clear()
        logger.info("Deduplication cache cleared")


class AutonomousDeduplicationManager:
    """
    Manages deduplication for autonomous AI agents with adaptive thresholds.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.deduplicator = EnhancedDeduplicator(config)

        # Adaptive parameters
        self.false_positive_rate = 0.0
        self.false_negative_rate = 0.0
        self.total_evaluations = 0

        # Learning parameters
        self.learning_rate = 0.1
        self.adaptation_threshold = 10  # Number of evaluations before adapting

        # Performance tracking
        self.performance_metrics = {
            "duplicates_found": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "total_processed": 0,
            "average_similarity": 0.0,
        }

    def process_memory(
        self,
        new_fact: str,
        existing_memories: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a new memory for deduplication with autonomous adaptation.
        """
        # Check for deduplication
        should_dedup, duplicate_id, similarity = self.deduplicator.should_deduplicate(
            new_fact, existing_memories, metadata
        )

        # Update performance metrics
        self.performance_metrics["total_processed"] += 1

        if should_dedup:
            self.performance_metrics["duplicates_found"] += 1

        # Record for adaptive learning
        self._record_evaluation(should_dedup, similarity, metadata)

        return {
            "should_deduplicate": should_dedup,
            "duplicate_id": duplicate_id,
            "similarity_score": similarity,
            "confidence": self._calculate_confidence(similarity, metadata),
            "reasoning": self._generate_reasoning(should_dedup, similarity, metadata),
        }

    def _record_evaluation(self, should_dedup: bool, similarity: float, metadata: Dict[str, Any]):
        """
        Record evaluation for adaptive learning.
        """
        self.total_evaluations += 1

        # Update average similarity
        current_avg = self.performance_metrics["average_similarity"]
        self.performance_metrics["average_similarity"] = (
            current_avg * (self.total_evaluations - 1) + similarity
        ) / self.total_evaluations

        # Adapt thresholds periodically
        if self.total_evaluations % self.adaptation_threshold == 0:
            self._adapt_thresholds()

    def _adapt_thresholds(self):
        """
        Adapt similarity thresholds based on performance.
        """
        # Simple adaptive strategy
        if self.false_positive_rate > 0.1:  # Too many false positives
            # Increase thresholds to be more selective
            for category in self.deduplicator.similarity_thresholds:
                current = self.deduplicator.similarity_thresholds[category]
                adjusted = min(current + self.learning_rate * 0.1, 0.95)
                self.deduplicator.similarity_thresholds[category] = adjusted

        elif self.false_negative_rate > 0.15:  # Too many false negatives
            # Decrease thresholds to be more inclusive
            for category in self.deduplicator.similarity_thresholds:
                current = self.deduplicator.similarity_thresholds[category]
                adjusted = max(current - self.learning_rate * 0.1, 0.7)
                self.deduplicator.similarity_thresholds[category] = adjusted

        logger.info(f"Adapted thresholds after {self.total_evaluations} evaluations")

    def _calculate_confidence(self, similarity: float, metadata: Dict[str, Any]) -> float:
        """
        Calculate confidence in deduplication decision.
        """
        # Base confidence from similarity
        base_confidence = abs(similarity - 0.5) * 2  # Distance from uncertain middle

        # Adjust for category reliability
        category = metadata.get("category", "general")
        category_reliability = {
            "bug_fix": 0.9,
            "error_solution": 0.95,
            "architecture": 0.8,
            "performance": 0.85,
            "general": 0.7,
        }

        reliability = category_reliability.get(category, 0.7)

        return min(base_confidence * reliability, 1.0)

    def _generate_reasoning(self, should_dedup: bool, similarity: float, metadata: Dict[str, Any]) -> str:
        """
        Generate human-readable reasoning for deduplication decision.
        """
        category = metadata.get("category", "general")
        threshold = self.deduplicator.similarity_thresholds.get(category, 0.85)

        if should_dedup:
            return f"Similarity {similarity:.3f} exceeds threshold {threshold:.3f} for {category}"
        else:
            return f"Similarity {similarity:.3f} below threshold {threshold:.3f} for {category}"

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.
        """
        return {
            "metrics": self.performance_metrics,
            "thresholds": self.deduplicator.similarity_thresholds,
            "adaptation_stats": {
                "false_positive_rate": self.false_positive_rate,
                "false_negative_rate": self.false_negative_rate,
                "total_evaluations": self.total_evaluations,
                "learning_rate": self.learning_rate,
            },
            "deduplication_stats": self.deduplicator.get_deduplication_stats(),
        }

    def reset_performance_metrics(self):
        """
        Reset performance metrics for fresh tracking.
        """
        self.performance_metrics = {
            "duplicates_found": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "total_processed": 0,
            "average_similarity": 0.0,
        }
        self.total_evaluations = 0
        logger.info("Performance metrics reset")


# Utility functions for deduplication
def calculate_content_hash(content: str) -> str:
    """
    Calculate content hash for fast duplicate detection.
    """
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def extract_key_features(fact: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key features for deduplication comparison.
    """
    features = {
        "content_hash": calculate_content_hash(fact),
        "length": len(fact),
        "word_count": len(fact.split()),
        "category": metadata.get("category", "general"),
        "has_code": metadata.get("contains_code", False),
        "error_related": metadata.get("error_related", False),
        "solution_related": metadata.get("solution_related", False),
        "file_references": metadata.get("file_references", []),
    }

    return features


def similarity_based_clustering(
    memories: List[Dict[str, Any]], similarity_threshold: float = 0.8
) -> List[List[Dict[str, Any]]]:
    """
    Cluster memories based on similarity for batch deduplication.
    """
    clusters = []
    processed = set()

    for i, memory in enumerate(memories):
        if i in processed:
            continue

        cluster = [memory]
        processed.add(i)

        # Find similar memories
        for j, other_memory in enumerate(memories):
            if j <= i or j in processed:
                continue

            # Calculate similarity (simplified)
            similarity = calculate_simple_similarity(memory.get("memory", ""), other_memory.get("memory", ""))

            if similarity >= similarity_threshold:
                cluster.append(other_memory)
                processed.add(j)

        clusters.append(cluster)

    return clusters


def calculate_simple_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple similarity between two texts.
    """
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0
