#!/usr/bin/env python3
"""
Comprehensive timezone safety tests for mem0 memory modules.
This test suite ensures proper timezone handling across all modules.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from mem0.mem0.memory.confidence_scoring import _safe_datetime_now as conf_safe_now, _safe_datetime_diff as conf_safe_diff
    from mem0.mem0.memory.metadata_tagging import _safe_datetime_now as tag_safe_now, _safe_datetime_diff as tag_safe_diff
    from mem0.mem0.memory.enhanced_deduplication import _safe_datetime_now as dedup_safe_now, _safe_datetime_diff as dedup_safe_diff
    from mem0.mem0.memory.storage_optimization import _safe_datetime_now as storage_safe_now, _safe_datetime_diff as storage_safe_diff
except ImportError as e:
    pytest.skip(f"Cannot import memory modules: {e}", allow_module_level=True)


class TestTimezoneSafety:
    """Test timezone safety across all memory modules."""
    
    def test_safe_datetime_now_with_naive(self):
        """Test safe datetime now with timezone-naive reference."""
        naive_dt = datetime.fromisoformat('2024-01-01T12:00:00')
        
        # Test all modules
        conf_result = conf_safe_now(naive_dt)
        tag_result = tag_safe_now(naive_dt)
        dedup_result = dedup_safe_now(naive_dt)
        storage_result = storage_safe_now(naive_dt)
        
        # All should be naive (no tzinfo)
        assert conf_result.tzinfo is None
        assert tag_result.tzinfo is None
        assert dedup_result.tzinfo is None
        assert storage_result.tzinfo is None
    
    def test_safe_datetime_now_with_aware(self):
        """Test safe datetime now with timezone-aware reference."""
        aware_dt = datetime.fromisoformat('2024-01-01T12:00:00+05:00')
        
        # Test all modules
        conf_result = conf_safe_now(aware_dt)
        tag_result = tag_safe_now(aware_dt)
        dedup_result = dedup_safe_now(aware_dt)
        storage_result = storage_safe_now(aware_dt)
        
        # All should preserve timezone
        assert conf_result.tzinfo is not None
        assert tag_result.tzinfo is not None
        assert dedup_result.tzinfo is not None
        assert storage_result.tzinfo is not None
    
    def test_safe_datetime_diff_mixed_types(self):
        """Test safe datetime diff with mixed naive/aware types."""
        naive_dt = datetime.fromisoformat('2024-01-01T12:00:00')
        aware_dt = datetime.fromisoformat('2024-01-01T12:00:00+00:00')
        
        # Test all modules - these should not raise TypeError
        conf_diff = conf_safe_diff(aware_dt, naive_dt)
        tag_diff = tag_safe_diff(aware_dt, naive_dt)
        dedup_diff = dedup_safe_diff(aware_dt, naive_dt)
        storage_diff = storage_safe_diff(aware_dt, naive_dt)
        
        # All should return timedelta
        assert isinstance(conf_diff, timedelta)
        assert isinstance(tag_diff, timedelta)
        assert isinstance(dedup_diff, timedelta)
        assert isinstance(storage_diff, timedelta)
    
    def test_problematic_patterns_resolved(self):
        """Test that the original problematic patterns are resolved."""
        
        # Pattern 1: datetime.now(None) - should not fail
        naive_dt = datetime.fromisoformat('2024-01-01T12:00:00')
        try:
            result = conf_safe_now(naive_dt)  # tzinfo is None
            assert True  # If we get here, no TypeError was raised
        except TypeError:
            pytest.fail("safe_datetime_now should not raise TypeError with naive datetime")
        
        # Pattern 2: Mixed datetime subtraction - should not fail
        naive_dt = datetime.fromisoformat('2024-01-01T12:00:00')
        aware_dt = datetime.fromisoformat('2024-01-01T12:00:00+00:00')
        try:
            result = conf_safe_diff(aware_dt, naive_dt)
            assert True  # If we get here, no TypeError was raised
        except TypeError:
            pytest.fail("safe_datetime_diff should not raise TypeError with mixed types")
    
    def test_metadata_simulation(self):
        """Test with realistic metadata scenarios that could cause issues."""
        
        # Scenario 1: Metadata with naive datetime string
        metadata_naive = {
            'created_at': '2024-01-01T12:00:00',  # No timezone
            'last_accessed': '2024-01-02T12:00:00'  # No timezone
        }
        
        # These patterns should work safely
        created_time = datetime.fromisoformat(metadata_naive['created_at'])
        current_time = conf_safe_now(created_time)
        time_diff = conf_safe_diff(current_time, created_time)
        
        assert isinstance(time_diff, timedelta)
        
        # Scenario 2: Metadata with mixed timezone formats
        metadata_mixed = {
            'created_at': '2024-01-01T12:00:00',  # Naive
            'last_accessed': '2024-01-02T12:00:00+00:00'  # Aware
        }
        
        created_time = datetime.fromisoformat(metadata_mixed['created_at'])
        last_time = datetime.fromisoformat(metadata_mixed['last_accessed'].replace('Z', '+00:00'))
        
        # This should not raise TypeError
        time_diff = conf_safe_diff(current_time, last_time)
        assert isinstance(time_diff, timedelta)
    
    def test_consistency_across_modules(self):
        """Test that all modules handle timezone scenarios consistently."""
        
        test_cases = [
            datetime.fromisoformat('2024-01-01T12:00:00'),  # Naive
            datetime.fromisoformat('2024-01-01T12:00:00+00:00'),  # UTC
            datetime.fromisoformat('2024-01-01T12:00:00+05:00'),  # Offset
        ]
        
        for test_dt in test_cases:
            # All modules should handle the same input consistently
            conf_now = conf_safe_now(test_dt)
            tag_now = tag_safe_now(test_dt)
            dedup_now = dedup_safe_now(test_dt)
            storage_now = storage_safe_now(test_dt)
            
            # Timezone awareness should be consistent
            awareness = [dt.tzinfo is not None for dt in [conf_now, tag_now, dedup_now, storage_now]]
            assert all(awareness) or not any(awareness), f"Inconsistent timezone awareness for {test_dt}"


class TestRegression:
    """Regression tests for specific issues that were fixed."""
    
    def test_confidence_scoring_recency_boost(self):
        """Test the specific pattern from _calculate_recency_boost."""
        from mem0.mem0.memory.confidence_scoring import EnhancedConfidenceScorer
        
        # Simulate the problematic scenario
        config = {'test': True}
        scorer = EnhancedConfidenceScorer(config)
        
        # This was the failing pattern: naive datetime in last_accessed
        last_accessed = '2024-01-01T12:00:00'  # No timezone
        
        # This should not raise TypeError
        try:
            result = scorer._calculate_recency_boost(last_accessed)
            assert isinstance(result, float)
        except TypeError:
            pytest.fail("_calculate_recency_boost should not raise TypeError with naive datetime")
    
    def test_confidence_scoring_temporal_relevance(self):
        """Test the specific pattern from _calculate_temporal_relevance."""
        from mem0.mem0.memory.confidence_scoring import EnhancedConfidenceScorer
        
        config = {'test': True}
        scorer = EnhancedConfidenceScorer(config)
        
        # This was the failing pattern: naive datetime in metadata
        metadata = {'created_at': '2024-01-01T12:00:00'}  # No timezone
        
        # This should not raise TypeError
        try:
            result = scorer._calculate_temporal_relevance(metadata)
            assert isinstance(result, float)
        except TypeError:
            pytest.fail("_calculate_temporal_relevance should not raise TypeError with naive datetime")
    
    def test_context_aware_scorer_penalize_outdated(self):
        """Test the specific pattern from ContextAwareConfidenceScorer."""
        from mem0.mem0.memory.confidence_scoring import ContextAwareConfidenceScorer
        
        config = {'test': True}
        scorer = ContextAwareConfidenceScorer(config)
        
        # Simulate the problematic scenario
        base_confidence = 0.8
        metadata = {'created_at': '2024-01-01T12:00:00'}  # No timezone
        profile = {'penalize_outdated': 0.1}
        
        # This should not raise TypeError
        try:
            result = scorer._apply_context_adjustments(base_confidence, metadata, profile)
            assert isinstance(result, float)
        except TypeError:
            pytest.fail("_apply_context_adjustments should not raise TypeError with naive datetime")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_none_reference_time(self):
        """Test safe_datetime_now with None reference."""
        result = conf_safe_now(None)
        assert isinstance(result, datetime)
        # Should be naive when no reference
        assert result.tzinfo is None
    
    def test_same_type_datetimes(self):
        """Test safe_datetime_diff with same-type datetimes."""
        # Both naive
        dt1 = datetime.fromisoformat('2024-01-01T12:00:00')
        dt2 = datetime.fromisoformat('2024-01-01T11:00:00')
        result = conf_safe_diff(dt1, dt2)
        assert result == timedelta(hours=1)
        
        # Both aware
        dt1 = datetime.fromisoformat('2024-01-01T12:00:00+00:00')
        dt2 = datetime.fromisoformat('2024-01-01T11:00:00+00:00')
        result = conf_safe_diff(dt1, dt2)
        assert result == timedelta(hours=1)
    
    def test_empty_metadata(self):
        """Test handling of empty or missing metadata."""
        from mem0.mem0.memory.confidence_scoring import EnhancedConfidenceScorer
        
        scorer = EnhancedConfidenceScorer({'test': True})
        
        # Empty metadata should not cause issues
        result = scorer._calculate_temporal_relevance({})
        assert result == 1.0
        
        # Missing created_at should not cause issues
        result = scorer._calculate_temporal_relevance({'other_field': 'value'})
        assert result == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 