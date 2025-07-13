"""
Comprehensive tests for coding-specific memory optimizations.
"""

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from mem0.configs.coding_config import (
    CodingFactExtractor,
    CodingMemoryConfig,
    create_coding_optimized_config,
)
from mem0.memory.coding_memory import AsyncCodingMemory, CodingMemory
from mem0.memory.enhanced_deduplication import (
    AutonomousDeduplicationManager,
    EnhancedDeduplicator,
)


class TestCodingMemoryConfig:
    """Test suite for CodingMemoryConfig."""

    def test_default_config_creation(self):
        """Test creating default coding memory config."""
        config = CodingMemoryConfig()

        assert config.coding_similarity_threshold == 0.85
        assert len(config.coding_categories) == 10
        assert "bug_fix" in config.coding_categories
        assert "architecture" in config.coding_categories
        assert config.coding_context_weights["code_snippet"] == 1.0
        assert config.coding_context_weights["error_solution"] == 0.9

    def test_custom_config_creation(self):
        """Test creating custom coding memory config."""
        custom_config = {
            "coding_similarity_threshold": 0.9,
            "coding_categories": ["custom_category"],
            "coding_context_weights": {"custom_context": 0.8},
        }

        config = CodingMemoryConfig(**custom_config)

        assert config.coding_similarity_threshold == 0.9
        assert "custom_category" in config.coding_categories
        assert config.coding_context_weights["custom_context"] == 0.8

    def test_autonomous_storage_config(self):
        """Test autonomous storage configuration."""
        config = CodingMemoryConfig()

        autonomous_config = config.autonomous_storage_config
        assert autonomous_config["max_memories_per_session"] == 50
        assert autonomous_config["context_window_size"] == 20
        assert autonomous_config["relevance_decay_factor"] == 0.1

    def test_coding_metadata_config(self):
        """Test coding metadata configuration."""
        config = CodingMemoryConfig()

        metadata_config = config.coding_metadata_config
        assert metadata_config["auto_tag_code_blocks"] is True
        assert metadata_config["extract_file_references"] is True
        assert metadata_config["track_solution_effectiveness"] is True

    def test_performance_config(self):
        """Test performance configuration."""
        config = CodingMemoryConfig()

        performance_config = config.coding_performance_config
        assert performance_config["batch_size"] == 10
        assert performance_config["parallel_processing"] is True
        assert performance_config["cache_frequent_patterns"] is True


