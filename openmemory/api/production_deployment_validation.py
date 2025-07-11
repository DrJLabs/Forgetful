#!/usr/bin/env python3
"""
Production Deployment Validation for MCP Server Performance Optimizations

This script validates that the MCP server performance optimizations are ready
for production deployment by checking all critical components and performance targets.
"""

import sys
import os
import asyncio
import time
import traceback
import json
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ValidationLevel(Enum):
    """Validation levels for different checks"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    name: str
    level: ValidationLevel
    passed: bool
    message: str
    details: Dict[str, Any] = None
    duration_ms: float = 0.0


class ProductionValidator:
    """Production deployment validator for MCP server optimizations"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.start_time = time.time()
    
    async def validate_component(self, name: str, level: ValidationLevel, check_func, *args, **kwargs) -> ValidationResult:
        """Validate a component and record the result"""
        start_time = time.time()
        
        try:
            result = check_func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                # Handle async functions
                result = await result
            
            duration_ms = (time.time() - start_time) * 1000
            
            if isinstance(result, tuple):
                passed, message, details = result
            elif isinstance(result, bool):
                passed, message, details = result, "Check completed", {}
            else:
                passed, message, details = True, str(result), {}
            
            validation_result = ValidationResult(
                name=name,
                level=level,
                passed=passed,
                message=message,
                details=details or {},
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            validation_result = ValidationResult(
                name=name,
                level=level,
                passed=False,
                message=f"Validation failed: {str(e)}",
                details={"exception": str(e), "traceback": traceback.format_exc()},
                duration_ms=duration_ms
            )
        
        self.results.append(validation_result)
        return validation_result
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        total_duration = (time.time() - self.start_time) * 1000
        
        summary = {
            "total_checks": len(self.results),
            "total_duration_ms": total_duration,
            "passed": 0,
            "failed": 0,
            "by_level": {level.value: {"passed": 0, "failed": 0} for level in ValidationLevel},
            "critical_failures": [],
            "high_failures": [],
            "overall_status": "unknown"
        }
        
        for result in self.results:
            if result.passed:
                summary["passed"] += 1
                summary["by_level"][result.level.value]["passed"] += 1
            else:
                summary["failed"] += 1
                summary["by_level"][result.level.value]["failed"] += 1
                
                if result.level == ValidationLevel.CRITICAL:
                    summary["critical_failures"].append(result.name)
                elif result.level == ValidationLevel.HIGH:
                    summary["high_failures"].append(result.name)
        
        # Determine overall status
        if summary["by_level"]["critical"]["failed"] > 0:
            summary["overall_status"] = "critical_failure"
        elif summary["by_level"]["high"]["failed"] > 0:
            summary["overall_status"] = "high_risk"
        elif summary["failed"] > 0:
            summary["overall_status"] = "warning"
        else:
            summary["overall_status"] = "ready"
        
        return summary


# Validation Functions

def validate_python_environment():
    """Validate Python environment and dependencies"""
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 9):
        return False, f"Python 3.9+ required, found {python_version.major}.{python_version.minor}", {}
    
    try:
        import asyncio
        import dataclasses
        import typing
        import json
        import threading
        import contextvars
        
        return True, f"Python {python_version.major}.{python_version.minor}.{python_version.micro} environment validated", {
            "python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
            "required_modules": ["asyncio", "dataclasses", "typing", "json", "threading", "contextvars"]
        }
    except ImportError as e:
        return False, f"Missing required Python modules: {e}", {}


def validate_file_structure():
    """Validate that all required files exist"""
    required_files = [
        "app/utils/connection_pool.py",
        "app/utils/performance_monitor.py", 
        "app/utils/batch_processor.py",
        "app/utils/memory_factory.py",
        "app/utils/mcp_initialization.py",
        "app/mcp_server.py",
        "tests/test_mcp_performance.py"
    ]
    
    missing_files = []
    existing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            existing_files.append(file_path)
        else:
            missing_files.append(file_path)
    
    if missing_files:
        return False, f"Missing required files: {missing_files}", {
            "missing": missing_files,
            "existing": existing_files
        }
    
    return True, f"All {len(required_files)} required files found", {
        "files_validated": required_files
    }


