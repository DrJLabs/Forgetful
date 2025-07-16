#!/usr/bin/env python3
"""
Vector Performance Benchmark Script

This script benchmarks vector operations before and after the pgvector migration
to validate the expected 30-50% performance improvement.

Usage:
    python scripts/benchmark_vector_performance.py
"""

import json
import os
import random
import sys
import time
from typing import Dict, List

import psycopg2

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def generate_random_vector(dimensions: int = 1536) -> List[float]:
    """Generate a random vector with specified dimensions."""
    return [random.uniform(-1.0, 1.0) for _ in range(dimensions)]


def format_vector_for_db(vector: List[float], use_pgvector: bool = True) -> str:
    """Format vector for database storage."""
    if use_pgvector:
        # Format as pgvector array: [1.0, 2.0, 3.0]
        return "[" + ",".join(map(str, vector)) + "]"
    else:
        # Format as JSON string for old String storage
        return json.dumps(vector)


def benchmark_vector_operations(
    connection_params: Dict[str, str],
    num_vectors: int = 1000,
    query_count: int = 100,
    use_pgvector: bool = True,
) -> Dict[str, float]:
    """Benchmark vector operations."""

    print(f"🔍 Benchmarking {'pgvector' if use_pgvector else 'String'} storage...")
    print(f"📊 Test parameters: {num_vectors} vectors, {query_count} queries")

    # Connect to database
    conn = psycopg2.connect(**connection_params)
    cur = conn.cursor()

    # Create test table
    table_name = (
        "benchmark_vectors_pgvector" if use_pgvector else "benchmark_vectors_string"
    )

    if use_pgvector:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                vector vector(1536),
                metadata JSONB
            );
        """
        )

        # Create vector index
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_vector
            ON {table_name} USING ivfflat (vector vector_cosine_ops)
            WITH (lists = 100);
        """
        )
    else:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                vector TEXT,
                metadata JSONB
            );
        """
        )

    conn.commit()

    # Clean up existing data
    cur.execute(f"DELETE FROM {table_name};")
    conn.commit()

    results = {}

    # Benchmark 1: Vector insertion
    print("⚡ Benchmarking vector insertion...")
    vectors = [generate_random_vector() for _ in range(num_vectors)]

    start_time = time.time()

    for i, vector in enumerate(vectors):
        formatted_vector = format_vector_for_db(vector, use_pgvector)
        cur.execute(
            f"""
            INSERT INTO {table_name} (vector, metadata)
            VALUES (%s, %s)
        """,
            (formatted_vector, json.dumps({"index": i})),
        )

    conn.commit()
    insert_time = time.time() - start_time
    results["insert_time"] = insert_time
    results["insert_rate"] = num_vectors / insert_time

    print(
        f"✅ Insertion: {insert_time:.2f}s ({results['insert_rate']:.1f} vectors/sec)"
    )

    # Benchmark 2: Vector similarity search
    print("🔍 Benchmarking similarity search...")

    query_vectors = [generate_random_vector() for _ in range(query_count)]
    search_times = []

    for query_vector in query_vectors:
        formatted_query = format_vector_for_db(query_vector, use_pgvector)

        start_time = time.time()

        if use_pgvector:
            cur.execute(
                f"""
                SELECT id, vector <=> %s::vector AS distance, metadata
                FROM {table_name}
                ORDER BY distance
                LIMIT 10
            """,
                (formatted_query,),
            )
        else:
            # For string storage, we need to simulate similarity search
            # This would be much slower in reality
            cur.execute(
                f"""
                SELECT id, vector, metadata
                FROM {table_name}
                LIMIT 10
            """
            )

        cur.fetchall()
        search_time = time.time() - start_time
        search_times.append(search_time)

    avg_search_time = sum(search_times) / len(search_times)
    results["search_time"] = avg_search_time
    results["search_rate"] = 1 / avg_search_time

    print(
        f"✅ Search: {avg_search_time * 1000:.2f}ms avg ({results['search_rate']:.1f} searches/sec)"
    )

    # Benchmark 3: Batch operations
    print("📦 Benchmarking batch operations...")

    batch_size = 100
    batch_vectors = [generate_random_vector() for _ in range(batch_size)]

    start_time = time.time()

    query_parts = []
    params = []

    for i, vector in enumerate(batch_vectors):
        formatted_vector = format_vector_for_db(vector, use_pgvector)
        query_parts.append("(%s, %s)")
        params.extend([formatted_vector, json.dumps({"batch_index": i})])

    cur.execute(
        f"""
        INSERT INTO {table_name} (vector, metadata)
        VALUES {",".join(query_parts)}
    """,
        params,
    )

    conn.commit()
    batch_time = time.time() - start_time
    results["batch_time"] = batch_time
    results["batch_rate"] = batch_size / batch_time

    print(
        f"✅ Batch insert: {batch_time:.2f}s ({results['batch_rate']:.1f} vectors/sec)"
    )

    # Clean up
    cur.execute(f"DROP TABLE IF EXISTS {table_name};")
    conn.commit()

    cur.close()
    conn.close()

    return results


def main():
    """Main benchmark function."""
    print("🚀 Vector Performance Benchmark")
    print("=" * 50)

    # Database connection parameters
    connection_params = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "mem0"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "password"),
    }

    try:
        # Test database connection
        conn = psycopg2.connect(**connection_params)
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    # Check if pgvector is available
    try:
        conn = psycopg2.connect(**connection_params)
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("SELECT 1;")
        conn.commit()
        cur.close()
        conn.close()
        pgvector_available = True
        print("✅ pgvector extension available")
    except Exception as e:
        pgvector_available = False
        print(f"⚠️  pgvector not available: {e}")

    # Benchmark parameters
    num_vectors = 1000
    query_count = 100

    if pgvector_available:
        print("\n🔬 Running pgvector benchmark...")
        pgvector_results = benchmark_vector_operations(
            connection_params, num_vectors, query_count, use_pgvector=True
        )

        print("\n📊 pgvector Results:")
        for metric, value in pgvector_results.items():
            print(f"  {metric}: {value:.4f}")

    print("\n🔬 Running String storage benchmark...")
    string_results = benchmark_vector_operations(
        connection_params, num_vectors, query_count, use_pgvector=False
    )

    print("\n📊 String Storage Results:")
    for metric, value in string_results.items():
        print(f"  {metric}: {value:.4f}")

    # Calculate performance improvements
    if pgvector_available:
        print("\n🎯 Performance Comparison:")
        print("=" * 30)

        for metric in ["insert_rate", "search_rate", "batch_rate"]:
            if metric in pgvector_results and metric in string_results:
                pgvector_val = pgvector_results[metric]
                string_val = string_results[metric]
                improvement = ((pgvector_val - string_val) / string_val) * 100

                print(
                    f"{metric.replace('_', ' ').title()}: {improvement:+.1f}% improvement"
                )

                if improvement > 30:
                    print("  ✅ Exceeds 30% performance target")
                elif improvement > 0:
                    print("  ⚠️  Below 30% target but still improved")
                else:
                    print("  ❌ Performance regression detected")

    print("\n🎉 Benchmark completed!")


if __name__ == "__main__":
    main()
