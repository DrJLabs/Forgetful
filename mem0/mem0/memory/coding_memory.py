"""
Enhanced Memory class optimized for coding contexts and autonomous AI agents.
This module extends the base Memory class with coding-specific optimizations.
"""

import asyncio
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pytz

from mem0.memory.main import Memory, AsyncMemory
from mem0.configs.coding_config import CodingMemoryConfig, CodingFactExtractor
from mem0.memory.utils import parse_messages, remove_code_blocks
from mem0.memory.enhanced_deduplication import (
    EnhancedDeduplicator,
    AutonomousDeduplicationManager,
)
from mem0.utils.factory import EmbedderFactory, LlmFactory, VectorStoreFactory

logger = logging.getLogger(__name__)


class CodingMemory(Memory):
    """
    Enhanced Memory class optimized for coding contexts and autonomous AI agents.
    """

    def __init__(self, config: CodingMemoryConfig):
        super().__init__(config)
        self.coding_config = config
        self.fact_extractor = CodingFactExtractor()

        # Enhanced caching for coding contexts
        self.coding_cache = {}
        self.context_patterns = {}

        # Initialize enhanced deduplication
        self.deduplication_manager = AutonomousDeduplicationManager(config.__dict__)

        # Initialize coding-specific components
        self._initialize_coding_optimizations()

    def _initialize_coding_optimizations(self):
        """Initialize coding-specific optimizations."""
        # Set up enhanced similarity thresholds
        self.coding_similarity_threshold = (
            self.coding_config.coding_similarity_threshold
        )

        # Initialize context-aware categorization
        self.coding_categories = self.coding_config.coding_categories

        # Set up autonomous storage parameters
        self.autonomous_config = self.coding_config.autonomous_storage_config

        logger.info("Coding memory optimizations initialized")

    def add_coding_context(
        self,
        messages,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        coding_context: Optional[str] = None,
        priority: float = 0.5,
        **kwargs,
    ):
        """
        Add memory with coding-specific context awareness.

        Args:
            messages: Input messages to process
            user_id: User identifier
            agent_id: Agent identifier
            run_id: Run identifier
            metadata: Additional metadata
            coding_context: Type of coding context (bug_fixing, architecture, etc.)
            priority: Priority for this memory (0.0 to 1.0)
            **kwargs: Additional arguments
        """
        # Enhance metadata with coding context
        enhanced_metadata = metadata or {}

        if coding_context:
            # Apply context-specific parameters
            context_config = self.coding_config.autonomous_storage_config.get(
                coding_context, {}
            )
            enhanced_metadata.update(
                {
                    "coding_context": coding_context,
                    "priority": priority,
                    "context_config": context_config,
                }
            )

        # Use enhanced fact extraction
        return self.add(
            messages,
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
            metadata=enhanced_metadata,
            prompt=self.coding_config.coding_fact_extraction_prompt,
            **kwargs,
        )

    def _add_to_vector_store(self, messages, metadata, filters, infer):
        """
        Enhanced vector store addition with coding-specific optimizations.
        """
        if not infer:
            return super()._add_to_vector_store(messages, metadata, filters, infer)

        # Use coding-specific fact extraction
        parsed_messages = parse_messages(messages)

        # Apply coding-optimized fact extraction
        system_prompt = (
            self.coding_config.coding_fact_extraction_prompt
            or self.fact_extractor.get_coding_fact_extraction_prompt()
        )
        user_prompt = f"Input:\n{parsed_messages}"

        response = self.llm.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        try:
            response = remove_code_blocks(response)
            new_retrieved_facts = json.loads(response)["facts"]
        except Exception as e:
            logger.error(f"Error in coding fact extraction: {e}")
            new_retrieved_facts = []

        if not new_retrieved_facts:
            logger.debug("No coding facts retrieved from input.")
            return []

        # Enhanced processing with coding context
        return self._process_coding_facts(new_retrieved_facts, metadata, filters)

    def _process_coding_facts(
        self, facts: List[str], metadata: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process coding facts with enhanced categorization and metadata.
        """
        processed_memories = []

        for fact in facts:
            # Auto-categorize the fact
            category = self.fact_extractor.categorize_coding_fact(fact)

            # Extract coding-specific metadata
            coding_metadata = self.fact_extractor.extract_coding_metadata(fact)

            # Apply context-aware scoring
            context_weight = self.coding_config.coding_context_weights.get(
                category, 0.5
            )

            # Enhanced metadata with coding context
            enhanced_metadata = {
                **metadata,
                "category": category,
                "context_weight": context_weight,
                **coding_metadata,
            }

            # Apply enhanced similarity checking
            if self._should_store_coding_fact(fact, enhanced_metadata, filters):
                # Create memory with enhanced metadata
                embeddings = self.embedding_model.embed(fact, "add")
                memory_id = self._create_coding_memory(
                    fact, embeddings, enhanced_metadata
                )

                processed_memories.append(
                    {
                        "id": memory_id,
                        "memory": fact,
                        "category": category,
                        "context_weight": context_weight,
                        "event": "ADD",
                    }
                )

        return processed_memories

    def _should_store_coding_fact(
        self, fact: str, metadata: Dict[str, Any], filters: Dict[str, Any]
    ) -> bool:
        """
        Determine if a coding fact should be stored based on enhanced deduplication.
        """
        # Get existing memories for comparison
        embeddings = self.embedding_model.embed(fact, "add")
        existing_memories = self.vector_store.search(
            query=fact,
            vectors=embeddings,
            limit=5,
            filters=filters,
        )

        # Convert to format expected by deduplication manager
        existing_memories_formatted = []
        for mem in existing_memories:
            existing_memories_formatted.append(
                {
                    "id": mem.id,
                    "memory": mem.payload.get("data", ""),
                    "metadata": mem.payload,
                }
            )

        # Use enhanced deduplication logic
        dedup_result = self.deduplication_manager.process_memory(
            fact, existing_memories_formatted, metadata
        )

        # Log deduplication decision
        if dedup_result["should_deduplicate"]:
            logger.debug(
                f"Fact rejected by enhanced deduplication: {dedup_result['reasoning']}"
            )
            return False

        return True

    def _create_coding_memory(
        self, data: str, embeddings: List[float], metadata: Dict[str, Any]
    ) -> str:
        """
        Create memory with enhanced coding-specific metadata.

        CRITICAL: Directly implements memory creation to avoid problematic
        dictionary key anti-pattern with potentially long data strings.
        """
        import uuid
        from datetime import datetime
        import pytz

        # Generate memory ID and prepare enhanced metadata
        memory_id = str(uuid.uuid4())
        enhanced_metadata = metadata or {}
        enhanced_metadata["data"] = data
        enhanced_metadata["hash"] = hashlib.md5(data.encode()).hexdigest()
        from mem0.memory.timezone_utils import create_memory_timestamp

        enhanced_metadata["created_at"] = create_memory_timestamp()

        # Use pre-computed embeddings directly - SAFE APPROACH
        self.vector_store.insert(
            vectors=[embeddings],
            ids=[memory_id],
            payloads=[enhanced_metadata],
        )

        # Add to history with proper error handling
        try:
            self.db.add_history(
                memory_id,
                None,
                data,
                "ADD",
                created_at=enhanced_metadata.get("created_at"),
                actor_id=enhanced_metadata.get("actor_id"),
                role=enhanced_metadata.get("role"),
            )
        except Exception as e:
            logger.error(f"Failed to add history for coding memory {memory_id}: {e}")

        # Add telemetry capture for consistency
        try:
            from mem0.memory.telemetry import capture_event

            capture_event(
                "mem0._create_memory",
                self,
                {"memory_id": memory_id, "sync_type": "sync"},
            )
        except ImportError:
            logger.debug("Telemetry capture not available")

        # Store coding-specific patterns for optimization
        category = metadata.get("category", "general")
        if category not in self.context_patterns:
            self.context_patterns[category] = []

        self.context_patterns[category].append(
            {
                "memory_id": memory_id,
                "data": data[:100],  # Store first 100 chars for pattern matching
                "metadata": metadata,
            }
        )

        return memory_id

    def search_coding_context(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        coding_context: Optional[str] = None,
        limit: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search with coding-specific context awareness.
        """
        # Build enhanced filters for coding context
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if agent_id:
            filters["agent_id"] = agent_id
        if run_id:
            filters["run_id"] = run_id

        # Apply coding context filtering
        if coding_context:
            filters["coding_context"] = coding_context

        # Perform enhanced search
        results = self.search(query, filters=filters, limit=limit, **kwargs)

        # Apply coding-specific result ranking
        if isinstance(results, dict) and "results" in results:
            results["results"] = self._rank_coding_results(
                results["results"], query, coding_context
            )

        return results

    def _rank_coding_results(
        self, results: List[Dict[str, Any]], query: str, coding_context: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Apply coding-specific ranking to search results.
        """
        for result in results:
            # Apply context-aware scoring
            base_score = result.get("score", 0.0)

            # Get category from metadata
            category = result.get("metadata", {}).get("category", "general")
            context_weight = self.coding_config.coding_context_weights.get(
                category, 0.5
            )

            # Apply priority boost for error-related content
            priority_boost = result.get("metadata", {}).get("priority_boost", 0.0)

            # Calculate enhanced score
            enhanced_score = base_score * context_weight + priority_boost

            # Boost score if it matches the requested coding context
            if (
                coding_context
                and result.get("metadata", {}).get("coding_context") == coding_context
            ):
                enhanced_score *= 1.2

            result["enhanced_score"] = enhanced_score

        # Sort by enhanced score
        results.sort(key=lambda x: x.get("enhanced_score", 0), reverse=True)

        return results

    def get_coding_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get analytics about coding memory usage.
        """
        # Get all memories for the user
        all_memories = self.get_all(user_id=user_id)

        if not all_memories:
            return {"total_memories": 0, "categories": {}, "patterns": {}}

        # Analyze categories
        categories = {}
        total_memories = len(all_memories)

        for memory in all_memories:
            category = memory.get("metadata", {}).get("category", "uncategorized")
            categories[category] = categories.get(category, 0) + 1

        # Calculate category percentages
        for category in categories:
            categories[category] = {
                "count": categories[category],
                "percentage": (categories[category] / total_memories) * 100,
            }

        return {
            "total_memories": total_memories,
            "categories": categories,
            "patterns": self.context_patterns,
            "optimization_suggestions": self._get_optimization_suggestions(categories),
        }

    def _get_optimization_suggestions(
        self, categories: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """
        Generate optimization suggestions based on usage patterns.
        """
        suggestions = []

        # Analyze category distribution
        total_memories = sum(cat["count"] for cat in categories.values())

        if total_memories > 0:
            # Check for imbalanced categories
            bug_fix_ratio = categories.get("bug_fix", {}).get("percentage", 0)
            if bug_fix_ratio > 50:
                suggestions.append(
                    "High bug fix ratio detected. Consider focusing on code quality and testing."
                )

            architecture_ratio = categories.get("architecture", {}).get("percentage", 0)
            if architecture_ratio < 10:
                suggestions.append(
                    "Low architecture memory ratio. Consider documenting design decisions."
                )

            performance_ratio = categories.get("performance", {}).get("percentage", 0)
            if performance_ratio > 30:
                suggestions.append(
                    "High performance issue ratio. Consider systematic performance optimization."
                )

        return suggestions

    def get_deduplication_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about deduplication performance.
        """
        return self.deduplication_manager.get_performance_report()

    def test_deduplication_performance(
        self, test_facts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Test deduplication performance with a set of test facts.
        """
        results = {
            "total_tested": len(test_facts),
            "duplicates_detected": 0,
            "unique_stored": 0,
            "performance_metrics": [],
            "false_positive_samples": [],
            "false_negative_samples": [],
        }

        stored_facts = []

        for i, test_fact in enumerate(test_facts):
            fact_text = test_fact.get("fact", "")
            metadata = test_fact.get("metadata", {})
            expected_duplicate = test_fact.get("is_duplicate", False)

            # Test deduplication
            dedup_result = self.deduplication_manager.process_memory(
                fact_text, stored_facts, metadata
            )

            detected_duplicate = dedup_result["should_deduplicate"]

            # Record performance
            results["performance_metrics"].append(
                {
                    "test_index": i,
                    "similarity_score": dedup_result["similarity_score"],
                    "confidence": dedup_result["confidence"],
                    "reasoning": dedup_result["reasoning"],
                    "expected_duplicate": expected_duplicate,
                    "detected_duplicate": detected_duplicate,
                }
            )

            # Check for false positives/negatives
            if expected_duplicate and not detected_duplicate:
                results["false_negative_samples"].append(
                    {
                        "index": i,
                        "fact": fact_text,
                        "metadata": metadata,
                        "similarity_score": dedup_result["similarity_score"],
                    }
                )
            elif not expected_duplicate and detected_duplicate:
                results["false_positive_samples"].append(
                    {
                        "index": i,
                        "fact": fact_text,
                        "metadata": metadata,
                        "similarity_score": dedup_result["similarity_score"],
                    }
                )

            # Update results
            if detected_duplicate:
                results["duplicates_detected"] += 1
            else:
                results["unique_stored"] += 1
                stored_facts.append(
                    {"id": f"test_{i}", "memory": fact_text, "metadata": metadata}
                )

        # Calculate accuracy metrics
        if results["total_tested"] > 0:
            results["accuracy"] = (
                results["total_tested"]
                - len(results["false_positive_samples"])
                - len(results["false_negative_samples"])
            ) / results["total_tested"]
            results["false_positive_rate"] = (
                len(results["false_positive_samples"]) / results["total_tested"]
            )
            results["false_negative_rate"] = (
                len(results["false_negative_samples"]) / results["total_tested"]
            )

        return results


class AsyncCodingMemory(AsyncMemory):
    """
    Async version of CodingMemory for high-performance scenarios.
    """

    def __init__(self, config: CodingMemoryConfig):
        super().__init__(config)
        self.coding_config = config
        self.fact_extractor = CodingFactExtractor()

    async def add_coding_context(
        self,
        messages,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        coding_context: Optional[str] = None,
        priority: float = 0.5,
        **kwargs,
    ):
        """
        Async version of add_coding_context.
        """
        # Enhance metadata with coding context
        enhanced_metadata = metadata or {}

        if coding_context:
            enhanced_metadata.update(
                {
                    "coding_context": coding_context,
                    "priority": priority,
                }
            )

        # Use enhanced fact extraction
        return await self.add(
            messages,
            user_id=user_id,
            agent_id=agent_id,
            run_id=run_id,
            metadata=enhanced_metadata,
            prompt=self.coding_config.coding_fact_extraction_prompt,
            **kwargs,
        )

    async def search_coding_context(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        coding_context: Optional[str] = None,
        limit: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Async version of search_coding_context.
        """
        # Build enhanced filters for coding context
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if agent_id:
            filters["agent_id"] = agent_id
        if run_id:
            filters["run_id"] = run_id

        # Apply coding context filtering
        if coding_context:
            filters["coding_context"] = coding_context

        # Perform enhanced search
        results = await self.search(query, filters=filters, limit=limit, **kwargs)

        return results