class TestCodingFactExtractor:
    """Test suite for CodingFactExtractor."""

    def test_get_coding_fact_extraction_prompt(self):
        """Test getting coding fact extraction prompt."""
        prompt = CodingFactExtractor.get_coding_fact_extraction_prompt()

        assert "code analyst" in prompt.lower()
        assert "autonomous ai coding agents" in prompt.lower()
        assert "code solutions" in prompt.lower()
        assert "bug fixes" in prompt.lower()
        assert "architecture" in prompt.lower()

    def test_categorize_coding_fact_bug_fix(self):
        """Test categorizing bug fix facts."""
        facts = [
            "Fixed memory leak error in React component",
            "Resolved crash when parsing JSON data",
            "Bug in authentication causing 401 errors",
            "Exception handling for database connections",
        ]

        for fact in facts:
            category = CodingFactExtractor.categorize_coding_fact(fact)
            assert category == "bug_fix"

    def test_categorize_coding_fact_architecture(self):
        """Test categorizing architecture facts."""
        facts = [
            "Implemented microservices architecture pattern",
            "Design decision to use REST API over GraphQL",
            "Structural refactoring of database layer",
            "Architecture pattern for event-driven system",
        ]

        for fact in facts:
            category = CodingFactExtractor.categorize_coding_fact(fact)
            assert category == "architecture"

    def test_categorize_coding_fact_performance(self):
        """Test categorizing performance facts."""
        facts = [
            "Optimized database query performance by 50%",
            "Memory usage reduced through caching",
            "Speed improvement using async processing",
            "Performance bottleneck in image processing",
        ]

        for fact in facts:
            category = CodingFactExtractor.categorize_coding_fact(fact)
            assert category == "performance"

    def test_categorize_coding_fact_configuration(self):
        """Test categorizing configuration facts."""
        facts = [
            "Environment setup for development",
            "Configuration file for production deployment",
            "Setup instructions for CI/CD pipeline",
            "Deploy script for cloud infrastructure",
        ]

        for fact in facts:
            category = CodingFactExtractor.categorize_coding_fact(fact)
            assert category == "configuration"

    def test_categorize_coding_fact_testing(self):
        """Test categorizing testing facts."""
        facts = [
            "Unit tests for user authentication",
            "Integration testing strategy",
            "Validation of API endpoints",
            "Test coverage for edge cases",
        ]

        for fact in facts:
            category = CodingFactExtractor.categorize_coding_fact(fact)
            assert category == "testing"

    def test_categorize_coding_fact_debugging(self):
        """Test categorizing debugging facts."""
        facts = [
            "Debug logging for transaction processing",
            "Trace analysis of performance issues",
            "Log investigation for error tracking",
            "Debugging steps for memory leaks",
        ]

        for fact in facts:
            category = CodingFactExtractor.categorize_coding_fact(fact)
            assert category == "debugging"

    def test_categorize_coding_fact_refactoring(self):
        """Test categorizing refactoring facts."""
        facts = [
            "Refactored legacy code structure",
            "Cleanup of unused dependencies",
            "Improved code organization",
            "Restructured component hierarchy",
        ]

        for fact in facts:
            category = CodingFactExtractor.categorize_coding_fact(fact)
            assert category == "refactoring"

    def test_categorize_coding_fact_default(self):
        """Test categorizing default facts."""
        facts = [
            "Implemented new feature for user management",
            "Created API endpoint for data retrieval",
            "Added validation logic for form inputs",
            "Developed algorithm for data processing",
        ]

        for fact in facts:
            category = CodingFactExtractor.categorize_coding_fact(fact)
            assert category == "code_implementation"

    def test_extract_coding_metadata_file_references(self):
        """Test extracting file references from facts."""
        facts = [
            "Updated config.json with new settings",
            "Modified /src/components/Button.tsx for styling",
            "Created utils/helper.py for data processing",
            "Fixed bug in main.js file",
        ]

        for fact in facts:
            metadata = CodingFactExtractor.extract_coding_metadata(fact)
            assert "file_references" in metadata
            assert len(metadata["file_references"]) > 0

    def test_extract_coding_metadata_code_indicators(self):
        """Test extracting code indicators from facts."""
        facts = [
            "Added function calculateTotal() to process data",
            "Created class UserManager for authentication",
            "```python\ndef process_data():\n    return result```",
            "The method getUserInfo() returns user data",
        ]

        for fact in facts:
            metadata = CodingFactExtractor.extract_coding_metadata(fact)
            assert metadata.get("contains_code") is True

    def test_extract_coding_metadata_error_indicators(self):
        """Test extracting error indicators from facts."""
        facts = [
            "Fixed critical error in payment processing",
            "Resolved exception in user authentication",
            "Database connection failed during startup",
            "Application crashed due to memory overflow",
        ]

        for fact in facts:
            metadata = CodingFactExtractor.extract_coding_metadata(fact)
            assert metadata.get("error_related") is True
            assert metadata.get("priority_boost") == 0.2

    def test_extract_coding_metadata_solution_indicators(self):
        """Test extracting solution indicators from facts."""
        facts = [
            "Found solution for memory optimization",
            "Fixed authentication issue successfully",
            "Resolved performance bottleneck",
            "Implementation works correctly now",
        ]

        for fact in facts:
            metadata = CodingFactExtractor.extract_coding_metadata(fact)
            assert metadata.get("solution_related") is True
            assert metadata.get("priority_boost") == 0.1


