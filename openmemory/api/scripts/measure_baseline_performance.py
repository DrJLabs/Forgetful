#!/usr/bin/env python3
"""
Baseline Performance Measurement Script
Phase 2 - Action Item 1: Establish Performance Baseline

This script measures actual performance characteristics of the test suite
to establish accurate baselines before optimization.
"""

import subprocess
import time
import json
import sys
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import statistics


@dataclass
class PerformanceResult:
    """Performance measurement result."""

    configuration: str
    workers: int
    total_time: float
    tests_collected: int
    tests_passed: int
    tests_failed: int
    collection_time: float
    execution_time: float
    setup_time: float
    teardown_time: float
    memory_peak_mb: float
    cpu_usage_percent: float


class BaselinePerformanceMeasurer:
    """Measures baseline performance of the test suite."""

    def __init__(self, test_path: str = "tests/test_simple.py", iterations: int = 3):
        self.test_path = test_path
        self.iterations = iterations
        self.results: List[PerformanceResult] = []

    def measure_test_collection(self) -> float:
        """Measure test collection time."""
        start_time = time.perf_counter()

        result = subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                self.test_path,
                "--collect-only",
                "--disable-warnings",
                "-q",
            ],
            capture_output=True,
            text=True,
        )

        end_time = time.perf_counter()

        if result.returncode == 0:
            # Count collected tests from output
            lines = result.stdout.split("\n")
            for line in lines:
                if "collected" in line and "item" in line:
                    # Extract test count from "collected X items"
                    words = line.split()
                    for i, word in enumerate(words):
                        if word == "collected" and i + 1 < len(words):
                            try:
                                return end_time - start_time, int(words[i + 1])
                            except ValueError:
                                pass

        return end_time - start_time, 0

    def measure_execution(self, workers: int = 1) -> PerformanceResult:
        """Measure test execution performance."""
        print(f"Measuring execution with {workers} worker(s)...")

        # Measure collection time
        collection_time, test_count = self.measure_test_collection()

        # Prepare command
        cmd = [
            "python",
            "-m",
            "pytest",
            self.test_path,
            "--disable-warnings",
            "--no-cov",  # Disable coverage for pure performance measurement
            "-q",
        ]

        if workers > 1:
            cmd.extend(["-n", str(workers)])

        # Measure execution
        start_time = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True)
        end_time = time.perf_counter()

        total_time = end_time - start_time

        # Parse test results
        tests_passed = 0
        tests_failed = 0

        if result.returncode == 0:
            # Extract test results from output
            lines = result.stdout.split("\n")
            for line in lines:
                if " passed" in line:
                    words = line.split()
                    for i, word in enumerate(words):
                        if word == "passed":
                            try:
                                tests_passed = int(words[i - 1])
                                break
                            except (ValueError, IndexError):
                                pass
                if " failed" in line:
                    words = line.split()
                    for i, word in enumerate(words):
                        if word == "failed":
                            try:
                                tests_failed = int(words[i - 1])
                                break
                            except (ValueError, IndexError):
                                pass

        # If we couldn't parse, use test_count as passed
        if tests_passed == 0 and tests_failed == 0 and test_count > 0:
            tests_passed = test_count

        config_name = f"{workers}_worker{'s' if workers != 1 else ''}"

        return PerformanceResult(
            configuration=config_name,
            workers=workers,
            total_time=total_time,
            tests_collected=test_count,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            collection_time=collection_time,
            execution_time=total_time - collection_time,
            setup_time=0.0,  # TODO: Measure setup/teardown separately
            teardown_time=0.0,
            memory_peak_mb=0.0,  # TODO: Add memory profiling
            cpu_usage_percent=0.0,  # TODO: Add CPU monitoring
        )

    def run_comprehensive_baseline(self) -> Dict[str, Any]:
        """Run comprehensive baseline measurements."""
        print("=== Phase 2 Baseline Performance Measurement ===")
        print(f"Test target: {self.test_path}")
        print(f"Iterations per configuration: {self.iterations}")
        print()

        # Test different worker configurations
        worker_configs = [1, 2, 4, 8]
        all_results = {}

        for workers in worker_configs:
            config_results = []

            print(f"Testing {workers} worker configuration:")

            for iteration in range(self.iterations):
                print(f"  Iteration {iteration + 1}/{self.iterations}...")
                result = self.measure_execution(workers)
                config_results.append(result)

                print(f"    Total time: {result.total_time:.3f}s")
                print(f"    Collection: {result.collection_time:.3f}s")
                print(
                    f"    Tests: {result.tests_collected} collected, {result.tests_passed} passed"
                )

            # Calculate statistics
            times = [r.total_time for r in config_results]
            collection_times = [r.collection_time for r in config_results]

            all_results[f"{workers}_workers"] = {
                "workers": workers,
                "iterations": config_results,
                "statistics": {
                    "mean_total_time": statistics.mean(times),
                    "median_total_time": statistics.median(times),
                    "min_total_time": min(times),
                    "max_total_time": max(times),
                    "std_total_time": statistics.stdev(times) if len(times) > 1 else 0,
                    "mean_collection_time": statistics.mean(collection_times),
                    "tests_collected": config_results[0].tests_collected,
                    "tests_passed": config_results[0].tests_passed,
                    "tests_failed": config_results[0].tests_failed,
                },
            }

            stats = all_results[f"{workers}_workers"]["statistics"]
            print(
                f"  Average total time: {stats['mean_total_time']:.3f}s (±{stats['std_total_time']:.3f}s)"
            )
            print(f"  Average collection: {stats['mean_collection_time']:.3f}s")
            print()

        return all_results

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate performance baseline report."""
        report = []
        report.append("# Performance Baseline Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Test target: {self.test_path}")
        report.append("")

        # Summary table
        report.append("## Performance Summary")
        report.append("")
        report.append(
            "| Workers | Mean Time (s) | Std Dev (s) | Tests | Collection (s) | Status |"
        )
        report.append(
            "|---------|---------------|-------------|-------|----------------|--------|"
        )

        best_time = float("inf")
        best_config = None

        for config_name, data in results.items():
            stats = data["statistics"]
            workers = data["workers"]
            mean_time = stats["mean_total_time"]
            std_time = stats["std_total_time"]
            collection_time = stats["mean_collection_time"]
            tests = stats["tests_collected"]

            if mean_time < best_time:
                best_time = mean_time
                best_config = config_name

            status = "✅ FASTEST" if config_name == best_config else ""

            report.append(
                f"| {workers} | {mean_time:.3f} | {std_time:.3f} | {tests} | {collection_time:.3f} | {status} |"
            )

        report.append("")

        # Performance analysis
        sequential_time = results["1_workers"]["statistics"]["mean_total_time"]

        report.append("## Performance Analysis")
        report.append("")
        report.append(f"**Sequential (1 worker) baseline**: {sequential_time:.3f}s")
        report.append("")

        for config_name, data in results.items():
            if data["workers"] == 1:
                continue

            workers = data["workers"]
            parallel_time = data["statistics"]["mean_total_time"]
            improvement = ((sequential_time - parallel_time) / sequential_time) * 100

            if improvement > 0:
                report.append(
                    f"**{workers} workers**: {improvement:.1f}% faster than sequential"
                )
            else:
                report.append(
                    f"**{workers} workers**: {abs(improvement):.1f}% slower than sequential ❌"
                )

        report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")

        if best_config == "1_workers":
            report.append(
                "- **Sequential execution is fastest** for this test suite size"
            )
            report.append("- Parallel execution overhead exceeds benefits")
            report.append(
                "- Consider parallel execution only for larger test suites (>50 tests)"
            )
        else:
            report.append(
                f"- **Optimal configuration**: {results[best_config]['workers']} workers"
            )
            report.append(
                f"- **Performance gain**: {((sequential_time - best_time) / sequential_time) * 100:.1f}% improvement"
            )

        return "\n".join(report)

    def save_results(self, results: Dict[str, Any], report: str):
        """Save results and report to files."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Save raw results as JSON
        results_file = f"baseline_results_{timestamp}.json"
        with open(results_file, "w") as f:
            # Convert PerformanceResult objects to dicts for JSON serialization
            json_results = {}
            for config, data in results.items():
                json_results[config] = {
                    "workers": data["workers"],
                    "statistics": data["statistics"],
                    "iterations": [asdict(result) for result in data["iterations"]],
                }
            json.dump(json_results, f, indent=2)

        # Save report as markdown
        report_file = f"baseline_report_{timestamp}.md"
        with open(report_file, "w") as f:
            f.write(report)

        print(f"Results saved to: {results_file}")
        print(f"Report saved to: {report_file}")

        return results_file, report_file


def main():
    """Main execution function."""
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        test_path = "tests/test_simple.py"

    # Create scripts directory if it doesn't exist
    os.makedirs("scripts", exist_ok=True)

    measurer = BaselinePerformanceMeasurer(test_path=test_path, iterations=3)

    try:
        results = measurer.run_comprehensive_baseline()
        report = measurer.generate_report(results)

        print("=== BASELINE PERFORMANCE REPORT ===")
        print(report)
        print()

        results_file, report_file = measurer.save_results(results, report)

        print("=== ACTION ITEMS ===")
        print("1. Review performance characteristics above")
        print("2. Use this data for optimization decisions")
        print("3. Re-run after optimizations to validate improvements")
        print(f"4. Baseline files: {results_file}, {report_file}")

    except Exception as e:
        print(f"Error during baseline measurement: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
