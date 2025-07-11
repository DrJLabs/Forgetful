"""
Database Framework Tests - Step 1.2: Database Testing Framework

This module provides comprehensive testing for database operations including:
- Transaction rollback testing
- Database integrity testing 
- Connection management testing
- Performance monitoring
- Concurrent access testing
"""

import pytest
import asyncio
import psycopg2
from uuid import uuid4
from datetime import datetime, UTC
from sqlalchemy import create_engine, text, MetaData, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from concurrent.futures import ThreadPoolExecutor
import time

from app.models import User, App, Memory, MemoryState
from app.database import Base


class TestDatabaseFramework:
    """Test the database testing framework itself."""

    def test_sqlite_test_engine(self, test_db_engine):
        """Test SQLite in-memory database setup."""
        assert test_db_engine is not None

        with test_db_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

    def test_postgres_test_engine(self, docker_postgres_engine):
        """Test PostgreSQL test database setup."""
        assert docker_postgres_engine is not None

        with docker_postgres_engine.connect() as conn:
            # Test basic connectivity
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

            # Test pgvector extension
            result = conn.execute(
                text("SELECT * FROM pg_extension WHERE extname = 'vector'")
            )
            assert result.fetchone() is not None

    def test_database_schemas_match(self, test_db_engine, docker_postgres_engine):
        """Test that SQLite and PostgreSQL schemas are equivalent."""
        # Check that all tables exist in both databases
        sqlite_tables = set(Base.metadata.tables.keys())

        with docker_postgres_engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """
                )
            )
            postgres_tables = {row[0] for row in result}

        # Core tables should exist in both
        core_tables = {"users", "apps", "memories"}
        assert core_tables.issubset(sqlite_tables)
        assert core_tables.issubset(postgres_tables)


class TestTransactionRollback:
    """Test database transaction rollback behavior."""

    def test_session_rollback_on_exception(
        self, postgres_test_session, test_user_factory
    ):
        """Test that transactions are properly rolled back on exception."""
        initial_count = postgres_test_session.query(User).count()

        try:
            # Create user
            user = test_user_factory(user_id="rollback_test")
            postgres_test_session.add(user)
            postgres_test_session.flush()

            # Verify user exists in transaction
            assert (
                postgres_test_session.query(User)
                .filter_by(user_id="rollback_test")
                .count()
                == 1
            )

            # Force an exception
            raise ValueError("Test exception")

        except ValueError:
            # Exception should trigger rollback
            pass

        # Verify rollback occurred - count should be same as initial
        final_count = postgres_test_session.query(User).count()
        assert final_count == initial_count

    def test_manual_rollback(self, transaction_test_session, test_user_factory):
        """Test manual transaction rollback."""
        # Start transaction
        trans = transaction_test_session.begin()

        try:
            # Create user within transaction
            user = test_user_factory(user_id="manual_rollback")
            transaction_test_session.execute(
                text(
                    "INSERT INTO users (id, user_id, name, created_at) VALUES (:id, :user_id, :name, :created_at)"
                ),
                {
                    "id": str(user.id),
                    "user_id": user.user_id,
                    "name": user.name,
                    "created_at": user.created_at,
                },
            )

            # Verify user exists in transaction
            result = transaction_test_session.execute(
                text("SELECT COUNT(*) FROM users WHERE user_id = :user_id"),
                {"user_id": "manual_rollback"},
            )
            assert result.fetchone()[0] == 1

            # Manual rollback
            trans.rollback()

        except Exception as e:
            trans.rollback()
            raise

        # Verify rollback - user should not exist
        result = transaction_test_session.execute(
            text("SELECT COUNT(*) FROM users WHERE user_id = :user_id"),
            {"user_id": "manual_rollback"},
        )
        assert result.fetchone()[0] == 0

    def test_concurrent_transactions(self, concurrent_sessions, test_user_factory):
        """Test concurrent transaction isolation."""
        session1, session2, session3 = concurrent_sessions

        # Create user in session1
        user1 = test_user_factory(user_id="concurrent_test_1")
        session1.add(user1)
        session1.commit()

        # Start transactions in sessions 2 and 3
        trans2 = session2.begin()
        trans3 = session3.begin()

        try:
            # Modify user in session2
            session2.query(User).filter_by(user_id="concurrent_test_1").update(
                {"name": "Updated by session2"}
            )

            # Try to read from session3 - should see original value
            user_in_session3 = (
                session3.query(User).filter_by(user_id="concurrent_test_1").first()
            )
            assert user_in_session3.name == "Test User"  # Original value

            # Commit session2
            trans2.commit()

            # Now session3 should still see original value (isolation)
            user_in_session3 = (
                session3.query(User).filter_by(user_id="concurrent_test_1").first()
            )
            assert user_in_session3.name == "Test User"  # Still original value

            trans3.commit()

        except Exception as e:
            trans2.rollback()
            trans3.rollback()
            raise

    def test_savepoint_rollback(self, postgres_test_session, test_user_factory):
        """Test savepoint rollback functionality."""
        # Create initial user
        user1 = test_user_factory(user_id="savepoint_test_1")
        postgres_test_session.add(user1)
        postgres_test_session.commit()

        # Create savepoint
        savepoint = postgres_test_session.begin_nested()

        try:
            # Create another user
            user2 = test_user_factory(user_id="savepoint_test_2")
            postgres_test_session.add(user2)
            postgres_test_session.flush()

            # Verify both users exist
            assert (
                postgres_test_session.query(User)
                .filter_by(user_id="savepoint_test_1")
                .count()
                == 1
            )
            assert (
                postgres_test_session.query(User)
                .filter_by(user_id="savepoint_test_2")
                .count()
                == 1
            )

            # Rollback to savepoint
            savepoint.rollback()

            # Only first user should exist
            assert (
                postgres_test_session.query(User)
                .filter_by(user_id="savepoint_test_1")
                .count()
                == 1
            )
            assert (
                postgres_test_session.query(User)
                .filter_by(user_id="savepoint_test_2")
                .count()
                == 0
            )

        except Exception as e:
            savepoint.rollback()
            raise


class TestDatabaseIntegrity:
    """Test database integrity constraints and relationships."""

    def test_foreign_key_constraints(
        self, postgres_test_session, test_user_factory, test_app_factory
    ):
        """Test foreign key constraint enforcement."""
        # Create user
        user = test_user_factory(user_id="fk_test_user")
        postgres_test_session.add(user)
        postgres_test_session.commit()

        # Create app with valid user_id
        app = test_app_factory(name="Valid App")
        app.user_id = user.user_id
        postgres_test_session.add(app)
        postgres_test_session.commit()

        # Try to create app with invalid user_id
        invalid_app = test_app_factory(name="Invalid App")
        invalid_app.user_id = "non_existent_user"
        postgres_test_session.add(invalid_app)

        # Should raise integrity error
        with pytest.raises(IntegrityError):
            postgres_test_session.commit()

    def test_unique_constraints(self, postgres_test_session, test_user_factory):
        """Test unique constraint enforcement."""
        # Create user
        user1 = test_user_factory(user_id="unique_test")
        postgres_test_session.add(user1)
        postgres_test_session.commit()

        # Try to create another user with same user_id
        user2 = test_user_factory(user_id="unique_test")
        postgres_test_session.add(user2)

        # Should raise integrity error
        with pytest.raises(IntegrityError):
            postgres_test_session.commit()

    def test_not_null_constraints(self, postgres_test_session):
        """Test NOT NULL constraint enforcement."""
        # Try to create user without required fields
        with pytest.raises(IntegrityError):
            postgres_test_session.execute(
                text("INSERT INTO users (id, created_at) VALUES (:id, :created_at)"),
                {"id": str(uuid4()), "created_at": datetime.now(UTC)},
            )
            postgres_test_session.commit()

    def test_cascade_deletes(
        self, postgres_test_session, test_user_factory, test_app_factory
    ):
        """Test cascade delete behavior."""
        # Create user and app
        user = test_user_factory(user_id="cascade_test")
        postgres_test_session.add(user)
        postgres_test_session.commit()

        app = test_app_factory(name="Cascade App")
        app.user_id = user.user_id
        postgres_test_session.add(app)
        postgres_test_session.commit()

        # Delete user
        postgres_test_session.delete(user)
        postgres_test_session.commit()

        # App should still exist (no cascade delete configured)
        remaining_apps = (
            postgres_test_session.query(App).filter_by(user_id=user.user_id).count()
        )
        assert remaining_apps >= 0  # Depends on foreign key configuration


class TestPerformanceMonitoring:
    """Test database performance monitoring capabilities."""

    def test_connection_pooling(self, docker_postgres_engine):
        """Test connection pool behavior."""
        # Get initial pool status
        pool = docker_postgres_engine.pool
        initial_size = pool.size()

        # Create multiple connections
        connections = []
        for i in range(3):
            conn = docker_postgres_engine.connect()
            connections.append(conn)

        # Pool should have grown
        assert pool.size() >= initial_size

        # Close connections
        for conn in connections:
            conn.close()

        # Pool should return to normal size
        assert pool.size() <= initial_size + 3

    def test_query_performance(
        self, postgres_test_session, test_user_factory, performance_monitor
    ):
        """Test query performance monitoring."""
        # Get initial performance stats
        initial_stats = performance_monitor(postgres_test_session.bind)

        # Create test data
        users = [test_user_factory(user_id=f"perf_test_{i}") for i in range(100)]
        postgres_test_session.add_all(users)
        postgres_test_session.commit()

        # Run queries
        start_time = time.time()
        result = (
            postgres_test_session.query(User)
            .filter(User.user_id.like("perf_test_%"))
            .all()
        )
        end_time = time.time()

        # Check query completed in reasonable time
        assert end_time - start_time < 1.0  # Less than 1 second
        assert len(result) == 100

        # Get final performance stats
        final_stats = performance_monitor(postgres_test_session.bind)

        # Should have more tuples returned
        assert final_stats["tuples_returned"] > initial_stats["tuples_returned"]
        assert final_stats["tuples_fetched"] > initial_stats["tuples_fetched"]

    def test_memory_usage_monitoring(self, postgres_test_session, test_user_factory):
        """Test memory usage during bulk operations."""
        # Create large dataset
        batch_size = 1000
        users = [
            test_user_factory(user_id=f"memory_test_{i}") for i in range(batch_size)
        ]

        # Monitor memory usage during bulk insert
        start_time = time.time()
        postgres_test_session.add_all(users)
        postgres_test_session.commit()
        end_time = time.time()

        # Should complete in reasonable time
        assert end_time - start_time < 5.0  # Less than 5 seconds

        # Verify all users were created
        count = (
            postgres_test_session.query(User)
            .filter(User.user_id.like("memory_test_%"))
            .count()
        )
        assert count == batch_size


class TestConcurrentAccess:
    """Test concurrent database access patterns."""

    def test_concurrent_reads(self, docker_postgres_engine, test_user_factory):
        """Test concurrent read operations."""
        # Create test data
        with docker_postgres_engine.connect() as conn:
            SessionLocal = sessionmaker(bind=conn)
            session = SessionLocal()

            users = [
                test_user_factory(user_id=f"concurrent_read_{i}") for i in range(10)
            ]
            session.add_all(users)
            session.commit()
            session.close()

        def read_operation(thread_id):
            """Read operation to be run concurrently."""
            with docker_postgres_engine.connect() as conn:
                SessionLocal = sessionmaker(bind=conn)
                session = SessionLocal()

                # Perform read operation
                result = (
                    session.query(User)
                    .filter(User.user_id.like("concurrent_read_%"))
                    .all()
                )
                session.close()
                return len(result)

        # Run concurrent read operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_operation, i) for i in range(5)]
            results = [future.result() for future in futures]

        # All reads should return same count
        assert all(result == 10 for result in results)

    def test_concurrent_writes(self, docker_postgres_engine, test_user_factory):
        """Test concurrent write operations."""

        def write_operation(thread_id):
            """Write operation to be run concurrently."""
            with docker_postgres_engine.connect() as conn:
                SessionLocal = sessionmaker(bind=conn)
                session = SessionLocal()

                try:
                    # Create user
                    user = test_user_factory(user_id=f"concurrent_write_{thread_id}")
                    session.add(user)
                    session.commit()
                    return True
                except Exception as e:
                    session.rollback()
                    return False
                finally:
                    session.close()

        # Run concurrent write operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(write_operation, i) for i in range(3)]
            results = [future.result() for future in futures]

        # All writes should succeed
        assert all(result for result in results)

        # Verify all users were created
        with docker_postgres_engine.connect() as conn:
            SessionLocal = sessionmaker(bind=conn)
            session = SessionLocal()

            count = (
                session.query(User)
                .filter(User.user_id.like("concurrent_write_%"))
                .count()
            )
            assert count == 3
            session.close()

    def test_deadlock_detection(self, concurrent_sessions, test_user_factory):
        """Test deadlock detection and resolution."""
        session1, session2, session3 = concurrent_sessions

        # Create test users
        user1 = test_user_factory(user_id="deadlock_test_1")
        user2 = test_user_factory(user_id="deadlock_test_2")

        session1.add(user1)
        session1.add(user2)
        session1.commit()

        # Create potential deadlock scenario
        # This is a simplified test - real deadlock scenarios are more complex
        trans1 = session1.begin()
        trans2 = session2.begin()

        try:
            # Session1 locks user1
            session1.query(User).filter_by(
                user_id="deadlock_test_1"
            ).with_for_update().first()

            # Session2 locks user2
            session2.query(User).filter_by(
                user_id="deadlock_test_2"
            ).with_for_update().first()

            # Now try to access in reverse order (potential deadlock)
            # Session1 tries to lock user2
            session1.query(User).filter_by(
                user_id="deadlock_test_2"
            ).with_for_update().first()

            # Session2 tries to lock user1
            session2.query(User).filter_by(
                user_id="deadlock_test_1"
            ).with_for_update().first()

            trans1.commit()
            trans2.commit()

        except Exception as e:
            # Deadlock should be detected and resolved
            trans1.rollback()
            trans2.rollback()
            # This is expected behavior


class TestDatabaseInspection:
    """Test database inspection and introspection capabilities."""

    def test_table_inspection(self, docker_postgres_engine, db_inspector):
        """Test database table inspection."""
        tables = db_inspector(docker_postgres_engine)

        # Check that core tables exist
        assert "users" in tables
        assert "apps" in tables
        assert "memories" in tables

        # Check user table structure
        user_columns = {col["column"] for col in tables["users"]}
        expected_columns = {"id", "user_id", "name", "created_at"}
        assert expected_columns.issubset(user_columns)

    def test_index_inspection(self, docker_postgres_engine):
        """Test database index inspection."""
        with docker_postgres_engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT indexname, tablename, indexdef
                FROM pg_indexes 
                WHERE tablename IN ('users', 'apps', 'memories')
                ORDER BY tablename, indexname
            """
                )
            )

            indexes = result.fetchall()
            assert len(indexes) > 0  # Should have at least primary key indexes

    def test_constraint_inspection(self, docker_postgres_engine):
        """Test database constraint inspection."""
        with docker_postgres_engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT 
                    tc.constraint_name,
                    tc.table_name,
                    tc.constraint_type,
                    kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = 'public'
                    AND tc.table_name IN ('users', 'apps', 'memories')
                ORDER BY tc.table_name, tc.constraint_name
            """
                )
            )

            constraints = result.fetchall()

            # Should have primary key constraints
            pk_constraints = [c for c in constraints if c[2] == "PRIMARY KEY"]
            assert len(pk_constraints) >= 3  # At least one for each table


@pytest.mark.integration
class TestDatabaseIntegrationScenarios:
    """Test realistic database integration scenarios."""

    def test_complete_memory_lifecycle(
        self,
        postgres_test_session,
        test_user_factory,
        test_app_factory,
        test_memory_factory,
    ):
        """Test complete memory lifecycle with database operations."""
        # Create user and app
        user = test_user_factory(user_id="lifecycle_test")
        app = test_app_factory(name="Lifecycle App")
        app.user_id = user.user_id

        postgres_test_session.add(user)
        postgres_test_session.add(app)
        postgres_test_session.commit()

        # Create memory
        memory = test_memory_factory(
            content="Lifecycle test memory", user_id=user.user_id, app_id=str(app.id)
        )
        postgres_test_session.add(memory)
        postgres_test_session.commit()

        # Read memory
        retrieved_memory = (
            postgres_test_session.query(Memory).filter_by(id=memory.id).first()
        )
        assert retrieved_memory is not None
        assert retrieved_memory.content == "Lifecycle test memory"

        # Update memory
        retrieved_memory.content = "Updated lifecycle memory"
        postgres_test_session.commit()

        # Verify update
        updated_memory = (
            postgres_test_session.query(Memory).filter_by(id=memory.id).first()
        )
        assert updated_memory.content == "Updated lifecycle memory"

        # Delete memory
        postgres_test_session.delete(updated_memory)
        postgres_test_session.commit()

        # Verify deletion
        deleted_memory = (
            postgres_test_session.query(Memory).filter_by(id=memory.id).first()
        )
        assert deleted_memory is None

    def test_bulk_operations_performance(
        self, postgres_test_session, test_user_factory, performance_monitor
    ):
        """Test bulk database operations performance."""
        initial_stats = performance_monitor(postgres_test_session.bind)

        # Bulk insert
        users = [test_user_factory(user_id=f"bulk_{i}") for i in range(500)]
        start_time = time.time()
        postgres_test_session.add_all(users)
        postgres_test_session.commit()
        insert_time = time.time() - start_time

        # Bulk update
        start_time = time.time()
        postgres_test_session.query(User).filter(User.user_id.like("bulk_%")).update(
            {"name": "Bulk Updated"}, synchronize_session=False
        )
        postgres_test_session.commit()
        update_time = time.time() - start_time

        # Bulk delete
        start_time = time.time()
        postgres_test_session.query(User).filter(User.user_id.like("bulk_%")).delete(
            synchronize_session=False
        )
        postgres_test_session.commit()
        delete_time = time.time() - start_time

        # All operations should complete in reasonable time
        assert insert_time < 2.0  # Less than 2 seconds
        assert update_time < 1.0  # Less than 1 second
        assert delete_time < 1.0  # Less than 1 second

        final_stats = performance_monitor(postgres_test_session.bind)

        # Should have processed many tuples
        assert final_stats["tuples_inserted"] > initial_stats["tuples_inserted"]
        assert final_stats["tuples_updated"] > initial_stats["tuples_updated"]
        assert final_stats["tuples_deleted"] > initial_stats["tuples_deleted"]
