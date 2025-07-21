#!/usr/bin/env python3
"""
Database Performance Benchmarking Script
Phase 2 - Action Item 3: Database Performance Optimization

This script measures database setup performance to validate optimization claims.
"""

import os
import statistics
import sys
import time
from contextlib import contextmanager
from typing import Any

# Set up test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-testing"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import after setting environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import Base
from app.models import User


class DatabasePerformanceBenchmark:
    """Benchmark database setup performance."""

    def __init__(self, iterations: int = 10):
        self.iterations = iterations
        self.results = {}

    @contextmanager
    def timer(self, description: str):
        """Context manager for timing operations."""
        start = time.perf_counter()
        yield
        elapsed = time.perf_counter() - start
        print(f"  {description}: {elapsed:.4f}s")
        return elapsed

    def benchmark_function_scoped_fixtures(self) -> dict[str, float]:
        """Benchmark traditional function-scoped database fixtures."""
        print("🔄 Benchmarking function-scoped database fixtures...")

        setup_times = []
        teardown_times = []
        total_times = []

        for i in range(self.iterations):
            print(f"  Iteration {i + 1}/{self.iterations}")

            # Measure setup time
            start_total = time.perf_counter()
            start_setup = time.perf_counter()

            # Create new engine every time (function-scoped behavior)
            engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,
            )

            # Create schema
            Base.metadata.create_all(bind=engine)

            # Create session
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()

            setup_time = time.perf_counter() - start_setup
            setup_times.append(setup_time)

            # Simulate some database operations
            import uuid

            user = User(
                id=str(uuid.uuid4()),
                user_id="test-user",
                name="Test User",
                email="test@example.com",
                metadata={},
            )
            session.add(user)
            session.commit()

            # Measure teardown time
            start_teardown = time.perf_counter()

            session.close()
            Base.metadata.drop_all(bind=engine)
            engine.dispose()

            teardown_time = time.perf_counter() - start_teardown
            teardown_times.append(teardown_time)

            total_time = time.perf_counter() - start_total
            total_times.append(total_time)

        return {
            "setup_mean": statistics.mean(setup_times),
            "setup_std": statistics.stdev(setup_times) if len(setup_times) > 1 else 0,
            "teardown_mean": statistics.mean(teardown_times),
            "teardown_std": statistics.stdev(teardown_times)
            if len(teardown_times) > 1
            else 0,
            "total_mean": statistics.mean(total_times),
            "total_std": statistics.stdev(total_times) if len(total_times) > 1 else 0,
            "raw_times": total_times,
        }

    def benchmark_session_scoped_fixtures(self) -> dict[str, float]:
        """Benchmark optimized session-scoped database fixtures."""
        print("🚀 Benchmarking session-scoped database fixtures...")

        # One-time session setup
        print("  Setting up session-scoped engine...")
        session_start = time.perf_counter()

        # Create engine once (session-scoped behavior)
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        # Create schema once
        Base.metadata.create_all(bind=engine)

        session_setup_time = time.perf_counter() - session_start
        print(f"  Session setup: {session_setup_time:.4f}s")

        # Benchmark per-test operations
        test_times = []

        for i in range(self.iterations):
            print(f"  Iteration {i + 1}/{self.iterations}")

            start_test = time.perf_counter()

            # Create connection and transaction (function-scoped with session-scoped engine)
            connection = engine.connect()
            transaction = connection.begin()

            SessionLocal = sessionmaker(bind=connection)
            session = SessionLocal()

            # Simulate database operations
            import uuid

            user = User(
                id=str(uuid.uuid4()),
                user_id=f"test-user-{i}",
                name=f"Test User {i}",
                email=f"test{i}@example.com",
                metadata={},
            )
            session.add(user)
            session.commit()

            # Cleanup (transaction rollback)
            transaction.rollback()
            session.close()
            connection.close()

            test_time = time.perf_counter() - start_test
            test_times.append(test_time)

        # One-time teardown
        teardown_start = time.perf_counter()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        session_teardown_time = time.perf_counter() - teardown_start

        print(f"  Session teardown: {session_teardown_time:.4f}s")

        return {
            "session_setup": session_setup_time,
            "session_teardown": session_teardown_time,
            "test_mean": statistics.mean(test_times),
            "test_std": statistics.stdev(test_times) if len(test_times) > 1 else 0,
            "total_mean": (session_setup_time + sum(test_times) + session_teardown_time)
            / self.iterations,
            "raw_times": test_times,
        }

    def benchmark_database_operations(self) -> dict[str, float]:
        """Benchmark common database operations for context."""
        print("📊 Benchmarking database operations...")

        # Setup optimized database
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)

        operation_times = {"insert": [], "select": [], "update": [], "delete": []}

        for i in range(self.iterations):
            session = SessionLocal()

            # Insert operation
            start = time.perf_counter()
            import uuid

            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                user_id=f"bench-user-{i}",
                name=f"Benchmark User {i}",
                email=f"bench{i}@example.com",
                metadata={"test": True},
            )
            session.add(user)
            session.commit()
            operation_times["insert"].append(time.perf_counter() - start)

            # Select operation
            start = time.perf_counter()
            found_user = session.query(User).filter(User.id == user_id).first()
            operation_times["select"].append(time.perf_counter() - start)

            # Update operation
            start = time.perf_counter()
            found_user.name = f"Updated User {i}"
            session.commit()
            operation_times["update"].append(time.perf_counter() - start)

            # Delete operation
            start = time.perf_counter()
            session.delete(found_user)
            session.commit()
            operation_times["delete"].append(time.perf_counter() - start)

            session.close()

        # Cleanup
        engine.dispose()

        return {
            op: {
                "mean": statistics.mean(times),
                "std": statistics.stdev(times) if len(times) > 1 else 0,
            }
            for op, times in operation_times.items()
        }

    def run_comprehensive_benchmark(self) -> dict[str, Any]:
        """Run comprehensive database performance benchmark."""
        print("=== Database Performance Benchmark ===")
        print(f"Iterations: {self.iterations}")
        print()

        # Benchmark function-scoped fixtures
        function_results = self.benchmark_function_scoped_fixtures()
        print()

        # Benchmark session-scoped fixtures
        session_results = self.benchmark_session_scoped_fixtures()
        print()

        # Benchmark operations
        operations_results = self.benchmark_database_operations()
        print()

        return {
            "function_scoped": function_results,
            "session_scoped": session_results,
            "operations": operations_results,
        }

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate performance analysis report."""
        report = []
        report.append("# Database Performance Analysis Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Iterations: {self.iterations}")
        report.append("")

        function_data = results["function_scoped"]
        session_data = results["session_scoped"]

        # Performance comparison
        report.append("## Setup Performance Comparison")
        report.append("")
        report.append(
            "| Approach | Setup Time (s) | Total Time per Test (s) | Performance |"
        )
        report.append(
            "|----------|----------------|-------------------------|-------------|"
        )

        function_total = function_data["total_mean"]
        session_total = session_data["total_mean"]

        if function_total > session_total:
            improvement = ((function_total - session_total) / function_total) * 100
            status = f"✅ {improvement:.1f}% faster"
        else:
            degradation = ((session_total - function_total) / function_total) * 100
            status = f"❌ {degradation:.1f}% slower"

        report.append(
            f"| Function-scoped | {function_data['setup_mean']:.4f} | {function_total:.4f} | Baseline |"
        )
        report.append(
            f"| Session-scoped | {session_data['session_setup']:.4f} | {session_total:.4f} | {status} |"
        )
        report.append("")

        # Detailed analysis
        report.append("## Detailed Analysis")
        report.append("")
        report.append("### Function-Scoped Fixtures")
        report.append(
            f"- **Setup time**: {function_data['setup_mean']:.4f}s (±{function_data['setup_std']:.4f}s)"
        )
        report.append(
            f"- **Teardown time**: {function_data['teardown_mean']:.4f}s (±{function_data['teardown_std']:.4f}s)"
        )
        report.append(
            f"- **Total per test**: {function_data['total_mean']:.4f}s (±{function_data['total_std']:.4f}s)"
        )
        report.append("")

        report.append("### Session-Scoped Fixtures")
        report.append(
            f"- **Session setup**: {session_data['session_setup']:.4f}s (one-time)"
        )
        report.append(
            f"- **Per-test time**: {session_data['test_mean']:.4f}s (±{session_data['test_std']:.4f}s)"
        )
        report.append(
            f"- **Session teardown**: {session_data['session_teardown']:.4f}s (one-time)"
        )
        report.append(f"- **Amortized per test**: {session_data['total_mean']:.4f}s")
        report.append("")

        # Database operations context
        operations = results["operations"]
        report.append("### Database Operations (Context)")
        report.append("")
        for op, data in operations.items():
            report.append(
                f"- **{op.capitalize()}**: {data['mean']:.4f}s (±{data['std']:.4f}s)"
            )
        report.append("")

        # Recommendations
        report.append("## Recommendations")
        report.append("")

        if improvement > 0:
            report.append(
                f"✅ **Session-scoped fixtures provide {improvement:.1f}% performance improvement**"
            )
            report.append("- Current implementation is optimized")
            report.append(
                "- Consider extending session-scoped approach to other fixtures"
            )
        else:
            report.append(
                f"⚠️  **Session-scoped fixtures are {abs(improvement):.1f}% slower**"
            )
            report.append("- Review implementation for potential issues")
            report.append("- Consider function-scoped approach for small test suites")

        report.append("")
        report.append("**Total improvement claimed**: Session-scoped reduces overhead")
        report.append(f"**Measured improvement**: {improvement:.1f}%")

        return "\n".join(report)


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Database Performance Benchmark")
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations for each test (default: 10)",
    )
    parser.add_argument(
        "--output", type=str, help="Output file for results (default: print to console)"
    )

    args = parser.parse_args()

    benchmark = DatabasePerformanceBenchmark(iterations=args.iterations)

    try:
        results = benchmark.run_comprehensive_benchmark()
        report = benchmark.generate_report(results)

        print("=== PERFORMANCE ANALYSIS ===")
        print(report)

        if args.output:
            with open(args.output, "w") as f:
                f.write(report)
            print(f"\nResults saved to: {args.output}")

    except Exception as e:
        print(f"Error during benchmark: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