async def validate_performance_monitoring():
    """Validate performance monitoring system"""
    try:
        from app.utils.performance_monitor import PerformanceMonitor, MetricType
        
        monitor = PerformanceMonitor()
        
        # Test metric recording
        monitor.record_metric(MetricType.RESPONSE_TIME, 25.0)
        monitor.record_operation_time("test_operation", 30.0, True)
        
        # Test performance summary
        summary = monitor.get_performance_summary()
        
        required_keys = ['timestamp', 'operations', 'metrics', 'alerts']
        missing_keys = [key for key in required_keys if key not in summary]
        
        if missing_keys:
            return False, f"Performance summary missing keys: {missing_keys}", {}
        
        # Test thresholds
        if not hasattr(monitor, '_thresholds'):
            return False, "Performance monitor missing threshold configuration", {}
        
        thresholds = monitor._thresholds
        if thresholds.get('response_time_ms', 0) != 50.0:
            return False, f"Sub-50ms target not configured correctly: {thresholds.get('response_time_ms')}", {}
        
        return True, "Performance monitoring system validated", {
            "metrics_recorded": 2,
            "summary_keys": list(summary.keys()),
            "response_time_target_ms": thresholds.get('response_time_ms'),
            "error_rate_target": thresholds.get('error_rate')
        }
        
    except Exception as e:
        return False, f"Performance monitoring validation failed: {e}", {"exception": str(e)}


async def validate_connection_pooling():
    """Validate connection pool functionality"""
    try:
        from app.utils.memory_factory import MemoryClientFactory
        
        # Configure in mock mode for testing
        MemoryClientFactory.configure(mock_mode=True)
        
        from app.utils.connection_pool import MemoryClientPool
        
        pool = MemoryClientPool(max_connections=3, min_connections=1)
        metrics = pool.get_metrics()
        
        required_metrics = ['pool_size', 'total_created', 'current_active', 'idle_connections']
        missing_metrics = [m for m in required_metrics if m not in metrics]
        
        if missing_metrics:
            return False, f"Connection pool missing metrics: {missing_metrics}", {}
        
        # Test connection warming
        await pool.warm_connections(2)
        warmed_metrics = pool.get_metrics()
        
        if warmed_metrics['pool_size'] < 1:
            return False, "Connection warming failed", {"metrics": warmed_metrics}
        
        return True, "Connection pooling validated", {
            "initial_metrics": metrics,
            "warmed_metrics": warmed_metrics,
            "warming_successful": True
        }
        
    except Exception as e:
        return False, f"Connection pooling validation failed: {e}", {"exception": str(e)}


async def validate_batch_processing():
    """Validate batch processing functionality"""
    try:
        from app.utils.batch_processor import BatchProcessor, OperationType, BatchRequest
        
        processor = BatchProcessor(max_batch_size=5, max_wait_time_ms=100.0)
        
        # Test batch request creation
        request = BatchRequest(
            operation_type=OperationType.ADD_MEMORY,
            parameters={"text": "test memory"},
            request_id="test_req_1",
            user_id="test_user",
            client_name="test_client"
        )
        
        # Test smart batching
        optimal_size = processor._get_optimal_batch_size(OperationType.SEARCH_MEMORY)
        if optimal_size != 5:  # Expected size for search operations
            return False, f"Smart batching not working: expected 5, got {optimal_size}", {}
        
        # Test statistics
        stats = processor.get_stats()
        required_stats = ['max_batch_size', 'max_wait_time_ms', 'total_requests', 'total_batches']
        missing_stats = [s for s in required_stats if s not in stats]
        
        if missing_stats:
            return False, f"Batch processor missing stats: {missing_stats}", {}
        
        await processor.shutdown()
        
        return True, "Batch processing validated", {
            "smart_batching": True,
            "optimal_search_size": optimal_size,
            "stats_available": list(stats.keys())
        }
        
    except Exception as e:
        return False, f"Batch processing validation failed: {e}", {"exception": str(e)}


async def validate_async_initialization():
    """Validate async initialization system"""
    try:
        from app.utils.mcp_initialization import (
            MCPInitializationManager, setup_mcp_components, 
            initialize_mcp_optimizations
        )
        
        # Test component registration
        manager = MCPInitializationManager()
        
        def test_initializer():
            return True
        
        manager.register_component("test_component", test_initializer)
        
        # Test initialization
        success = await manager.initialize_all(timeout=5.0)
        
        if not success:
            return False, "Async initialization failed", {}
        
        status = manager.get_status()
        
        if not status.get("initialization_complete"):
            return False, "Initialization not marked complete", {"status": status}
        
        await manager.shutdown()
        
        return True, "Async initialization validated", {
            "initialization_successful": success,
            "components_initialized": len(status.get("components", {}))
        }
        
    except Exception as e:
        return False, f"Async initialization validation failed: {e}", {"exception": str(e)}


