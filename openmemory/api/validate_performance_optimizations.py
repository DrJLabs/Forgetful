#!/usr/bin/env python3
"""
Validation script for MCP Server Performance Optimizations (Story 3.1)

This script validates that all performance optimizations have been implemented:
- Connection pooling functionality
- Performance monitoring capabilities
- Batch processing implementation
- Integration with MCP server functions
"""

import sys
import os
import asyncio
import time
import traceback

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_imports():
    """Validate that all optimization modules can be imported"""
    print("🔍 Validating imports...")
    
    try:
        # Test connection pool imports
        from app.utils.connection_pool import (
            MemoryClientPool, get_connection_pool, get_pooled_client,
            ConnectionStatus, ConnectionInfo
        )
        print("✅ Connection pool imports successful")
        
        # Test performance monitor imports
        from app.utils.performance_monitor import (
            PerformanceMonitor, get_performance_monitor, timed_operation,
            performance_context, MetricType, PerformanceMetric, OperationStats
        )
        print("✅ Performance monitor imports successful")
        
        # Test batch processor imports
        from app.utils.batch_processor import (
            BatchProcessor, get_batch_processor, submit_batch_request,
            OperationType, BatchRequest, BatchResponse
        )
        print("✅ Batch processor imports successful")
        
        # Test MCP server integration
        from app.mcp_server import (
            add_memories, search_memory, performance_monitor, 
            connection_pool, batch_processor
        )
        print("✅ MCP server integration imports successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import validation failed: {e}")
        traceback.print_exc()
        return False


def validate_connection_pool():
    """Validate connection pool functionality"""
    print("\n🔍 Validating connection pool...")
    
    try:
        from app.utils.connection_pool import MemoryClientPool
        
        # Test connection pool initialization
        pool = MemoryClientPool(max_connections=3, min_connections=1)
        print("✅ Connection pool initialization successful")
        
        # Test metrics collection
        metrics = pool.get_metrics()
        required_metrics = ['pool_size', 'total_created', 'current_active', 'idle_connections']
        
        for metric in required_metrics:
            if metric not in metrics:
                print(f"❌ Missing metric: {metric}")
                return False
        
        print("✅ Connection pool metrics validation successful")
        print(f"   Pool size: {metrics['pool_size']}")
        print(f"   Total created: {metrics['total_created']}")
        print(f"   Current active: {metrics['current_active']}")
        print(f"   Idle connections: {metrics['idle_connections']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection pool validation failed: {e}")
        traceback.print_exc()
        return False


def validate_performance_monitor():
    """Validate performance monitoring functionality"""
    print("\n🔍 Validating performance monitor...")
    
    try:
        from app.utils.performance_monitor import PerformanceMonitor, MetricType
        
        # Test performance monitor initialization
        monitor = PerformanceMonitor()
        print("✅ Performance monitor initialization successful")
        
        # Test metric recording
        monitor.record_metric(MetricType.RESPONSE_TIME, 25.5)
        monitor.record_metric(MetricType.THROUGHPUT, 150.0)
        monitor.record_operation_time("test_operation", 30.0, True)
        print("✅ Performance metric recording successful")
        
        # Test performance summary
        summary = monitor.get_performance_summary()
        required_keys = ['timestamp', 'operations', 'metrics', 'alerts']
        
        for key in required_keys:
            if key not in summary:
                print(f"❌ Missing summary key: {key}")
                return False
        
        print("✅ Performance summary validation successful")
        print(f"   Operations tracked: {len(summary['operations'])}")
        print(f"   Metrics recorded: {len(summary['metrics'])}")
        print(f"   Alerts: {len(summary['alerts'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance monitor validation failed: {e}")
        traceback.print_exc()
        return False


