#!/usr/bin/env python3
"""
Background agent connectivity testing script
"""

import os
import time

import psycopg2
from neo4j import GraphDatabase

# Test credentials - these are default test passwords for local development
TEST_DB_PASSWORD = os.getenv("TEST_DB_PASSWORD", "testpass")  # noqa: S105
TEST_NEO4J_PASSWORD = os.getenv("TEST_NEO4J_PASSWORD", "testpass")  # noqa: S105


def test_postgres_connectivity():
    """Test PostgreSQL connectivity"""
    max_retries = 10
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5433,
                database="background_test_db",
                user="postgres",
                password=TEST_DB_PASSWORD,  # noqa: S106
            )
            conn.close()
            print(f"✅ PostgreSQL connection successful (attempt {i + 1})")
            return True
        except Exception as e:
            print(f"❌ PostgreSQL connection failed (attempt {i + 1}): {e}")
            if i == max_retries - 1:
                raise
            time.sleep(5)
    return False


def test_neo4j_connectivity():
    """Test Neo4j connectivity"""
    max_retries = 10
    for i in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                "bolt://localhost:7688", auth=("neo4j", TEST_NEO4J_PASSWORD)
            )
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                assert result.single()["test"] == 1
            driver.close()
            print(f"✅ Neo4j connection successful (attempt {i + 1})")
            return True
        except Exception as e:
            print(f"❌ Neo4j connection failed (attempt {i + 1}): {e}")
            if i == max_retries - 1:
                raise
            time.sleep(5)
    return False


if __name__ == "__main__":
    print("🏥 Running background agent health checks...")

    # Test database connectivity
    postgres_ok = test_postgres_connectivity()
    neo4j_ok = test_neo4j_connectivity()

    if postgres_ok and neo4j_ok:
        print("✅ All connectivity tests passed")
        exit(0)
    else:
        print("❌ Some connectivity tests failed")
        exit(1)