def validate_memory_factory():
    """Validate memory client factory"""
    try:
        from app.utils.memory_factory import MemoryClientFactory, MockMemoryClient
        
        # Test mock mode
        MemoryClientFactory.configure(mock_mode=True)
        client = MemoryClientFactory.create_client()
        
        if not isinstance(client, MockMemoryClient):
            return False, "Mock mode not working correctly", {}
        
        # Test mock client functionality
        result = client.add("test memory", "test_user")
        
        if not isinstance(result, dict) or 'results' not in result:
            return False, "Mock client add method not working", {"result": result}
        
        # Test search
        search_result = client.search("test", "test_user")
        
        if not isinstance(search_result, dict):
            return False, "Mock client search method not working", {"result": search_result}
        
        MemoryClientFactory.reset()
        
        return True, "Memory factory validated", {
            "mock_mode_working": True,
            "mock_client_functional": True
        }
        
    except Exception as e:
        return False, f"Memory factory validation failed: {e}", {"exception": str(e)}


def validate_performance_targets():
    """Validate performance targets are correctly configured"""
    try:
        from app.utils.performance_monitor import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # Check targets
        thresholds = monitor._thresholds
        
        targets_check = {
            "sub_50ms_target": thresholds.get('response_time_ms') == 50.0,
            "error_rate_target": thresholds.get('error_rate') <= 0.01,
            "throughput_target": thresholds.get('throughput_ops_per_sec') >= 100.0
        }
        
        failed_targets = [name for name, passed in targets_check.items() if not passed]
        
        if failed_targets:
            return False, f"Performance targets not configured correctly: {failed_targets}", {
                "thresholds": thresholds,
                "failed_targets": failed_targets
            }
        
        return True, "Performance targets validated", {
            "targets_met": targets_check,
            "thresholds": thresholds
        }
        
    except Exception as e:
        return False, f"Performance targets validation failed: {e}", {"exception": str(e)}


async def validate_integration():
    """Validate component integration"""
    try:
        # Test that individual components can be imported without errors
        from app.utils.performance_monitor import get_performance_monitor
        from app.utils.connection_pool import get_connection_pool
        from app.utils.batch_processor import get_batch_processor
        from app.utils.memory_factory import get_memory_client_safe
        
        # Check that component factories work
        performance_monitor = get_performance_monitor()
        connection_pool = get_connection_pool()
        batch_processor = get_batch_processor()
        memory_client = get_memory_client_safe()
        
        # Check that components are initialized
        if performance_monitor is None:
            return False, "Performance monitor not initialized", {}
        
        if connection_pool is None:
            return False, "Connection pool not initialized", {}
        
        if batch_processor is None:
            return False, "Batch processor not initialized", {}
        
        if memory_client is None:
            return False, "Memory client not initialized", {}
        
        # Try to import MCP server (may fail in test environment)
        mcp_server_available = False
        try:
            from app.mcp_server import add_memories, search_memory
            
            # Check that functions have decorators
            if hasattr(add_memories, '__wrapped__') and hasattr(search_memory, '__wrapped__'):
                mcp_server_available = True
        except ImportError:
            # MCP server may not be available in test environment
            pass
        
        return True, "Component integration validated", {
            "components_initialized": ["performance_monitor", "connection_pool", "batch_processor", "memory_client"],
            "mcp_server_available": mcp_server_available
        }
        
    except Exception as e:
        return False, f"Integration validation failed: {e}", {"exception": str(e)}


def validate_docker_readiness():
    """Validate Docker deployment readiness"""
    try:
        docker_files = [
            "Dockerfile",
            "requirements.txt"
        ]
        
        existing_files = []
        missing_files = []
        
        for file_path in docker_files:
            if os.path.exists(file_path):
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)
        
        # Check if basic Docker files exist
        if not os.path.exists("Dockerfile"):
            return False, "Dockerfile not found", {"missing": missing_files}
        
        return True, "Docker deployment files validated", {
            "existing_files": existing_files,
            "missing_files": missing_files
        }
        
    except Exception as e:
        return False, f"Docker readiness validation failed: {e}", {"exception": str(e)}