class TestCodingMemory:
    """Test suite for CodingMemory class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = CodingMemoryConfig()

        # Mock dependencies
        self.mock_embedding_model = Mock()
        self.mock_vector_store = Mock()
        self.mock_llm = Mock()
        self.mock_db = Mock()

        # Create patches
        self.embedding_patch = patch(
            "mem0.utils.factory.EmbedderFactory.create",
            return_value=self.mock_embedding_model,
        )
        self.vector_patch = patch(
            "mem0.utils.factory.VectorStoreFactory.create",
            return_value=self.mock_vector_store,
        )
        self.llm_patch = patch(
            "mem0.utils.factory.LlmFactory.create", return_value=self.mock_llm
        )
        self.db_patch = patch(
            "mem0.memory.storage.SQLiteManager", return_value=self.mock_db
        )

        # Start patches
        self.embedding_patch.start()
        self.vector_patch.start()
        self.llm_patch.start()
        self.db_patch.start()

    def teardown_method(self):
        """Clean up patches."""
        self.embedding_patch.stop()
        self.vector_patch.stop()
        self.llm_patch.stop()
        self.db_patch.stop()

    def test_coding_memory_initialization(self):
        """Test CodingMemory initialization."""
        memory = CodingMemory(self.config)

        assert memory.coding_config == self.config
        assert memory.fact_extractor is not None
        assert memory.coding_similarity_threshold == 0.85
        assert len(memory.coding_categories) == 10

    def test_add_coding_context_with_context(self):
        """Test adding memory with coding context."""
        memory = CodingMemory(self.config)

        # Mock LLM response
        self.mock_llm.generate_response.return_value = json.dumps(
            {"facts": ["Fixed memory leak in React component"]}
        )

        # Mock vector store search (no existing memories)
        self.mock_vector_store.search.return_value = []

        # Mock embedding
        self.mock_embedding_model.embed.return_value = [0.1, 0.2, 0.3]

        messages = [
            {"role": "user", "content": "I fixed a memory leak in the React component"},
            {"role": "assistant", "content": "Great! That should improve performance."},
        ]

        result = memory.add_coding_context(
            messages, user_id="test_user", coding_context="bug_fixing", priority=0.8
        )

        # Verify the result
        assert result is not None
        # The actual implementation details depend on the memory system

    def test_search_coding_context(self):
        """Test searching with coding context."""
        memory = CodingMemory(self.config)

        # Mock search results
        mock_results = {
            "results": [
                {
                    "id": "1",
                    "memory": "Fixed memory leak in React component",
                    "score": 0.9,
                    "metadata": {"category": "bug_fix"},
                }
            ]
        }

        with patch.object(memory, "search", return_value=mock_results):
            results = memory.search_coding_context(
                "memory leak fix", user_id="test_user", coding_context="bug_fixing"
            )

            assert "results" in results
            assert len(results["results"]) == 1
            assert "enhanced_score" in results["results"][0]

    def test_should_store_coding_fact_with_high_similarity(self):
        """Test deduplication with high similarity."""
        memory = CodingMemory(self.config)

        # Mock high similarity existing memory
        mock_memory = Mock()
        mock_memory.score = 0.95
        self.mock_vector_store.search.return_value = [mock_memory]

        # Mock embedding
        self.mock_embedding_model.embed.return_value = [0.1, 0.2, 0.3]

        should_store = memory._should_store_coding_fact(
            "This is a duplicate fact",
            {"category": "bug_fix"},
            {"user_id": "test_user"},
        )

        assert should_store is False

    def test_should_store_coding_fact_with_low_similarity(self):
        """Test storing fact with low similarity."""
        memory = CodingMemory(self.config)

        # Mock low similarity existing memory
        mock_memory = Mock()
        mock_memory.score = 0.5
        self.mock_vector_store.search.return_value = [mock_memory]

        # Mock embedding
        self.mock_embedding_model.embed.return_value = [0.1, 0.2, 0.3]

        should_store = memory._should_store_coding_fact(
            "This is a new fact", {"category": "bug_fix"}, {"user_id": "test_user"}
        )

        assert should_store is True

    def test_rank_coding_results(self):
        """Test ranking coding results."""
        memory = CodingMemory(self.config)

        results = [
            {
                "id": "1",
                "memory": "Fixed memory leak",
                "score": 0.8,
                "metadata": {"category": "bug_fix"},
            },
            {
                "id": "2",
                "memory": "General comment",
                "score": 0.9,
                "metadata": {"category": "general_comment"},
            },
        ]

        ranked_results = memory._rank_coding_results(
            results, "memory fix", "bug_fixing"
        )

        # Bug fix should be ranked higher despite lower base score
        assert ranked_results[0]["id"] == "1"
        assert "enhanced_score" in ranked_results[0]
        assert "enhanced_score" in ranked_results[1]

    def test_get_coding_analytics(self):
        """Test getting coding analytics."""
        memory = CodingMemory(self.config)

        # Mock get_all response
        mock_memories = [
            {"metadata": {"category": "bug_fix"}},
            {"metadata": {"category": "bug_fix"}},
            {"metadata": {"category": "architecture"}},
            {"metadata": {"category": "performance"}},
        ]

        with patch.object(memory, "get_all", return_value=mock_memories):
            analytics = memory.get_coding_analytics("test_user")

            assert analytics["total_memories"] == 4
            assert analytics["categories"]["bug_fix"]["count"] == 2
            assert analytics["categories"]["bug_fix"]["percentage"] == 50.0
            assert analytics["categories"]["architecture"]["count"] == 1
            assert analytics["categories"]["performance"]["count"] == 1
            assert len(analytics["optimization_suggestions"]) >= 0


class TestCreateCodingOptimizedConfig:
    """Test suite for create_coding_optimized_config function."""

    def test_create_default_config(self):
        """Test creating default optimized config."""
        config = create_coding_optimized_config()

        assert isinstance(config, CodingMemoryConfig)
        assert config.api_version == "v1.1"
        assert config.coding_similarity_threshold == 0.85
        assert config.custom_fact_extraction_prompt is not None

    def test_create_config_with_base(self):
        """Test creating optimized config with base configuration."""
        base_config = {
            "coding_similarity_threshold": 0.9,
            "custom_setting": "test_value",
        }

        config = create_coding_optimized_config(base_config)

        assert isinstance(config, CodingMemoryConfig)
        assert config.coding_similarity_threshold == 0.9
        assert config.api_version == "v1.1"


class TestIntegrationScenarios:
    """Integration tests for real-world coding scenarios."""

    def test_bug_fix_scenario(self):
        """Test complete bug fix scenario."""
        # This would be an integration test with actual components
        # For now, we'll test the configuration and flow
        config = create_coding_optimized_config()

        # Verify bug fix context is properly configured
        assert "bug_fix" in config.coding_categories
        assert config.coding_context_weights["error_solution"] == 0.9

        # Test fact extraction for bug fix
        fact = "Fixed memory leak in React useEffect by adding cleanup function"
        category = CodingFactExtractor.categorize_coding_fact(fact)
        metadata = CodingFactExtractor.extract_coding_metadata(fact)

        assert category == "bug_fix"
        assert metadata.get("solution_related") is True
        assert metadata.get("priority_boost") == 0.1

    def test_architecture_scenario(self):
        """Test complete architecture scenario."""
        config = create_coding_optimized_config()

        # Verify architecture context is properly configured
        assert "architecture" in config.coding_categories
        assert config.coding_context_weights["architectural_decision"] == 0.8

        # Test fact extraction for architecture
        fact = "Implemented microservices architecture pattern using Docker containers"
        category = CodingFactExtractor.categorize_coding_fact(fact)
        metadata = CodingFactExtractor.extract_coding_metadata(fact)

        assert category == "architecture"
        assert metadata.get("contains_code") is False  # No code blocks in this fact

    def test_performance_scenario(self):
        """Test complete performance scenario."""
        config = create_coding_optimized_config()

        # Test fact extraction for performance
        fact = "Optimized database query performance by 70% using proper indexing"
        category = CodingFactExtractor.categorize_coding_fact(fact)
        metadata = CodingFactExtractor.extract_coding_metadata(fact)

        assert category == "performance"
        assert metadata.get("solution_related") is True


class TestEnhancedDeduplication:
    """Test suite for enhanced deduplication algorithms."""

    def test_enhanced_deduplicator_initialization(self):
        """Test enhanced deduplicator initialization."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        assert deduplicator.similarity_thresholds["bug_fix"] == 0.9
        assert deduplicator.similarity_thresholds["error_solution"] == 0.92
        assert deduplicator.similarity_thresholds["architecture"] == 0.8
        assert len(deduplicator.semantic_patterns) == 4

    def test_should_deduplicate_exact_match(self):
        """Test deduplication with exact match."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        new_fact = "Fixed memory leak in React component"
        existing_memories = [
            {
                "id": "1",
                "memory": "Fixed memory leak in React component",
                "metadata": {
                    "category": "bug_fix",
                    "created_at": "2025-01-01T10:00:00Z",
                },
            }
        ]
        metadata = {"category": "bug_fix", "created_at": "2025-01-01T10:01:00Z"}

        should_dedup, duplicate_id, similarity = deduplicator.should_deduplicate(
            new_fact, existing_memories, metadata
        )

        assert should_dedup is True
        assert duplicate_id == "1"
        assert similarity > 0.9

    def test_should_deduplicate_different_facts(self):
        """Test deduplication with different facts."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        new_fact = "Implemented user authentication system"
        existing_memories = [
            {
                "id": "1",
                "memory": "Fixed database connection issue",
                "metadata": {
                    "category": "bug_fix",
                    "created_at": "2025-01-01T10:00:00Z",
                },
            }
        ]
        metadata = {
            "category": "code_implementation",
            "created_at": "2025-01-01T10:01:00Z",
        }

        should_dedup, duplicate_id, similarity = deduplicator.should_deduplicate(
            new_fact, existing_memories, metadata
        )

        assert should_dedup is False
        assert duplicate_id is None
        assert similarity < 0.8

    def test_semantic_similarity_calculation(self):
        """Test semantic similarity calculation."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        fact1 = "Fixed critical error in payment system"
        fact2 = "Resolved bug in payment processing"

        similarity = deduplicator._calculate_semantic_similarity(fact1, fact2)

        # Both facts contain error and solution patterns
        assert similarity > 0.4

    def test_context_similarity_calculation(self):
        """Test context similarity calculation."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        metadata1 = {
            "category": "bug_fix",
            "file_references": ["app.py", "utils.py"],
            "error_related": True,
        }
        metadata2 = {
            "category": "bug_fix",
            "file_references": ["app.py"],
            "error_related": True,
        }

        similarity = deduplicator._calculate_context_similarity(metadata1, metadata2)

        # Same category, overlapping files, same error status
        assert similarity > 0.7

    def test_temporal_factor_calculation(self):
        """Test temporal factor calculation."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        # Recent timestamps (within 5 minutes)
        metadata1 = {"created_at": "2025-01-01T10:00:00Z"}
        metadata2 = {"created_at": "2025-01-01T10:03:00Z"}

        factor = deduplicator._calculate_temporal_factor(metadata1, metadata2)
        assert factor == 1.0

        # Older timestamps (1 day apart)
        metadata3 = {"created_at": "2025-01-01T10:00:00Z"}
        metadata4 = {"created_at": "2025-01-02T10:00:00Z"}

        factor = deduplicator._calculate_temporal_factor(metadata3, metadata4)
        assert factor == 0.7

    def test_complementary_information_detection(self):
        """Test complementary information detection."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        new_fact = "Solution: Use connection pooling to fix database issues"
        existing_memory = {
            "memory": "Error: Database connection timeouts in production",
            "metadata": {"error_related": True},
        }
        metadata = {"solution_related": True}

        is_complementary = deduplicator._is_complementary_information(
            new_fact, existing_memory, metadata
        )

        assert is_complementary is True

    def test_progressive_refinement_detection(self):
        """Test progressive refinement detection."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        new_fact = "Improved database query performance by 50% using optimized indexing and connection pooling"
        existing_memory = {"memory": "Database query performance issue", "metadata": {}}
        metadata = {}

        is_refinement = deduplicator._is_progressive_refinement(
            new_fact, existing_memory, metadata
        )

        assert is_refinement is True

    def test_update_threshold(self):
        """Test threshold updating."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        original_threshold = deduplicator.similarity_thresholds["bug_fix"]
        deduplicator.update_threshold("bug_fix", 0.95)

        assert deduplicator.similarity_thresholds["bug_fix"] == 0.95
        assert deduplicator.similarity_thresholds["bug_fix"] != original_threshold

    def test_deduplication_stats(self):
        """Test deduplication statistics."""
        config = {}
        deduplicator = EnhancedDeduplicator(config)

        stats = deduplicator.get_deduplication_stats()

        assert "thresholds" in stats
        assert "cache_size" in stats
        assert "semantic_patterns" in stats
        assert stats["semantic_patterns"] == 4


