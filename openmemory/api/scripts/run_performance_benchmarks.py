#!/usr/bin/env python3
"""
Performance Benchmark Runner
Phase 2 - Action Item 4: Benchmark Infrastructure

This script runs performance benchmarks and generates reports for CI/CD integration.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class BenchmarkRunner:
    """Run and manage performance benchmarks."""

    def __init__(self, output_dir: str = "benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")

    def run_benchmark_suite(
        self, groups: list[str] = None, compare_baseline: str = None
    ) -> dict[str, Any]:
        """Run the complete benchmark suite."""
        print("🚀 Running Performance Benchmark Suite")
        print(f"Timestamp: {self.timestamp}")
        print(f"Output directory: {self.output_dir}")
        print()

        # Build command
        cmd = [
            "python",
            "-m",
            "pytest",
            "tests/benchmarks/",
            "--benchmark-only",
            "--benchmark-json="
            + str(self.output_dir / f"benchmark_{self.timestamp}.json"),
            "--benchmark-verbose",
            "--disable-warnings",
            "--no-cov",
            "-v",
        ]

        # Add group filter if specified
        if groups:
            group_filter = " or ".join([f"group={group}" for group in groups])
            cmd.extend(["-m", f"benchmark and ({group_filter})"])

        # Add baseline comparison if specified
        if compare_baseline:
            cmd.extend(
                [
                    "--benchmark-compare=" + compare_baseline,
                    "--benchmark-compare-fail=mean:20%",  # Fail if >20% regression
                ]
            )

        print(f"Executing: {' '.join(cmd)}")
        print()

        # Run benchmarks
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "command": " ".join(cmd),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Benchmark execution timed out after 10 minutes",
                "command": " ".join(cmd),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "command": " ".join(cmd)}

    def parse_benchmark_results(self, results_file: str) -> dict[str, Any]:
        """Parse benchmark results from JSON file."""
        try:
            with open(results_file) as f:
                data = json.load(f)

            parsed = {
                "metadata": {
                    "timestamp": self.timestamp,
                    "python_version": data.get("machine_info", {}).get(
                        "python_version", "unknown"
                    ),
                    "platform": data.get("machine_info", {}).get("platform", "unknown"),
                    "cpu_count": data.get("machine_info", {})
                    .get("cpu", {})
                    .get("count", "unknown"),
                },
                "benchmarks": {},
                "summary": {
                    "total_benchmarks": len(data.get("benchmarks", [])),
                    "groups": set(),
                },
            }

            # Parse individual benchmarks
            for benchmark in data.get("benchmarks", []):
                name = benchmark["name"]
                group = benchmark.get("group", "ungrouped")
                parsed["summary"]["groups"].add(group)

                parsed["benchmarks"][name] = {
                    "group": group,
                    "mean": benchmark["stats"]["mean"],
                    "min": benchmark["stats"]["min"],
                    "max": benchmark["stats"]["max"],
                    "stddev": benchmark["stats"]["stddev"],
                    "rounds": benchmark["stats"]["rounds"],
                    "iqr": benchmark["stats"]["iqr"],
                    "params": benchmark.get("params", {}),
                }

            parsed["summary"]["groups"] = list(parsed["summary"]["groups"])
            return parsed

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            return {"error": f"Failed to parse benchmark results: {e}"}

    def generate_performance_report(self, parsed_results: dict[str, Any]) -> str:
        """Generate human-readable performance report."""
        if "error" in parsed_results:
            return f"# Performance Report - ERROR\n\n{parsed_results['error']}"

        report = []
        report.append("# Performance Benchmark Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Timestamp: {parsed_results['metadata']['timestamp']}")
        report.append("")

        # Metadata
        metadata = parsed_results["metadata"]
        report.append("## Environment")
        report.append(f"- **Python**: {metadata['python_version']}")
        report.append(f"- **Platform**: {metadata['platform']}")
        report.append(f"- **CPU Cores**: {metadata['cpu_count']}")
        report.append("")

        # Summary
        summary = parsed_results["summary"]
        report.append("## Summary")
        report.append(f"- **Total Benchmarks**: {summary['total_benchmarks']}")
        report.append(f"- **Test Groups**: {', '.join(summary['groups'])}")
        report.append("")

        # Results by group
        benchmarks_by_group = {}
        for name, data in parsed_results["benchmarks"].items():
            group = data["group"]
            if group not in benchmarks_by_group:
                benchmarks_by_group[group] = []
            benchmarks_by_group[group].append((name, data))

        for group, benchmarks in benchmarks_by_group.items():
            report.append(f"## {group.title()} Benchmarks")
            report.append("")
            report.append(
                "| Benchmark | Mean (s) | Min (s) | Max (s) | StdDev | Rounds |"
            )
            report.append(
                "|-----------|----------|---------|---------|--------|--------|"
            )

            for name, data in sorted(benchmarks, key=lambda x: x[1]["mean"]):
                clean_name = name.replace("test_", "").replace("_benchmark", "")
                report.append(
                    f"| {clean_name} | {data['mean']:.4f} | {data['min']:.4f} | {data['max']:.4f} | {data['stddev']:.4f} | {data['rounds']} |"
                )

            report.append("")

        # Performance insights
        report.append("## Performance Insights")
        report.append("")

        # Find fastest and slowest benchmarks
        all_benchmarks = list(parsed_results["benchmarks"].items())
        if all_benchmarks:
            fastest = min(all_benchmarks, key=lambda x: x[1]["mean"])
            slowest = max(all_benchmarks, key=lambda x: x[1]["mean"])

            report.append(
                f"- **Fastest operation**: {fastest[0]} ({fastest[1]['mean']:.4f}s)"
            )
            report.append(
                f"- **Slowest operation**: {slowest[0]} ({slowest[1]['mean']:.4f}s)"
            )

            if slowest[1]["mean"] > 0:
                ratio = slowest[1]["mean"] / fastest[1]["mean"]
                report.append(
                    f"- **Performance range**: {ratio:.1f}x difference between fastest and slowest"
                )

        report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")

        slow_benchmarks = [
            (name, data)
            for name, data in parsed_results["benchmarks"].items()
            if data["mean"] > 1.0  # Benchmarks slower than 1 second
        ]

        if slow_benchmarks:
            report.append("### Performance Concerns")
            for name, data in slow_benchmarks:
                report.append(
                    f"- **{name}**: {data['mean']:.4f}s (consider optimization)"
                )
        else:
            report.append("✅ All benchmarks complete in reasonable time (<1s)")

        report.append("")
        report.append("**Generated by**: Performance Benchmark Runner v1.0")
        report.append(f"**Results file**: benchmark_{self.timestamp}.json")

        return "\n".join(report)

    def save_report(self, report: str, filename: str = None) -> str:
        """Save performance report to file."""
        if filename is None:
            filename = f"performance_report_{self.timestamp}.md"

        report_path = self.output_dir / filename
        with open(report_path, "w") as f:
            f.write(report)

        return str(report_path)

    def check_performance_regression(
        self, current_results: str, baseline_results: str
    ) -> dict[str, Any]:
        """Compare current results with baseline for regression detection."""
        try:
            current = self.parse_benchmark_results(current_results)
            baseline = self.parse_benchmark_results(baseline_results)

            if "error" in current or "error" in baseline:
                return {"error": "Failed to parse results for comparison"}

            regressions = []
            improvements = []

            for name, current_data in current["benchmarks"].items():
                if name in baseline["benchmarks"]:
                    baseline_mean = baseline["benchmarks"][name]["mean"]
                    current_mean = current_data["mean"]

                    change_percent = (
                        (current_mean - baseline_mean) / baseline_mean
                    ) * 100

                    if change_percent > 20:  # >20% slower is a regression
                        regressions.append(
                            {
                                "benchmark": name,
                                "baseline": baseline_mean,
                                "current": current_mean,
                                "change_percent": change_percent,
                            }
                        )
                    elif change_percent < -10:  # >10% faster is an improvement
                        improvements.append(
                            {
                                "benchmark": name,
                                "baseline": baseline_mean,
                                "current": current_mean,
                                "change_percent": change_percent,
                            }
                        )

            return {
                "regressions": regressions,
                "improvements": improvements,
                "total_benchmarks": len(current["benchmarks"]),
                "status": "regression" if regressions else "good",
            }

        except Exception as e:
            return {"error": f"Failed to compare results: {e}"}


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Performance Benchmark Runner")
    parser.add_argument(
        "--groups", nargs="*", help="Benchmark groups to run (default: all)"
    )
    parser.add_argument(
        "--output-dir",
        default="benchmark_results",
        help="Output directory for results (default: benchmark_results)",
    )
    parser.add_argument(
        "--compare", type=str, help="Baseline results file for regression comparison"
    )
    parser.add_argument(
        "--report-only", type=str, help="Generate report from existing results file"
    )
    parser.add_argument(
        "--check-regression",
        nargs=2,
        metavar=("CURRENT", "BASELINE"),
        help="Check for performance regression between two result files",
    )

    args = parser.parse_args()

    runner = BenchmarkRunner(args.output_dir)

    if args.check_regression:
        current_file, baseline_file = args.check_regression
        regression_results = runner.check_performance_regression(
            current_file, baseline_file
        )

        if "error" in regression_results:
            print(f"❌ Error: {regression_results['error']}")
            sys.exit(1)

        print("🔍 Performance Regression Analysis")
        print(f"Total benchmarks compared: {regression_results['total_benchmarks']}")
        print(f"Status: {regression_results['status']}")
        print()

        if regression_results["regressions"]:
            print("🚨 Performance Regressions Detected:")
            for reg in regression_results["regressions"]:
                print(f"  - {reg['benchmark']}: {reg['change_percent']:+.1f}% slower")
                print(
                    f"    Baseline: {reg['baseline']:.4f}s → Current: {reg['current']:.4f}s"
                )
            sys.exit(1)

        if regression_results["improvements"]:
            print("✅ Performance Improvements:")
            for imp in regression_results["improvements"]:
                print(
                    f"  - {imp['benchmark']}: {abs(imp['change_percent']):.1f}% faster"
                )

        print("✅ No significant performance regressions detected")
        return

    if args.report_only:
        print(f"📊 Generating report from: {args.report_only}")
        parsed_results = runner.parse_benchmark_results(args.report_only)
        report = runner.generate_performance_report(parsed_results)
        report_path = runner.save_report(report)
        print(f"📝 Report saved to: {report_path}")
        print()
        print(report)
        return

    # Run benchmarks
    print("🏃 Running Performance Benchmarks")
    results = runner.run_benchmark_suite(
        groups=args.groups, compare_baseline=args.compare
    )

    if not results["success"]:
        print("❌ Benchmark execution failed!")
        print(f"Return code: {results['returncode']}")
        if "error" in results:
            print(f"Error: {results['error']}")
        else:
            print("STDOUT:", results["stdout"])
            print("STDERR:", results["stderr"])
        sys.exit(1)

    print("✅ Benchmarks completed successfully!")
    print()

    # Generate and save report
    results_file = runner.output_dir / f"benchmark_{runner.timestamp}.json"
    if results_file.exists():
        parsed_results = runner.parse_benchmark_results(str(results_file))
        report = runner.generate_performance_report(parsed_results)
        report_path = runner.save_report(report)

        print(f"📊 Results: {results_file}")
        print(f"📝 Report: {report_path}")
        print()
        print("=== PERFORMANCE REPORT ===")
        print(report)
    else:
        print("⚠️  Warning: Benchmark results file not found")


if __name__ == "__main__":
    main()