def validate_production_configuration():
    """Validate production configuration"""
    try:
        # Check for production configuration options
        config_checks = {
            "env_file": os.path.exists(".env"),
            "config_json": os.path.exists("config.json"),
            "app_directory": os.path.exists("app/"),
            "tests_directory": os.path.exists("tests/")
        }
        
        missing_configs = [name for name, exists in config_checks.items() if not exists]
        
        if len(missing_configs) > 2:  # Allow some flexibility
            return False, f"Multiple production configuration items missing: {missing_configs}", {
                "config_checks": config_checks
            }
        
        return True, "Production configuration validated", {
            "config_checks": config_checks,
            "missing_configs": missing_configs
        }
        
    except Exception as e:
        return False, f"Production configuration validation failed: {e}", {"exception": str(e)}


async def main():
    """Main validation function"""
    print("🚀 Starting Production Deployment Validation for MCP Server")
    print("=" * 80)
    
    validator = ProductionValidator()
    
    # Critical validations
    await validator.validate_component(
        "Python Environment", ValidationLevel.CRITICAL, validate_python_environment
    )
    
    await validator.validate_component(
        "File Structure", ValidationLevel.CRITICAL, validate_file_structure
    )
    
    await validator.validate_component(
        "Memory Factory", ValidationLevel.CRITICAL, validate_memory_factory
    )
    
    # High priority validations
    await validator.validate_component(
        "Performance Monitoring", ValidationLevel.HIGH, validate_performance_monitoring
    )
    
    await validator.validate_component(
        "Connection Pooling", ValidationLevel.HIGH, validate_connection_pooling
    )
    
    await validator.validate_component(
        "Batch Processing", ValidationLevel.HIGH, validate_batch_processing
    )
    
    await validator.validate_component(
        "Async Initialization", ValidationLevel.HIGH, validate_async_initialization
    )
    
    await validator.validate_component(
        "Component Integration", ValidationLevel.HIGH, validate_integration
    )
    
    # Medium priority validations
    await validator.validate_component(
        "Performance Targets", ValidationLevel.MEDIUM, validate_performance_targets
    )
    
    await validator.validate_component(
        "Docker Readiness", ValidationLevel.MEDIUM, validate_docker_readiness
    )
    
    # Low priority validations  
    await validator.validate_component(
        "Production Configuration", ValidationLevel.LOW, validate_production_configuration
    )
    
    # Print results
    print("\n" + "=" * 80)
    print("📊 VALIDATION RESULTS")
    print("=" * 80)
    
    for result in validator.results:
        status_icon = "✅" if result.passed else "❌"
        level_indicator = {
            ValidationLevel.CRITICAL: "🔴",
            ValidationLevel.HIGH: "🟠", 
            ValidationLevel.MEDIUM: "🟡",
            ValidationLevel.LOW: "🟢"
        }[result.level]
        
        print(f"{status_icon} {level_indicator} {result.name}: {result.message}")
        if not result.passed and result.level in [ValidationLevel.CRITICAL, ValidationLevel.HIGH]:
            print(f"   Details: {result.details}")
    
    # Print summary
    summary = validator.get_summary()
    print("\n" + "=" * 80)
    print("🎯 DEPLOYMENT READINESS SUMMARY")
    print("=" * 80)
    
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Validation Duration: {summary['total_duration_ms']:.2f}ms")
    
    print("\nBy Priority Level:")
    for level in ValidationLevel:
        level_data = summary['by_level'][level.value]
        print(f"  {level.value.upper()}: {level_data['passed']}/{level_data['passed'] + level_data['failed']} passed")
    
    # Overall recommendation
    print(f"\n🎭 OVERALL STATUS: {summary['overall_status'].upper()}")
    
    if summary['overall_status'] == 'ready':
        print("🎉 PRODUCTION READY - All critical and high priority checks passed!")
        print("💡 The MCP server performance optimizations are ready for deployment.")
        return 0
    elif summary['overall_status'] == 'warning':
        print("⚠️  DEPLOY WITH CAUTION - Some low/medium priority issues detected")
        print("💡 Consider addressing remaining issues before production deployment.")
        return 1
    elif summary['overall_status'] == 'high_risk':
        print("🚨 HIGH RISK - Critical high priority issues detected")
        print(f"❌ High priority failures: {summary['high_failures']}")
        print("🛠️  Address high priority issues before deployment.")
        return 2
    else:  # critical_failure
        print("🔥 CRITICAL FAILURE - Deployment not recommended")
        print(f"❌ Critical failures: {summary['critical_failures']}")
        print("🛠️  Address critical issues before deployment.")
        return 3


if __name__ == "__main__":
    # Ensure we're in an async context
    exit_code = asyncio.run(main())
    sys.exit(exit_code)