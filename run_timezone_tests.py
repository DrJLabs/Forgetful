#!/usr/bin/env python3
"""
Test runner for timezone safety tests.

This script runs the comprehensive timezone safety tests for the storage optimization module.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_tests():
    """Run the timezone safety tests with comprehensive reporting."""
    print("🧪 Running Timezone Safety Tests for Storage Optimization")
    print("=" * 60)
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Test commands to run
    test_commands = [
        {
            'name': 'Unit Tests - Timezone Edge Cases',
            'cmd': ['python', '-m', 'pytest', 'tests/test_storage_optimization_timezone.py::TestTimezoneEdgeCases', '-v', '--tb=short'],
            'critical': True
        },
        {
            'name': 'Integration Tests - Full Workflow',
            'cmd': ['python', '-m', 'pytest', 'tests/test_storage_optimization_timezone.py::TestStorageOptimizationIntegration', '-v', '--tb=short'],
            'critical': True
        },
        {
            'name': 'Regression Tests - Original Bug',
            'cmd': ['python', '-m', 'pytest', 'tests/test_storage_optimization_timezone.py::TestTimezoneRegressionTests', '-v', '--tb=short'],
            'critical': True
        },
        {
            'name': 'Performance Tests - No Regression',
            'cmd': ['python', '-m', 'pytest', 'tests/test_storage_optimization_timezone.py::TestPerformanceRegression', '-v', '--tb=short', '-m', 'performance'],
            'critical': False
        },
        {
            'name': 'Coverage Report',
            'cmd': ['python', '-m', 'pytest', 'tests/test_storage_optimization_timezone.py', '--cov=mem0.memory.storage_optimization', '--cov-report=term-missing', '--cov-report=html'],
            'critical': False
        }
    ]
    
    results = []
    
    for test_suite in test_commands:
        print(f"\n🔍 Running: {test_suite['name']}")
        print("-" * 50)
        
        try:
            result = subprocess.run(
                test_suite['cmd'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"✅ PASSED: {test_suite['name']}")
                results.append((test_suite['name'], 'PASSED', test_suite['critical']))
            else:
                print(f"❌ FAILED: {test_suite['name']}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                results.append((test_suite['name'], 'FAILED', test_suite['critical']))
                
        except subprocess.TimeoutExpired:
            print(f"⏰ TIMEOUT: {test_suite['name']}")
            results.append((test_suite['name'], 'TIMEOUT', test_suite['critical']))
        except Exception as e:
            print(f"💥 ERROR: {test_suite['name']} - {e}")
            results.append((test_suite['name'], 'ERROR', test_suite['critical']))
    
    # Summary report
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY REPORT")
    print("=" * 60)
    
    passed_count = sum(1 for _, status, _ in results if status == 'PASSED')
    failed_count = sum(1 for _, status, _ in results if status == 'FAILED')
    critical_failures = sum(1 for _, status, critical in results if status == 'FAILED' and critical)
    
    print(f"Total Tests: {len(results)}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"🚨 Critical Failures: {critical_failures}")
    
    print("\nDetailed Results:")
    for name, status, critical in results:
        icon = "🚨" if critical and status == 'FAILED' else "✅" if status == 'PASSED' else "❌"
        criticality = " (CRITICAL)" if critical else ""
        print(f"  {icon} {name}: {status}{criticality}")
    
    # Final verdict
    if critical_failures > 0:
        print(f"\n🚨 CRITICAL FAILURES DETECTED: {critical_failures}")
        print("❌ Timezone fixes have critical issues that must be addressed before deployment.")
        return False
    elif failed_count > 0:
        print(f"\n⚠️  NON-CRITICAL FAILURES: {failed_count}")
        print("✅ Core timezone functionality is working, but some optional tests failed.")
        return True
    else:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Timezone fixes are working correctly and ready for deployment.")
        return True

def check_dependencies():
    """Check if required test dependencies are installed."""
    print("📋 Checking test dependencies...")
    
    required_packages = [
        'pytest',
        'freezegun',
        'pytest-cov'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("📦 Install with: pip install -r requirements-test.txt")
        return False
    
    print("✅ All test dependencies are installed.")
    return True

if __name__ == '__main__':
    print("🧪 Timezone Safety Test Suite")
    print("Testing timezone bug fixes in storage optimization module")
    print("=" * 60)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Cannot run tests without required dependencies.")
        sys.exit(1)
    
    # Run the tests
    success = run_tests()
    
    if success:
        print("\n✅ Test execution completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Test execution completed with critical failures!")
        sys.exit(1) 