#!/usr/bin/env python3
"""
Quick test to verify timezone fixes in storage optimization.

This script performs a simplified test to verify that:
1. The timezone functions are working correctly
2. The storage optimization module can handle timezone-aware timestamps
3. No critical errors occur during basic operations
"""

import sys
import traceback
from datetime import datetime, timedelta, timezone


def test_timezone_utilities():
    """Test the timezone utility functions."""
    print("🔍 Testing timezone utility functions...")

    try:
        from mem0.memory.timezone_utils import (
            create_memory_timestamp,
            safe_datetime_diff,
            safe_datetime_now,
        )

        # Test safe_datetime_now
        now = safe_datetime_now()
        assert isinstance(now, datetime)
        print("✅ safe_datetime_now() works correctly")

        # Test create_memory_timestamp
        timestamp = create_memory_timestamp()
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # Should be ISO format
        print("✅ create_memory_timestamp() works correctly")

        # Test safe_datetime_diff
        time1 = datetime.now(timezone.utc)
        time2 = time1 + timedelta(hours=1)
        diff = safe_datetime_diff(time2, time1)
        assert isinstance(diff, timedelta)
        assert diff.total_seconds() > 0
        print("✅ safe_datetime_diff() works correctly")

        return True

    except Exception as e:
        print(f"❌ Timezone utilities test failed: {e}")
        traceback.print_exc()
        return False


def test_storage_optimization_basic():
    """Test basic storage optimization functionality."""
    print("\n🔍 Testing storage optimization basic functionality...")

    try:
        from mem0.memory.storage_optimization import IntelligentStorageManager

        # Create storage manager
        config = {
            "max_memories_total": 1000,
            "max_memories_per_category": 200,
            "max_total_size_mb": 50,
            "warning_threshold": 0.8,
            "critical_threshold": 0.95,
        }

        storage_manager = IntelligentStorageManager(config)
        print("✅ IntelligentStorageManager created successfully")

        # Test with simple memory
        memory = {
            "id": "test-memory-1",
            "memory": "This is a test memory",
            "metadata": {
                "created_at": "2024-01-01T12:00:00Z",
                "last_accessed": "2024-01-01T12:00:00Z",
                "category": "testing",
                "access_count": 1,
                "success_rate": 0.5,
            },
        }

        memories = [memory]

        # Test storage limit checking
        result = storage_manager.check_storage_limits(memories)
        assert "overall_status" in result
        assert "current_stats" in result
        print("✅ check_storage_limits() works correctly")

        # Test memory priority calculation
        priority = storage_manager._calculate_memory_priority(memory)
        assert isinstance(priority, float)
        assert 0.0 <= priority <= 1.0
        print("✅ _calculate_memory_priority() works correctly")

        # Test recency factor calculation
        recency = storage_manager._calculate_recency_factor(memory["metadata"])
        assert isinstance(recency, float)
        assert 0.0 <= recency <= 1.0
        print("✅ _calculate_recency_factor() works correctly")

        return True

    except Exception as e:
        print(f"❌ Storage optimization test failed: {e}")
        traceback.print_exc()
        return False


def test_timezone_edge_cases():
    """Test timezone edge cases."""
    print("\n🔍 Testing timezone edge cases...")

    try:
        from mem0.memory.storage_optimization import IntelligentStorageManager

        config = {"max_memories_total": 1000}
        storage_manager = IntelligentStorageManager(config)

        # Test different timezone formats
        test_cases = [
            "2024-01-01T12:00:00Z",
            "2024-01-01T12:00:00+00:00",
            "2024-01-01T07:00:00-05:00",
            "2024-01-01T17:00:00+05:00",
        ]

        for i, timestamp in enumerate(test_cases):
            memory = {
                "id": f"test-memory-{i}",
                "memory": f"Test memory {i}",
                "metadata": {
                    "created_at": timestamp,
                    "last_accessed": timestamp,
                    "category": "testing",
                    "access_count": 1,
                    "success_rate": 0.5,
                },
            }

            # This should not raise exceptions
            recency = storage_manager._calculate_recency_factor(memory["metadata"])
            assert isinstance(recency, float)

        print("✅ Timezone edge cases handled correctly")
        return True

    except Exception as e:
        print(f"❌ Timezone edge cases test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all quick tests."""
    print("🧪 Quick Timezone Safety Test")
    print("=" * 40)

    tests = [
        ("Timezone Utilities", test_timezone_utilities),
        ("Storage Optimization Basic", test_storage_optimization_basic),
        ("Timezone Edge Cases", test_timezone_edge_cases),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        print("-" * 30)

        try:
            if test_func():
                print(f"✅ PASSED: {test_name}")
                passed += 1
            else:
                print(f"❌ FAILED: {test_name}")
                failed += 1
        except Exception as e:
            print(f"💥 ERROR: {test_name} - {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 40)
    print("📊 QUICK TEST SUMMARY")
    print("=" * 40)
    print(f"Total Tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL QUICK TESTS PASSED!")
        print("✅ Timezone fixes appear to be working correctly.")
        return True
    else:
        print(f"\n❌ {failed} TESTS FAILED!")
        print("🚨 There are issues with the timezone fixes.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
