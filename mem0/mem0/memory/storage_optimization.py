"""
Enhanced storage optimization system for autonomous AI memory storage.
This module provides advanced storage limits and intelligent purging logic.
"""

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

from mem0.configs.coding_config import CodingMemoryConfig
from mem0.memory.timezone_utils import (
    create_memory_timestamp,
    safe_datetime_diff,
    safe_datetime_now,
)

logger = logging.getLogger(__name__)


class IntelligentStorageManager:
    """
    Intelligent storage management system for autonomous AI memory storage.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.coding_config = CodingMemoryConfig()

        # Storage limits configuration
        self.storage_limits = {
            "max_memories_total": config.get("max_memories_total", 10000),
            "max_memories_per_category": config.get("max_memories_per_category", 2000),
            "max_memories_per_session": config.get("max_memories_per_session", 50),
            "max_memory_size_bytes": config.get("max_memory_size_bytes", 10240),  # 10KB per memory
            "max_total_size_mb": config.get("max_total_size_mb", 100),  # 100MB total
            "warning_threshold": config.get("warning_threshold", 0.8),  # 80% capacity
            "critical_threshold": config.get("critical_threshold", 0.95),  # 95% capacity
        }

        # Retention policies by category
        self.retention_policies = {
            "bug_fix": {
                "max_age_days": 90,
                "min_retention_count": 100,
                "priority_weight": 0.9,
                "access_weight": 0.8,
            },
            "error_solution": {
                "max_age_days": 120,
                "min_retention_count": 150,
                "priority_weight": 0.95,
                "access_weight": 0.85,
            },
            "architecture": {
                "max_age_days": 180,
                "min_retention_count": 80,
                "priority_weight": 0.8,
                "access_weight": 0.7,
            },
            "performance": {
                "max_age_days": 60,
                "min_retention_count": 60,
                "priority_weight": 0.85,
                "access_weight": 0.75,
            },
            "testing": {
                "max_age_days": 45,
                "min_retention_count": 40,
                "priority_weight": 0.7,
                "access_weight": 0.6,
            },
            "debugging": {
                "max_age_days": 30,
                "min_retention_count": 50,
                "priority_weight": 0.8,
                "access_weight": 0.7,
            },
            "deployment": {
                "max_age_days": 90,
                "min_retention_count": 50,
                "priority_weight": 0.82,
                "access_weight": 0.75,
            },
            "configuration": {
                "max_age_days": 120,
                "min_retention_count": 80,
                "priority_weight": 0.88,
                "access_weight": 0.8,
            },
            "documentation": {
                "max_age_days": 365,
                "min_retention_count": 200,
                "priority_weight": 0.75,
                "access_weight": 0.6,
            },
            "refactoring": {
                "max_age_days": 60,
                "min_retention_count": 30,
                "priority_weight": 0.75,
                "access_weight": 0.65,
            },
            "code_implementation": {
                "max_age_days": 90,
                "min_retention_count": 100,
                "priority_weight": 0.8,
                "access_weight": 0.7,
            },
            "general": {
                "max_age_days": 30,
                "min_retention_count": 20,
                "priority_weight": 0.6,
                "access_weight": 0.5,
            },
        }

        # Purging strategies
        self.purging_strategies = {
            "lru": self._lru_purge,
            "priority_based": self._priority_based_purge,
            "context_aware": self._context_aware_purge,
            "hybrid": self._hybrid_purge,
        }

        # Storage monitoring
        self.storage_stats = {
            "total_memories": 0,
            "total_size_bytes": 0,
            "category_counts": defaultdict(int),
            "category_sizes": defaultdict(int),
            "last_purge_time": None,
            "purge_count": 0,
            "memories_purged": 0,
        }

        # Performance tracking
        self.performance_metrics = {
            "storage_efficiency": 0.0,
            "retrieval_speed": 0.0,
            "purge_effectiveness": 0.0,
            "memory_utilization": 0.0,
        }

        logger.info("Intelligent storage manager initialized")

    def check_storage_limits(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check current storage against limits and recommend actions.

        Args:
            memories: List of current memories

        Returns:
            Dictionary containing storage status and recommendations
        """
        # Calculate current usage
        current_stats = self._calculate_storage_stats(memories)

        # Check various limits
        limits_status = {}

        # Total memory count
        total_limit = self.storage_limits["max_memories_total"]
        total_usage = current_stats["total_memories"] / total_limit
        limits_status["total_memories"] = {
            "current": current_stats["total_memories"],
            "limit": total_limit,
            "usage_percent": total_usage * 100,
            "status": self._get_status_level(total_usage),
        }

        # Total size
        size_limit = self.storage_limits["max_total_size_mb"] * 1024 * 1024  # Convert to bytes
        size_usage = current_stats["total_size_bytes"] / size_limit
        limits_status["total_size"] = {
            "current_mb": current_stats["total_size_bytes"] / (1024 * 1024),
            "limit_mb": self.storage_limits["max_total_size_mb"],
            "usage_percent": size_usage * 100,
            "status": self._get_status_level(size_usage),
        }

        # Category limits
        category_limit = self.storage_limits["max_memories_per_category"]
        category_status = {}
        for category, count in current_stats["category_counts"].items():
            category_usage = count / category_limit
            category_status[category] = {
                "current": count,
                "limit": category_limit,
                "usage_percent": category_usage * 100,
                "status": self._get_status_level(category_usage),
            }

        limits_status["categories"] = category_status

        # Overall status
        max_usage = max(total_usage, size_usage)
        overall_status = self._get_status_level(max_usage)

        # Recommendations
        recommendations = self._generate_storage_recommendations(limits_status, overall_status, current_stats)

        return {
            "overall_status": overall_status,
            "limits_status": limits_status,
            "current_stats": current_stats,
            "recommendations": recommendations,
        }

    def _calculate_storage_stats(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate detailed storage statistics.
        """
        stats = {
            "total_memories": len(memories),
            "total_size_bytes": 0,
            "category_counts": defaultdict(int),
            "category_sizes": defaultdict(int),
            "avg_memory_size": 0,
            "oldest_memory": None,
            "newest_memory": None,
            "access_distribution": defaultdict(int),
        }

        if not memories:
            return stats

        total_size = 0
        oldest_time = None
        newest_time = None

        for memory in memories:
            # Calculate size
            memory_size = len(str(memory).encode("utf-8"))
            total_size += memory_size

            # Category stats
            category = memory.get("metadata", {}).get("category", "general")
            stats["category_counts"][category] += 1
            stats["category_sizes"][category] += memory_size

            # Time tracking
            created_at = memory.get("metadata", {}).get("created_at")
            if created_at:
                try:
                    created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if oldest_time is None or created_time < oldest_time:
                        oldest_time = created_time
                        stats["oldest_memory"] = memory.get("id")
                    if newest_time is None or created_time > newest_time:
                        newest_time = created_time
                        stats["newest_memory"] = memory.get("id")
                except Exception:
                    pass

            # Access pattern
            access_count = memory.get("metadata", {}).get("access_count", 0)
            access_bucket = min(access_count // 5, 10)  # Group by 5s, cap at 10
            stats["access_distribution"][access_bucket] += 1

        stats["total_size_bytes"] = total_size
        stats["avg_memory_size"] = total_size / len(memories) if memories else 0

        return stats

    def _get_status_level(self, usage_ratio: float) -> str:
        """
        Get status level based on usage ratio.
        """
        if usage_ratio >= self.storage_limits["critical_threshold"]:
            return "critical"
        elif usage_ratio >= self.storage_limits["warning_threshold"]:
            return "warning"
        else:
            return "normal"

    def _generate_storage_recommendations(
        self,
        limits_status: Dict[str, Any],
        overall_status: str,
        current_stats: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Generate storage optimization recommendations.
        """
        recommendations = []

        if overall_status == "critical":
            recommendations.append(
                {
                    "type": "immediate_action",
                    "priority": "high",
                    "action": "purge_memories",
                    "description": "Storage is at critical capacity. Immediate purging required.",
                    "estimated_savings": "10-20%",
                }
            )

        elif overall_status == "warning":
            recommendations.append(
                {
                    "type": "scheduled_action",
                    "priority": "medium",
                    "action": "optimize_storage",
                    "description": "Storage approaching capacity. Consider optimization.",
                    "estimated_savings": "5-10%",
                }
            )

        # Category-specific recommendations
        for category, status in limits_status.get("categories", {}).items():
            if status["status"] in ["warning", "critical"]:
                recommendations.append(
                    {
                        "type": "category_optimization",
                        "priority": ("medium" if status["status"] == "warning" else "high"),
                        "action": f"purge_category_{category}",
                        "description": f'Category "{category}" is at {status["usage_percent"]:.1f}% capacity.',
                        "estimated_savings": f"{status['current'] * 0.1:.0f} memories",
                    }
                )

        # Performance recommendations
        if current_stats["avg_memory_size"] > self.storage_limits["max_memory_size_bytes"]:
            recommendations.append(
                {
                    "type": "performance_optimization",
                    "priority": "low",
                    "action": "compress_large_memories",
                    "description": "Some memories are larger than optimal. Consider compression.",
                    "estimated_savings": "5-15%",
                }
            )

        return recommendations

    def optimize_storage(
        self,
        memories: List[Dict[str, Any]],
        strategy: str = "hybrid",
        target_reduction: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Optimize storage using specified strategy.

        Args:
            memories: List of memories to optimize
            strategy: Optimization strategy to use
            target_reduction: Target reduction percentage (0.0-1.0)

        Returns:
            Dictionary containing optimization results
        """
        if strategy not in self.purging_strategies:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Calculate current stats
        initial_stats = self._calculate_storage_stats(memories)

        # Determine target memory count
        target_count = int(initial_stats["total_memories"] * (1 - target_reduction))
        memories_to_remove = initial_stats["total_memories"] - target_count

        if memories_to_remove <= 0:
            return {
                "status": "no_optimization_needed",
                "memories_removed": 0,
                "size_saved_mb": 0,
                "strategy_used": strategy,
            }

        # Apply purging strategy
        purge_function = self.purging_strategies[strategy]
        memories_to_purge = purge_function(memories, memories_to_remove)

        # Calculate savings
        size_saved = sum(len(str(memory).encode("utf-8")) for memory in memories_to_purge)
        size_saved_mb = size_saved / (1024 * 1024)

        # Update statistics
        self.storage_stats["last_purge_time"] = create_memory_timestamp()
        self.storage_stats["purge_count"] += 1
        self.storage_stats["memories_purged"] += len(memories_to_purge)

        # Calculate performance impact
        performance_impact = self._calculate_performance_impact(initial_stats, memories_to_purge)

        return {
            "status": "optimization_completed",
            "memories_removed": len(memories_to_purge),
            "size_saved_mb": size_saved_mb,
            "strategy_used": strategy,
            "performance_impact": performance_impact,
            "purged_memory_ids": [mem.get("id") for mem in memories_to_purge if mem.get("id")],
        }

    def _lru_purge(self, memories: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Purge memories using Least Recently Used strategy.
        """
        # Sort by last access time
        sorted_memories = sorted(
            memories,
            key=lambda m: m.get("metadata", {}).get("last_accessed", "1970-01-01T00:00:00Z"),
        )

        return sorted_memories[:count]

    def _priority_based_purge(self, memories: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Purge memories using priority-based strategy.
        """
        # Calculate priority scores
        scored_memories = []
        for memory in memories:
            score = self._calculate_memory_priority(memory)
            scored_memories.append((score, memory))

        # Sort by priority (lower scores first for purging)
        scored_memories.sort(key=lambda x: x[0])

        return [memory for _, memory in scored_memories[:count]]

    def _context_aware_purge(self, memories: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Purge memories using context-aware strategy.
        """
        # Group memories by category
        category_groups = defaultdict(list)
        for memory in memories:
            category = memory.get("metadata", {}).get("category", "general")
            category_groups[category].append(memory)

        memories_to_purge = []
        remaining_count = count

        # Purge from each category based on retention policies
        for category, category_memories in category_groups.items():
            if remaining_count <= 0:
                break

            policy = self.retention_policies.get(category, self.retention_policies["general"])

            # Determine how many to purge from this category
            category_purge_count = min(
                remaining_count,
                max(0, len(category_memories) - policy["min_retention_count"]),
            )

            if category_purge_count > 0:
                # Apply category-specific purging
                category_purged = self._purge_category_memories(category_memories, category_purge_count, policy)
                memories_to_purge.extend(category_purged)
                remaining_count -= len(category_purged)

        # If we still need to purge more, use LRU on remaining
        if remaining_count > 0:
            remaining_memories = [m for m in memories if m not in memories_to_purge]
            additional_purged = self._lru_purge(remaining_memories, remaining_count)
            memories_to_purge.extend(additional_purged)

        return memories_to_purge

    def _hybrid_purge(self, memories: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        """
        Purge memories using hybrid strategy (combination of methods).
        """
        # First pass: context-aware purging (70% of target)
        context_count = int(count * 0.7)
        context_purged = self._context_aware_purge(memories, context_count)

        # Second pass: priority-based purging on remaining (30% of target)
        remaining_memories = [m for m in memories if m not in context_purged]
        remaining_count = count - len(context_purged)

        if remaining_count > 0:
            priority_purged = self._priority_based_purge(remaining_memories, remaining_count)
            context_purged.extend(priority_purged)

        return context_purged

    def _purge_category_memories(
        self,
        category_memories: List[Dict[str, Any]],
        purge_count: int,
        policy: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Purge memories from a specific category based on policy.
        """
        # Calculate scores for each memory
        scored_memories = []
        for memory in category_memories:
            score = self._calculate_category_specific_score(memory, policy)
            scored_memories.append((score, memory))

        # Sort by score (lower scores first for purging)
        scored_memories.sort(key=lambda x: x[0])

        # Check age restrictions
        max_age = timedelta(days=policy["max_age_days"])
        current_time = safe_datetime_now()

        purged = []
        for score, memory in scored_memories:
            if len(purged) >= purge_count:
                break

            # Check if memory is old enough to purge
            created_at = memory.get("metadata", {}).get("created_at")
            if created_at:
                try:
                    created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    if safe_datetime_diff(current_time, created_time) > max_age:
                        purged.append(memory)
                    elif score < 0.3:  # Very low score, purge regardless of age
                        purged.append(memory)
                except Exception:
                    # If we can't parse the date, include it for purging
                    purged.append(memory)
            else:
                # No creation date, include for purging
                purged.append(memory)

        return purged

    def _calculate_memory_priority(self, memory: Dict[str, Any]) -> float:
        """
        Calculate priority score for a memory (higher = more important).
        """
        metadata = memory.get("metadata", {})

        # Base priority from category
        category = metadata.get("category", "general")
        policy = self.retention_policies.get(category, self.retention_policies["general"])
        base_priority = policy["priority_weight"]

        # Access frequency factor
        access_count = metadata.get("access_count", 0)
        access_factor = min(math.log(access_count + 1) / 10, 1.0)

        # Recency factor
        recency_factor = self._calculate_recency_factor(metadata)

        # Success rate factor
        success_rate = metadata.get("success_rate", 0.5)

        # Content quality factor
        content_length = len(memory.get("memory", ""))
        quality_factor = min(content_length / 500, 1.0)  # Normalize to 500 chars

        # Combine factors
        priority = (
            base_priority * 0.3
            + access_factor * 0.25
            + recency_factor * 0.2
            + success_rate * 0.15
            + quality_factor * 0.1
        )

        return priority

    def _calculate_category_specific_score(self, memory: Dict[str, Any], policy: Dict[str, Any]) -> float:
        """
        Calculate category-specific score for purging decisions.
        """
        metadata = memory.get("metadata", {})

        # Base score from policy
        base_score = policy["priority_weight"]

        # Access weight
        access_count = metadata.get("access_count", 0)
        access_score = min(math.log(access_count + 1) / 10, 1.0) * policy["access_weight"]

        # Recency score
        recency_score = self._calculate_recency_factor(metadata) * 0.3

        # Error/solution importance
        importance_boost = 0.0
        if metadata.get("error_related", False):
            importance_boost += 0.1
        if metadata.get("solution_related", False):
            importance_boost += 0.15

        # Final score (lower = more likely to be purged)
        score = base_score + access_score + recency_score + importance_boost

        return score

    def _calculate_recency_factor(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate recency factor (newer = higher score).
        """
        last_accessed = metadata.get("last_accessed")
        if not last_accessed:
            created_at = metadata.get("created_at")
            if not created_at:
                return 0.0
            last_accessed = created_at

        try:
            last_time = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
            time_diff = safe_datetime_diff(safe_datetime_now(), last_time).total_seconds()

            # Exponential decay with half-life of 7 days
            decay_factor = math.exp(-time_diff / (7 * 24 * 3600))
            return decay_factor
        except Exception:
            return 0.0

    def _calculate_performance_impact(
        self, initial_stats: Dict[str, Any], purged_memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate performance impact of purging.
        """
        # Calculate category impact
        category_impact = defaultdict(int)
        for memory in purged_memories:
            category = memory.get("metadata", {}).get("category", "general")
            category_impact[category] += 1

        # Calculate access pattern impact
        high_access_purged = sum(
            1 for memory in purged_memories if memory.get("metadata", {}).get("access_count", 0) > 10
        )

        # Calculate recency impact
        recent_purged = sum(
            1 for memory in purged_memories if self._calculate_recency_factor(memory.get("metadata", {})) > 0.8
        )

        return {
            "category_impact": dict(category_impact),
            "high_access_memories_purged": high_access_purged,
            "recent_memories_purged": recent_purged,
            "estimated_retrieval_improvement": f"{len(purged_memories) * 0.1:.1f}%",
        }

    def get_storage_recommendations(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get storage optimization recommendations.
        """
        storage_check = self.check_storage_limits(memories)
        recommendations = storage_check["recommendations"]

        # Add proactive recommendations
        current_stats = storage_check["current_stats"]

        # Check for unbalanced categories
        total_memories = current_stats["total_memories"]
        for category, count in current_stats["category_counts"].items():
            if count > total_memories * 0.3:  # Category has >30% of memories
                recommendations.append(
                    {
                        "type": "balance_optimization",
                        "priority": "low",
                        "action": f"review_category_{category}",
                        "description": f'Category "{category}" has {count} memories ({count / total_memories * 100:.1f}% of total).',
                        "estimated_savings": f"{count * 0.1:.0f} memories",
                    }
                )

        # Check for old memories
        if current_stats["oldest_memory"]:
            recommendations.append(
                {
                    "type": "age_optimization",
                    "priority": "low",
                    "action": "review_old_memories",
                    "description": "Some memories are quite old and may be candidates for archival.",
                    "estimated_savings": "5-10%",
                }
            )

        return recommendations

    def update_storage_policy(self, category: str, policy_updates: Dict[str, Any]):
        """
        Update retention policy for a category.
        """
        if category not in self.retention_policies:
            self.retention_policies[category] = self.retention_policies["general"].copy()

        self.retention_policies[category].update(policy_updates)
        logger.info(f"Updated retention policy for category '{category}'")

    def get_storage_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive storage analytics.
        """
        return {
            "storage_limits": self.storage_limits,
            "retention_policies": self.retention_policies,
            "current_stats": self.storage_stats,
            "performance_metrics": self.performance_metrics,
            "purging_strategies": list(self.purging_strategies.keys()),
        }

    def reset_storage_stats(self):
        """
        Reset storage statistics.
        """
        self.storage_stats = {
            "total_memories": 0,
            "total_size_bytes": 0,
            "category_counts": defaultdict(int),
            "category_sizes": defaultdict(int),
            "last_purge_time": None,
            "purge_count": 0,
            "memories_purged": 0,
        }
        logger.info("Storage statistics reset")


class AutonomousStorageManager:
    """
    Autonomous storage management for AI agents.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage_manager = IntelligentStorageManager(config)

        # Autonomous settings
        self.autonomous_settings = {
            "auto_optimize_enabled": config.get("auto_optimize_enabled", True),
            "optimization_interval_hours": config.get("optimization_interval_hours", 24),
            "emergency_purge_threshold": config.get("emergency_purge_threshold", 0.95),
            "auto_purge_threshold": config.get("auto_purge_threshold", 0.85),
            "max_auto_purge_percent": config.get("max_auto_purge_percent", 0.15),
        }

        # Learning parameters
        self.learning_enabled = config.get("enable_learning", True)
        self.optimization_history = []
        self.performance_tracking = {
            "optimizations_performed": 0,
            "total_memories_purged": 0,
            "average_performance_gain": 0.0,
            "user_satisfaction_score": 0.0,
        }

        self.last_optimization = None

    def monitor_and_optimize(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Monitor storage and perform autonomous optimization if needed.
        """
        # Check storage status
        storage_check = self.storage_manager.check_storage_limits(memories)
        overall_status = storage_check["overall_status"]

        # Determine if optimization is needed
        optimization_needed = False
        optimization_urgency = "normal"

        if overall_status == "critical":
            optimization_needed = True
            optimization_urgency = "emergency"
        elif overall_status == "warning" and self.autonomous_settings["auto_optimize_enabled"]:
            optimization_needed = True
            optimization_urgency = "scheduled"
        elif self._is_scheduled_optimization_due():
            optimization_needed = True
            optimization_urgency = "maintenance"

        result = {
            "optimization_performed": False,
            "storage_status": overall_status,
            "optimization_urgency": optimization_urgency,
            "recommendations": storage_check["recommendations"],
        }

        # Perform optimization if needed
        if optimization_needed:
            optimization_result = self._perform_autonomous_optimization(memories, optimization_urgency)
            result.update(optimization_result)
            result["optimization_performed"] = True

        return result

    def _is_scheduled_optimization_due(self) -> bool:
        """
        Check if scheduled optimization is due.
        """
        if not self.last_optimization:
            return True

        try:
            last_opt_time = datetime.fromisoformat(self.last_optimization)
            interval = timedelta(hours=self.autonomous_settings["optimization_interval_hours"])
            return safe_datetime_now() - last_opt_time >= interval
        except Exception:
            return True

    def _perform_autonomous_optimization(self, memories: List[Dict[str, Any]], urgency: str) -> Dict[str, Any]:
        """
        Perform autonomous optimization based on urgency.
        """
        # Determine optimization parameters
        if urgency == "emergency":
            strategy = "hybrid"
            target_reduction = min(self.autonomous_settings["max_auto_purge_percent"], 0.2)
        elif urgency == "scheduled":
            strategy = "context_aware"
            target_reduction = min(self.autonomous_settings["max_auto_purge_percent"], 0.1)
        else:  # maintenance
            strategy = "priority_based"
            target_reduction = 0.05

        # Perform optimization
        optimization_result = self.storage_manager.optimize_storage(memories, strategy, target_reduction)

        # Record optimization
        self._record_optimization(optimization_result, urgency)

        # Update learning data
        if self.learning_enabled:
            self._update_learning_data(optimization_result)

        self.last_optimization = create_memory_timestamp()

        return optimization_result

    def _record_optimization(self, result: Dict[str, Any], urgency: str):
        """
        Record optimization for analytics.
        """
        record = {
            "timestamp": create_memory_timestamp(),
            "urgency": urgency,
            "strategy": result["strategy_used"],
            "memories_removed": result["memories_removed"],
            "size_saved_mb": result["size_saved_mb"],
            "performance_impact": result["performance_impact"],
        }

        self.optimization_history.append(record)

        # Keep only recent history
        if len(self.optimization_history) > 100:
            self.optimization_history = self.optimization_history[-100:]

    def _update_learning_data(self, result: Dict[str, Any]):
        """
        Update learning data based on optimization results.
        """
        self.performance_tracking["optimizations_performed"] += 1
        self.performance_tracking["total_memories_purged"] += result["memories_removed"]

        # Calculate performance gain estimate
        size_saved = result["size_saved_mb"]
        if size_saved > 0:
            performance_gain = min(size_saved / 10, 1.0)  # Normalize to 10MB
            current_avg = self.performance_tracking["average_performance_gain"]
            total_opts = self.performance_tracking["optimizations_performed"]

            # Update running average
            self.performance_tracking["average_performance_gain"] = (
                current_avg * (total_opts - 1) + performance_gain
            ) / total_opts

    def provide_feedback(self, optimization_id: str, satisfaction_score: float):
        """
        Provide feedback on optimization effectiveness.
        """
        if not 0.0 <= satisfaction_score <= 1.0:
            raise ValueError("Satisfaction score must be between 0.0 and 1.0")

        # Update satisfaction tracking
        current_score = self.performance_tracking["user_satisfaction_score"]
        total_opts = self.performance_tracking["optimizations_performed"]

        if total_opts > 0:
            self.performance_tracking["user_satisfaction_score"] = (
                current_score * (total_opts - 1) + satisfaction_score
            ) / total_opts
        else:
            self.performance_tracking["user_satisfaction_score"] = satisfaction_score

        # Adapt parameters based on feedback
        if self.learning_enabled:
            self._adapt_based_on_feedback(satisfaction_score)

        logger.info(f"Feedback received for optimization {optimization_id}: {satisfaction_score}")

    def _adapt_based_on_feedback(self, satisfaction_score: float):
        """
        Adapt optimization parameters based on feedback.
        """
        if satisfaction_score < 0.3:
            # Very poor feedback, be more conservative
            self.autonomous_settings["max_auto_purge_percent"] = max(
                self.autonomous_settings["max_auto_purge_percent"] * 0.8, 0.05
            )
        elif satisfaction_score > 0.8:
            # Good feedback, can be more aggressive
            self.autonomous_settings["max_auto_purge_percent"] = min(
                self.autonomous_settings["max_auto_purge_percent"] * 1.1, 0.3
            )

        logger.info(f"Adapted purge parameters based on feedback: {satisfaction_score:.2f}")

    def get_optimization_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive optimization analytics.
        """
        return {
            "autonomous_settings": self.autonomous_settings,
            "performance_tracking": self.performance_tracking,
            "optimization_history": self.optimization_history[-10:],  # Last 10 optimizations
            "learning_enabled": self.learning_enabled,
            "last_optimization": self.last_optimization,
        }

    def enable_autonomous_mode(self, enabled: bool):
        """
        Enable or disable autonomous optimization mode.
        """
        self.autonomous_settings["auto_optimize_enabled"] = enabled
        logger.info(f"Autonomous optimization {'enabled' if enabled else 'disabled'}")

    def reset_learning_data(self):
        """
        Reset learning and performance data.
        """
        self.optimization_history.clear()
        self.performance_tracking = {
            "optimizations_performed": 0,
            "total_memories_purged": 0,
            "average_performance_gain": 0.0,
            "user_satisfaction_score": 0.0,
        }
        logger.info("Autonomous storage manager learning data reset")
