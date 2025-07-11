"""
Comprehensive timezone safety tests for storage optimization module.

This test suite covers:
1. Unit tests for timezone edge cases
2. Integration tests for storage optimization workflow
3. Regression tests for the original timezone bug
4. Performance tests to ensure fixes don't impact performance
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from freezegun import freeze_time

from mem0.memory.storage_optimization import (
    IntelligentStorageManager,
    AutonomousStorageManager
)
from mem0.memory.timezone_utils import (
    safe_datetime_now,
    safe_datetime_diff,
    create_memory_timestamp
)


class TestTimezoneEdgeCases:
    """Unit tests for timezone edge cases in storage optimization."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = {
            'max_memories_total': 1000,
            'max_memories_per_category': 200,
            'max_total_size_mb': 50,
            'warning_threshold': 0.8,
            'critical_threshold': 0.95
        }
        self.storage_manager = IntelligentStorageManager(self.config)
    
    def create_test_memory(self, created_at=None, last_accessed=None, category='general'):
        """Create a test memory with specified timestamps."""
        memory_id = str(uuid.uuid4())
        if created_at is None:
            created_at = create_memory_timestamp()
        
        return {
            'id': memory_id,
            'memory': f'Test memory {memory_id}',
            'metadata': {
                'created_at': created_at,
                'last_accessed': last_accessed or created_at,
                'category': category,
                'access_count': 1,
                'success_rate': 0.8
            }
        }
    
    def test_mixed_timezone_scenarios(self):
        """Test purging with memories from different timezones."""
        # Create memories with different timezone formats
        memories = [
            # UTC with Z suffix
            self.create_test_memory(
                created_at='2024-01-01T12:00:00Z',
                category='testing'
            ),
            # UTC with +00:00 suffix
            self.create_test_memory(
                created_at='2024-01-01T12:00:00+00:00',
                category='testing'
            ),
            # Different timezone
            self.create_test_memory(
                created_at='2024-01-01T12:00:00+05:00',
                category='testing'
            ),
            # Recent memory (should not be purged)
            self.create_test_memory(
                created_at=create_memory_timestamp(),
                category='testing'
            )
        ]
        
        # Test context-aware purging
        with freeze_time("2024-06-01T12:00:00Z"):
            purged = self.storage_manager._context_aware_purge(memories, 2)
            
            # Should purge older memories regardless of timezone format
            assert len(purged) == 2
            purged_ids = [m['id'] for m in purged]
            
            # Recent memory should not be purged
            recent_memory = memories[3]
            assert recent_memory['id'] not in purged_ids
    
    def test_dst_transition_scenarios(self):
        """Test memory age calculation during DST transitions."""
        # Test spring DST transition (2024-03-10 in US)
        memories = [
            self.create_test_memory(
                created_at='2024-03-09T12:00:00Z',  # Before DST
                category='testing'
            ),
            self.create_test_memory(
                created_at='2024-03-11T12:00:00Z',  # After DST
                category='testing'
            )
        ]
        
        # Test during DST transition
        with freeze_time("2024-03-10T12:00:00Z"):
            policy = self.storage_manager.retention_policies['testing']
            purged = self.storage_manager._purge_category_memories(
                memories, 1, policy
            )
            
            # Should handle DST transition gracefully
            assert len(purged) <= 1
            
            # Verify age calculation is consistent
            for memory in memories:
                created_at = memory['metadata']['created_at']
                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                age_diff = safe_datetime_diff(safe_datetime_now(), created_time)
                assert isinstance(age_diff, timedelta)
                assert age_diff.total_seconds() >= 0
    
    def test_recency_calculation_accuracy(self):
        """Test recency factor calculation with various timezone formats."""
        test_cases = [
            {
                'timestamp': '2024-01-01T12:00:00Z',
                'expected_range': (0.0, 0.1),  # Very old
                'description': 'UTC with Z suffix'
            },
            {
                'timestamp': '2024-01-01T12:00:00+00:00',
                'expected_range': (0.0, 0.1),  # Very old
                'description': 'UTC with +00:00 suffix'
            },
            {
                'timestamp': '2024-01-01T07:00:00-05:00',  # Same as above in different timezone
                'expected_range': (0.0, 0.1),  # Very old
                'description': 'Eastern timezone'
            }
        ]
        
        with freeze_time("2024-06-01T12:00:00Z"):
            for case in test_cases:
                memory = self.create_test_memory(
                    created_at=case['timestamp'],
                    last_accessed=case['timestamp']
                )
                
                recency_factor = self.storage_manager._calculate_recency_factor(
                    memory['metadata']
                )
                
                assert case['expected_range'][0] <= recency_factor <= case['expected_range'][1], \
                    f"Recency factor {recency_factor} not in expected range {case['expected_range']} " \
                    f"for {case['description']}"
    
    def test_memory_age_calculation_edge_cases(self):
        """Test memory age calculation with edge cases."""
        edge_cases = [
            # Invalid timestamp format
            {'created_at': 'invalid-timestamp', 'should_handle': True},
            # Missing timezone info
            {'created_at': '2024-01-01T12:00:00', 'should_handle': True},
            # Very old timestamp
            {'created_at': '1970-01-01T00:00:00Z', 'should_handle': True},
            # Future timestamp
            {'created_at': '2025-01-01T00:00:00Z', 'should_handle': True},
            # Leap year
            {'created_at': '2024-02-29T12:00:00Z', 'should_handle': True},
        ]
        
        for case in edge_cases:
            memory = self.create_test_memory(created_at=case['created_at'])
            
            # Should not raise exception
            try:
                recency_factor = self.storage_manager._calculate_recency_factor(
                    memory['metadata']
                )
                assert isinstance(recency_factor, float)
                assert 0.0 <= recency_factor <= 1.0
            except Exception as e:
                if case['should_handle']:
                    pytest.fail(f"Should handle edge case {case['created_at']}: {e}")