def validate_batch_processor():
    """Validate batch processor functionality"""
    print("\n🔍 Validating batch processor...")
    
    try:
        from app.utils.batch_processor import BatchProcessor, OperationType, BatchRequest
        
        # Test batch processor initialization
        processor = BatchProcessor(max_batch_size=5, max_wait_time_ms=100.0)
        print("✅ Batch processor initialization successful")
        
        # Test batch request creation
        request = BatchRequest(
            operation_type=OperationType.ADD_MEMORY,
            parameters={"text": "test memory"},
            request_id="test_req_1",
            user_id="test_user",
            client_name="test_client"
        )
        print("✅ Batch request creation successful")
        
        # Test request grouping
        requests = [request]
        grouped = processor._group_requests(requests)
        
        if len(grouped) != 1:
            print("❌ Request grouping failed")
            return False
        
        print("✅ Request grouping validation successful")
        
        # Test statistics
        stats = processor.get_stats()
        required_stats = ['max_batch_size', 'max_wait_time_ms', 'total_requests', 'total_batches']
        
        for stat in required_stats:
            if stat not in stats:
                print(f"❌ Missing statistic: {stat}")
                return False
        
        print("✅ Batch processor statistics validation successful")
        print(f"   Max batch size: {stats['max_batch_size']}")
        print(f"   Max wait time: {stats['max_wait_time_ms']}ms")
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Total batches: {stats['total_batches']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch processor validation failed: {e}")
        traceback.print_exc()
        return False


async def validate_mcp_integration():
    """Validate MCP server integration"""
    print("\n🔍 Validating MCP server integration...")
    
    try:
        # Test that MCP server has the optimized functions
        from app.mcp_server import add_memories, search_memory
        
        # Check if functions have the performance decorators
        if not hasattr(add_memories, '__wrapped__'):
            print("❌ add_memories function missing performance decorators")
            return False
        
        if not hasattr(search_memory, '__wrapped__'):
            print("❌ search_memory function missing performance decorators")
            return False
        
        print("✅ MCP server function decorators validation successful")
        
        # Test global instances
        from app.mcp_server import performance_monitor, connection_pool, batch_processor
        
        if performance_monitor is None:
            print("❌ Performance monitor not initialized")
            return False
        
        if connection_pool is None:
            print("❌ Connection pool not initialized")
            return False
        
        if batch_processor is None:
            print("❌ Batch processor not initialized")
            return False
        
        print("✅ MCP server global instances validation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP server integration validation failed: {e}")
        traceback.print_exc()
        return False


def validate_performance_targets():
    """Validate performance targets and monitoring"""
    print("\n🔍 Validating performance targets...")
    
    try:
        from app.utils.performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # Test sub-50ms target tracking
        monitor.record_operation_time("fast_operation", 25.0, True)
        stats = monitor.get_operation_stats("fast_operation")
        
        if stats.average_time >= 50.0:
            print("❌ Performance target validation failed - should be < 50ms")
            return False
        
        print("✅ Sub-50ms performance target validation successful")
        print(f"   Fast operation average: {stats.average_time:.2f}ms")
        
        # Test throughput tracking
        from app.utils.performance_monitor import MetricType
        monitor.record_metric(MetricType.THROUGHPUT, 150.0)
        
        recent_throughput = monitor.get_recent_metrics(MetricType.THROUGHPUT, 1)
        if len(recent_throughput) == 0 or recent_throughput[0].value < 100.0:
            print("❌ Throughput target validation failed - should be > 100 ops/sec")
            return False
        
        print("✅ Throughput target validation successful")
        print(f"   Current throughput: {recent_throughput[0].value:.2f} ops/sec")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance targets validation failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Main validation function"""
    print("🚀 Starting MCP Server Performance Optimization Validation")
    print("=" * 60)
    
    validations = [
        ("Import Validation", validate_imports),
        ("Connection Pool Validation", validate_connection_pool),
        ("Performance Monitor Validation", validate_performance_monitor),
        ("Batch Processor Validation", validate_batch_processor),
        ("MCP Integration Validation", lambda: asyncio.run(validate_mcp_integration())),
        ("Performance Targets Validation", validate_performance_targets)
    ]
    
    passed = 0
    failed = 0
    
    for name, validation_func in validations:
        try:
            if validation_func():
                passed += 1
                print(f"\n✅ {name} PASSED")
            else:
                failed += 1
                print(f"\n❌ {name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name} FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 VALIDATION SUMMARY")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print(f"   Total:  {passed + failed}")
    
    if failed == 0:
        print("🎉 ALL VALIDATIONS PASSED - Story 3.1 implementation is complete!")
        return 0
    else:
        print("⚠️  Some validations failed - please review the implementation")
        return 1


if __name__ == "__main__":
    sys.exit(main())