class TestAutonomousDeduplicationManager:
    """Test suite for autonomous deduplication manager."""

    def test_autonomous_manager_initialization(self):
        """Test autonomous deduplication manager initialization."""
        config = {}
        manager = AutonomousDeduplicationManager(config)

        assert manager.deduplicator is not None
        assert manager.learning_rate == 0.1
        assert manager.adaptation_threshold == 10
        assert manager.performance_metrics["total_processed"] == 0

    def test_process_memory_with_deduplication(self):
        """Test memory processing with deduplication."""
        config = {}
        manager = AutonomousDeduplicationManager(config)

        new_fact = "Fixed memory leak in React component"
        existing_memories = [
            {
                "id": "1",
                "memory": "Fixed memory leak in React component",
                "metadata": {"category": "bug_fix"},
            }
        ]
        metadata = {"category": "bug_fix"}

        result = manager.process_memory(new_fact, existing_memories, metadata)

        assert "should_deduplicate" in result
        assert "duplicate_id" in result
        assert "similarity_score" in result
        assert "confidence" in result
        assert "reasoning" in result

    def test_process_memory_without_deduplication(self):
        """Test memory processing without deduplication."""
        config = {}
        manager = AutonomousDeduplicationManager(config)

        new_fact = "Implemented user authentication system"
        existing_memories = [
            {
                "id": "1",
                "memory": "Fixed database connection issue",
                "metadata": {"category": "bug_fix"},
            }
        ]
        metadata = {"category": "code_implementation"}

        result = manager.process_memory(new_fact, existing_memories, metadata)

        assert result["should_deduplicate"] is False
        assert result["duplicate_id"] is None
        assert result["similarity_score"] < 0.8

    def test_confidence_calculation(self):
        """Test confidence calculation."""
        config = {}
        manager = AutonomousDeduplicationManager(config)

        # High similarity should give high confidence
        high_confidence = manager._calculate_confidence(0.95, {"category": "bug_fix"})
        assert high_confidence > 0.8

        # Low similarity should give low confidence
        low_confidence = manager._calculate_confidence(0.3, {"category": "general"})
        assert low_confidence < 0.5

    def test_reasoning_generation(self):
        """Test reasoning generation."""
        config = {}
        manager = AutonomousDeduplicationManager(config)

        # Should deduplicate
        reasoning = manager._generate_reasoning(True, 0.95, {"category": "bug_fix"})
        assert "exceeds threshold" in reasoning
        assert "0.950" in reasoning

        # Should not deduplicate
        reasoning = manager._generate_reasoning(False, 0.7, {"category": "bug_fix"})
        assert "below threshold" in reasoning
        assert "0.700" in reasoning

    def test_performance_report(self):
        """Test performance report generation."""
        config = {}
        manager = AutonomousDeduplicationManager(config)

        # Process some memories first
        manager.process_memory("test fact", [], {"category": "test"})

        report = manager.get_performance_report()

        assert "metrics" in report
        assert "thresholds" in report
        assert "adaptation_stats" in report
        assert "deduplication_stats" in report
        assert report["metrics"]["total_processed"] > 0

    def test_performance_metrics_reset(self):
        """Test performance metrics reset."""
        config = {}
        manager = AutonomousDeduplicationManager(config)

        # Process some memories first
        manager.process_memory("test fact", [], {"category": "test"})
        assert manager.performance_metrics["total_processed"] > 0

        # Reset metrics
        manager.reset_performance_metrics()
        assert manager.performance_metrics["total_processed"] == 0
        assert manager.total_evaluations == 0