class TestStorageOptimizationIntegration:
    """Integration tests for the full storage optimization workflow."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = {
            'max_memories_total': 100,
            'max_memories_per_category': 50,
            'max_total_size_mb': 10,
            'warning_threshold': 0.7,
            'critical_threshold': 0.9,
            'auto_optimize_enabled': True,
            'optimization_interval_hours': 24
        }
        self.autonomous_manager = AutonomousStorageManager(self.config)
    
    def create_memory_dataset(self, count=50):
        """Create a dataset of test memories with various timestamps."""
        memories = []
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        for i in range(count):
            # Create memories with different ages
            age_days = i * 2  # 0, 2, 4, 6, ... days old
            created_time = base_time - timedelta(days=age_days)
            
            memory = {
                'id': str(uuid.uuid4()),
                'memory': f'Test memory {i} with content length variation' * (i % 5 + 1),
                'metadata': {
                    'created_at': created_time.isoformat(),
                    'last_accessed': created_time.isoformat(),
                    'category': ['general', 'testing', 'debugging'][i % 3],
                    'access_count': max(1, i % 10),
                    'success_rate': 0.5 + (i % 5) * 0.1,
                    'error_related': i % 4 == 0,
                    'solution_related': i % 3 == 0
                }
            }
            memories.append(memory)
        
        return memories
    
    @freeze_time("2024-06-01T12:00:00Z")
    def test_autonomous_optimization_timezone_consistency(self):
        """Test that autonomous optimization maintains timezone consistency."""
        memories = self.create_memory_dataset(80)  # Over threshold
        
        # Trigger autonomous optimization
        result = self.autonomous_manager.monitor_and_optimize(memories)
        
        # Should trigger optimization due to high memory count
        assert result['optimization_performed'] is True
        assert 'purged_memory_ids' in result
        
        # Verify optimization timestamp is properly formatted
        assert self.autonomous_manager.last_optimization is not None
        
        # Should be ISO format with timezone info
        timestamp = self.autonomous_manager.last_optimization
        parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert parsed_time.tzinfo is not None
        
        # Verify optimization history timestamp consistency
        history = self.autonomous_manager.optimization_history
        assert len(history) > 0
        
        latest_record = history[-1]
        record_timestamp = latest_record['timestamp']
        record_time = datetime.fromisoformat(record_timestamp.replace('Z', '+00:00'))
        assert record_time.tzinfo is not None
    
    @freeze_time("2024-06-01T12:00:00Z")
    def test_full_purge_workflow_with_real_timestamps(self):
        """Test complete purge workflow with realistic timestamp scenarios."""
        # Create memories with various realistic timestamp formats
        memories = [
            # Different timezone formats that should be handled consistently
            {
                'id': str(uuid.uuid4()),
                'memory': 'Memory with Z suffix timestamp',
                'metadata': {
                    'created_at': '2024-01-01T12:00:00Z',
                    'last_accessed': '2024-01-01T12:00:00Z',
                    'category': 'testing',
                    'access_count': 1,
                    'success_rate': 0.5
                }
            },
            {
                'id': str(uuid.uuid4()),
                'memory': 'Memory with +00:00 suffix timestamp',
                'metadata': {
                    'created_at': '2024-01-01T12:00:00+00:00',
                    'last_accessed': '2024-01-01T12:00:00+00:00',
                    'category': 'testing',
                    'access_count': 1,
                    'success_rate': 0.5
                }
            },
            {
                'id': str(uuid.uuid4()),
                'memory': 'Memory with different timezone',
                'metadata': {
                    'created_at': '2024-01-01T07:00:00-05:00',  # Same as above in EST
                    'last_accessed': '2024-01-01T07:00:00-05:00',
                    'category': 'testing',
                    'access_count': 1,
                    'success_rate': 0.5
                }
            },
            {
                'id': str(uuid.uuid4()),
                'memory': 'Recent memory should not be purged',
                'metadata': {
                    'created_at': '2024-05-30T12:00:00Z',  # Recent
                    'last_accessed': '2024-05-30T12:00:00Z',
                    'category': 'testing',
                    'access_count': 5,
                    'success_rate': 0.9
                }
            }
        ]
        
        # Test different purging strategies
        strategies = ['lru', 'priority_based', 'context_aware', 'hybrid']
        
        for strategy in strategies:
            result = self.autonomous_manager.storage_manager.optimize_storage(
                memories.copy(), strategy=strategy, target_reduction=0.5
            )
            
            # Should successfully optimize without timezone errors
            assert result['status'] == 'optimization_completed'
            assert 'memories_removed' in result
            assert 'size_saved_mb' in result
            
            # Verify purged memories are the older ones
            purged_ids = set(result['purged_memory_ids'])
            
            # Recent memory should not be purged
            recent_memory_id = memories[3]['id']
            assert recent_memory_id not in purged_ids, \
                f"Recent memory was incorrectly purged with {strategy} strategy"
    
    def test_scheduled_optimization_timing(self):
        """Test that scheduled optimization timing respects timezone consistency."""
        # Set initial optimization time
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        with freeze_time(initial_time):
            self.autonomous_manager.last_optimization = create_memory_timestamp()
            initial_timestamp = self.autonomous_manager.last_optimization
        
        # Test various future times
        test_times = [
            # Before interval (should not trigger)
            initial_time + timedelta(hours=12),
            # Exactly at interval (should trigger)
            initial_time + timedelta(hours=24),
            # After interval (should trigger)
            initial_time + timedelta(hours=36),
            # DST transition
            initial_time + timedelta(days=70)  # Around DST change
        ]
        
        for test_time in test_times:
            with freeze_time(test_time):
                is_due = self.autonomous_manager._is_scheduled_optimization_due()
                
                time_diff = test_time - initial_time
                expected_due = time_diff.total_seconds() >= 24 * 3600
                
                assert is_due == expected_due, \
                    f"Scheduling logic failed at {test_time}: expected {expected_due}, got {is_due}"


class TestTimezoneRegressionTests:
    """Regression tests for the specific timezone bug that was fixed."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = {
            'max_memories_total': 1000,
            'max_memories_per_category': 200
        }
        self.storage_manager = IntelligentStorageManager(self.config)
    
    def test_original_timezone_bug_regression(self):
        """
        Regression test for the original timezone bug.
        
        Original bug: datetime.now() (timezone-naive) was compared with
        timezone-aware datetime objects, causing incorrect age calculations.
        """
        # Create memory with timezone-aware timestamp
        utc_time = datetime.now(timezone.utc)
        memory = {
            'id': str(uuid.uuid4()),
            'memory': 'Test memory for regression test',
            'metadata': {
                'created_at': utc_time.isoformat(),
                'last_accessed': utc_time.isoformat(),
                'category': 'testing',
                'access_count': 1,
                'success_rate': 0.5
            }
        }
        
        # Test that age calculation works correctly with timezone-aware timestamps
        policy = self.storage_manager.retention_policies['testing']
        
        # This should not raise any exceptions
        try:
            purged = self.storage_manager._purge_category_memories(
                [memory], 1, policy
            )
            
            # Recent memory should not be purged due to age
            # (it should only be purged if score is very low)
            if len(purged) > 0:
                # If purged, it should be due to low score, not age
                assert memory['metadata']['success_rate'] < 0.3 or \
                       memory['metadata']['access_count'] < 2
            
        except (TypeError, AttributeError) as e:
            pytest.fail(f"Original timezone bug regression detected: {e}")
    
    def test_timezone_conversion_consistency(self):
        """Test that timezone conversions are consistent across the system."""
        # Create memories with various timezone formats
        timestamps = [
            '2024-01-01T12:00:00Z',
            '2024-01-01T12:00:00+00:00',
            '2024-01-01T07:00:00-05:00',  # Same time in EST
            '2024-01-01T17:00:00+05:00',  # Same time in +5 timezone
        ]
        
        memories = []
        for i, timestamp in enumerate(timestamps):
            memory = {
                'id': str(uuid.uuid4()),
                'memory': f'Test memory {i}',
                'metadata': {
                    'created_at': timestamp,
                    'last_accessed': timestamp,
                    'category': 'testing',
                    'access_count': 1,
                    'success_rate': 0.5
                }
            }
            memories.append(memory)
        
        # All these memories represent the same time, so they should have
        # the same recency factor
        with freeze_time("2024-06-01T12:00:00Z"):
            recency_factors = []
            for memory in memories:
                factor = self.storage_manager._calculate_recency_factor(
                    memory['metadata']
                )
                recency_factors.append(factor)
            
            # All recency factors should be approximately equal
            # (within small floating point tolerance)
            base_factor = recency_factors[0]
            for factor in recency_factors[1:]:
                assert abs(factor - base_factor) < 0.001, \
                    f"Timezone conversion inconsistency: {recency_factors}"
    
    def test_memory_age_calculation_accuracy_regression(self):
        """Test that memory age calculations are accurate after timezone fixes."""
        # Create memories with known ages
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        test_cases = [
            {'days_old': 0, 'should_purge': False},     # Brand new
            {'days_old': 30, 'should_purge': False},    # 30 days (within testing policy)
            {'days_old': 50, 'should_purge': True},     # 50 days (beyond testing policy)
            {'days_old': 100, 'should_purge': True},    # 100 days (definitely old)
        ]
        
        current_time = base_time + timedelta(days=60)  # 60 days from base
        
        with freeze_time(current_time):
            for case in test_cases:
                memory_time = base_time + timedelta(days=case['days_old'])
                memory = {
                    'id': str(uuid.uuid4()),
                    'memory': f'Test memory {case["days_old"]} days old',
                    'metadata': {
                        'created_at': memory_time.isoformat(),
                        'last_accessed': memory_time.isoformat(),
                        'category': 'testing',
                        'access_count': 5,  # High access count
                        'success_rate': 0.9  # High success rate
                    }
                }
                
                policy = self.storage_manager.retention_policies['testing']
                purged = self.storage_manager._purge_category_memories(
                    [memory], 1, policy
                )
                
                actual_age_days = (current_time - memory_time).days
                expected_purge = actual_age_days > policy['max_age_days']
                actual_purged = len(purged) > 0
                
                # Age calculation should be accurate
                if expected_purge:
                    assert actual_purged, \
                        f"Memory {actual_age_days} days old should be purged " \
                        f"(policy max: {policy['max_age_days']} days)"
                else:
                    # If not purged due to age, should only be purged due to low score
                    if actual_purged:
                        # Calculate the score to verify it's low
                        score = self.storage_manager._calculate_category_specific_score(
                            memory, policy
                        )
                        assert score < 0.3, \
                            f"Memory purged with score {score} >= 0.3 and age {actual_age_days} days"


class TestPerformanceRegression:
    """Performance tests to ensure timezone fixes don't impact performance."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = {
            'max_memories_total': 10000,
            'max_memories_per_category': 2000
        }
        self.storage_manager = IntelligentStorageManager(self.config)
    
    def create_large_memory_dataset(self, count=1000):
        """Create a large dataset for performance testing."""
        memories = []
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        for i in range(count):
            memory_time = base_time - timedelta(days=i % 365)
            memory = {
                'id': str(uuid.uuid4()),
                'memory': f'Performance test memory {i}',
                'metadata': {
                    'created_at': memory_time.isoformat(),
                    'last_accessed': memory_time.isoformat(),
                    'category': ['general', 'testing', 'debugging', 'performance'][i % 4],
                    'access_count': i % 20,
                    'success_rate': 0.5 + (i % 5) * 0.1
                }
            }
            memories.append(memory)
        
        return memories
    
    @pytest.mark.performance
    def test_timezone_operations_performance(self):
        """Test that timezone operations maintain acceptable performance."""
        import time
        
        memories = self.create_large_memory_dataset(1000)
        
        # Test recency calculation performance
        start_time = time.time()
        for memory in memories[:100]:  # Test subset for speed
            self.storage_manager._calculate_recency_factor(memory['metadata'])
        recency_time = time.time() - start_time
        
        # Should complete within reasonable time (less than 1 second for 100 memories)
        assert recency_time < 1.0, f"Recency calculation too slow: {recency_time:.2f}s"
        
        # Test purge operation performance
        start_time = time.time()
        policy = self.storage_manager.retention_policies['testing']
        purged = self.storage_manager._purge_category_memories(
            memories[:100], 50, policy
        )
        purge_time = time.time() - start_time
        
        # Should complete within reasonable time (less than 2 seconds for 100 memories)
        assert purge_time < 2.0, f"Purge operation too slow: {purge_time:.2f}s"
        
        # Verify operation actually worked
        assert isinstance(purged, list)
        assert len(purged) <= 50


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 