class TestDeduplicationIntegration:
    """Test integration of deduplication with coding memory."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = CodingMemoryConfig()

        # Mock dependencies
        self.mock_embedding_model = Mock()
        self.mock_vector_store = Mock()
        self.mock_llm = Mock()
        self.mock_db = Mock()

        # Create patches
        self.embedding_patch = patch(
            "mem0.utils.factory.EmbedderFactory.create",
            return_value=self.mock_embedding_model,
        )
        self.vector_patch = patch(
            "mem0.utils.factory.VectorStoreFactory.create",
            return_value=self.mock_vector_store,
        )
        self.llm_patch = patch(
            "mem0.utils.factory.LlmFactory.create", return_value=self.mock_llm
        )
        self.db_patch = patch(
            "mem0.memory.storage.SQLiteManager", return_value=self.mock_db
        )

        # Start patches
        self.embedding_patch.start()
        self.vector_patch.start()
        self.llm_patch.start()
        self.db_patch.start()

    def teardown_method(self):
        """Clean up patches."""
        self.embedding_patch.stop()
        self.vector_patch.stop()
        self.llm_patch.stop()
        self.db_patch.stop()

    def test_coding_memory_with_enhanced_deduplication(self):
        """Test coding memory with enhanced deduplication."""
        memory = CodingMemory(self.config)

        # Verify deduplication manager is initialized
        assert memory.deduplication_manager is not None
        assert isinstance(memory.deduplication_manager, AutonomousDeduplicationManager)

    def test_deduplication_analytics_retrieval(self):
        """Test deduplication analytics retrieval."""
        memory = CodingMemory(self.config)

        analytics = memory.get_deduplication_analytics()

        assert "metrics" in analytics
        assert "thresholds" in analytics
        assert "adaptation_stats" in analytics
        assert "deduplication_stats" in analytics

    def test_deduplication_performance_testing(self):
        """Test deduplication performance testing."""
        memory = CodingMemory(self.config)

        test_facts = [
            {
                "fact": "Fixed memory leak in React component",
                "metadata": {"category": "bug_fix"},
                "is_duplicate": False,
            },
            {
                "fact": "Fixed memory leak in React component",
                "metadata": {"category": "bug_fix"},
                "is_duplicate": True,
            },
            {
                "fact": "Implemented user authentication system",
                "metadata": {"category": "code_implementation"},
                "is_duplicate": False,
            },
        ]

        results = memory.test_deduplication_performance(test_facts)

        assert "total_tested" in results
        assert "duplicates_detected" in results
        assert "unique_stored" in results
        assert "performance_metrics" in results
        assert "accuracy" in results
        assert results["total_tested"] == 3


class TestDeduplicationUtilities:
    """Test suite for deduplication utility functions."""

    def test_calculate_content_hash(self):
        """Test content hash calculation."""
        from mem0.memory.enhanced_deduplication import calculate_content_hash

        content = "This is a test fact"
        hash1 = calculate_content_hash(content)
        hash2 = calculate_content_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

        # Different content should have different hashes
        hash3 = calculate_content_hash("Different content")
        assert hash1 != hash3

    def test_extract_key_features(self):
        """Test key feature extraction."""
        from mem0.memory.enhanced_deduplication import extract_key_features

        fact = "Fixed memory leak in React component"
        metadata = {
            "category": "bug_fix",
            "contains_code": True,
            "error_related": True,
            "file_references": ["app.js"],
        }

        features = extract_key_features(fact, metadata)

        assert "content_hash" in features
        assert "length" in features
        assert "word_count" in features
        assert "category" in features
        assert "has_code" in features
        assert "error_related" in features
        assert "file_references" in features

        assert features["category"] == "bug_fix"
        assert features["has_code"] is True
        assert features["error_related"] is True
        assert features["word_count"] == 6

    def test_similarity_based_clustering(self):
        """Test similarity-based clustering."""
        from mem0.memory.enhanced_deduplication import similarity_based_clustering

        memories = [
            {"memory": "Fixed memory leak in React component"},
            {"memory": "Resolved memory leak in React app"},
            {"memory": "Implemented user authentication system"},
            {"memory": "Added user login functionality"},
        ]

        clusters = similarity_based_clustering(memories, similarity_threshold=0.3)

        assert len(clusters) >= 2  # Should have at least 2 clusters
        assert all(len(cluster) >= 1 for cluster in clusters)

    def test_calculate_simple_similarity(self):
        """Test simple similarity calculation."""
        from mem0.memory.enhanced_deduplication import calculate_simple_similarity

        # Identical texts
        similarity = calculate_simple_similarity("hello world", "hello world")
        assert similarity == 1.0

        # Completely different texts
        similarity = calculate_simple_similarity("hello world", "goodbye moon")
        assert similarity == 0.0

        # Partially similar texts
        similarity = calculate_simple_similarity("hello world", "hello universe")
        assert 0.0 < similarity < 1.0


class TestConfidenceScoring:
    """Test suite for confidence scoring system."""

    def test_enhanced_confidence_scorer_initialization(self):
        """Test EnhancedConfidenceScorer initialization."""
        from mem0.memory.confidence_scoring import EnhancedConfidenceScorer

        config = {"test_config": "value"}
        scorer = EnhancedConfidenceScorer(config)

        assert scorer.config == config
        assert len(scorer.category_weights) > 0
        assert scorer.category_weights["bug_fix"] == 0.95
        assert scorer.category_weights["error_solution"] == 0.98

    def test_calculate_confidence_high_quality(self):
        """Test confidence calculation for high quality memory."""
        from mem0.memory.confidence_scoring import EnhancedConfidenceScorer

        config = {"test_config": "value"}
        scorer = EnhancedConfidenceScorer(config)

        memory_content = "Fixed critical memory leak in React component by adding proper cleanup in useEffect hook"
        metadata = {
            "category": "bug_fix",
            "error_related": True,
            "solution_related": True,
            "file_references": ["src/components/UserProfile.tsx"],
            "code_blocks": True,
        }

        result = scorer.calculate_confidence(memory_content, metadata)

        assert result["confidence"] >= 0.8
        assert "components" in result
        assert "explanation" in result

    def test_context_aware_confidence_scorer(self):
        """Test ContextAwareConfidenceScorer."""
        from mem0.memory.confidence_scoring import ContextAwareConfidenceScorer

        config = {"test_config": "value"}
        scorer = ContextAwareConfidenceScorer(config)

        memory_content = "Implemented authentication middleware with JWT tokens"
        metadata = {
            "category": "code_implementation",
            "code_blocks": True,
            "solution_related": True,
        }

        result = scorer.score_for_context(memory_content, metadata, "autonomous_coding")

        assert "context_adjusted_confidence" in result
        assert result["context_type"] == "autonomous_coding"
        assert "context_profile" in result


class TestMemoryCategorization:
    """Test suite for memory categorization system."""

    def test_hierarchical_categorizer_initialization(self):
        """Test HierarchicalCategorizer initialization."""
        from mem0.memory.memory_categorization import HierarchicalCategorizer

        config = {"test_config": "value"}
        categorizer = HierarchicalCategorizer(config)

        assert len(categorizer.category_hierarchy) == 4
        assert "development" in categorizer.category_hierarchy
        assert "troubleshooting" in categorizer.category_hierarchy
        assert "operations" in categorizer.category_hierarchy
        assert "knowledge" in categorizer.category_hierarchy

    def test_categorize_memory_bug_fix(self):
        """Test categorizing bug fix memory."""
        from mem0.memory.memory_categorization import HierarchicalCategorizer

        config = {"test_config": "value"}
        categorizer = HierarchicalCategorizer(config)

        memory_content = (
            "Fixed critical bug in authentication system causing login failures"
        )
        metadata = {"error_related": True}

        result = categorizer.categorize_memory(memory_content, metadata)

        assert result["primary_category"] == "bug_fix"
        assert result["confidence"] > 0.8
        assert "hierarchical_path" in result

    def test_auto_categorizer(self):
        """Test AutoCategorizer."""
        from mem0.memory.memory_categorization import AutoCategorizer

        config = {"test_config": "value"}
        auto_categorizer = AutoCategorizer(config)

        memory_content = "Implemented caching mechanism to improve API response times"
        metadata = {}

        result = auto_categorizer.auto_categorize(memory_content, metadata)

        assert "auto_action" in result
        assert "requires_review" in result
        assert result["auto_action"] in [
            "auto_categorize",
            "suggest_with_review",
            "manual_categorization",
        ]


class TestStorageOptimization:
    """Test suite for storage optimization system."""

    def test_intelligent_storage_manager_initialization(self):
        """Test IntelligentStorageManager initialization."""
        from mem0.memory.storage_optimization import IntelligentStorageManager

        config = {"max_memories_total": 5000}
        manager = IntelligentStorageManager(config)

        assert manager.storage_limits["max_memories_total"] == 5000
        assert len(manager.retention_policies) > 0
        assert "bug_fix" in manager.retention_policies
        assert manager.retention_policies["bug_fix"]["max_age_days"] == 90

    def test_check_storage_limits(self):
        """Test checking storage limits."""
        from mem0.memory.storage_optimization import IntelligentStorageManager

        config = {"max_memories_total": 100, "max_total_size_mb": 1}
        manager = IntelligentStorageManager(config)

        # Create mock memories
        memories = [
            {"id": str(i), "memory": f"Memory {i}", "metadata": {"category": "bug_fix"}}
            for i in range(90)
        ]

        result = manager.check_storage_limits(memories)

        assert result["overall_status"] in ["normal", "warning", "critical"]
        assert "limits_status" in result
        assert "recommendations" in result

    def test_optimize_storage_lru(self):
        """Test storage optimization with LRU strategy."""
        from mem0.memory.storage_optimization import IntelligentStorageManager

        config = {"max_memories_total": 100}
        manager = IntelligentStorageManager(config)

        # Create mock memories with different access times
        memories = [
            {
                "id": str(i),
                "memory": f"Memory {i}",
                "metadata": {
                    "category": "bug_fix",
                    "last_accessed": f"2024-01-{i+1:02d}T10:00:00Z",
                },
            }
            for i in range(20)
        ]

        result = manager.optimize_storage(memories, "lru", 0.5)

        assert result["status"] == "optimization_completed"
        assert result["memories_removed"] == 10
        assert result["strategy_used"] == "lru"

    def test_autonomous_storage_manager(self):
        """Test AutonomousStorageManager."""
        from mem0.memory.storage_optimization import AutonomousStorageManager

        config = {"max_memories_total": 100, "auto_optimize_enabled": True}
        manager = AutonomousStorageManager(config)

        # Create mock memories approaching limit
        memories = [
            {"id": str(i), "memory": f"Memory {i}", "metadata": {"category": "general"}}
            for i in range(85)
        ]

        result = manager.monitor_and_optimize(memories)

        assert "optimization_performed" in result
        assert "storage_status" in result
        assert result["storage_status"] in ["normal", "warning", "critical"]


class TestMetadataTagging:
    """Test suite for metadata tagging system."""

    def test_semantic_tagger_initialization(self):
        """Test SemanticTagger initialization."""
        from mem0.memory.metadata_tagging import SemanticTagger

        config = {"test_config": "value"}
        tagger = SemanticTagger(config)

        assert len(tagger.semantic_categories) > 0
        assert "technical_concepts" in tagger.semantic_categories
        assert "problem_solving" in tagger.semantic_categories
        assert len(tagger.technology_tags) > 0

    def test_tag_memory_comprehensive(self):
        """Test comprehensive memory tagging."""
        from mem0.memory.metadata_tagging import SemanticTagger

        config = {"test_config": "value"}
        tagger = SemanticTagger(config)

        memory_content = "Fixed critical bug in React authentication using JWT tokens"
        metadata = {
            "category": "bug_fix",
            "file_references": ["src/auth/Login.tsx"],
            "created_at": "2024-01-15T10:00:00Z",
        }

        result = tagger.tag_memory(memory_content, metadata)

        assert "tags" in result
        assert "confidence" in result
        assert "tag_summary" in result
        assert "recommended_tags" in result

        # Check semantic tags
        assert "semantic" in result["tags"]

        # Check technology tags
        assert "technology" in result["tags"]

        # Check auto tags
        assert "auto" in result["tags"]

    def test_auto_tagging_manager(self):
        """Test AutoTaggingManager."""
        from mem0.memory.metadata_tagging import AutoTaggingManager

        config = {"test_config": "value"}
        manager = AutoTaggingManager(config)

        memory_content = "Optimized database query performance by adding proper indexes"
        metadata = {"category": "performance"}

        result = manager.auto_tag_memory(memory_content, metadata)

        assert "auto_tags" in result
        assert "confidence" in result
        assert "auto_tagging_decision" in result
        assert result["auto_tagging_decision"] in [
            "auto_tag_all",
            "auto_tag_high_confidence",
            "suggest_with_review",
            "manual_tagging_required",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
