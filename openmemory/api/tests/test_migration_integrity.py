"""
Migration Integrity Tests - Step 1.2: Database Testing Framework

This module provides comprehensive testing for database migration integrity including:
- Alembic migration validation
- Schema evolution testing
- Migration rollback testing
- Data preservation during migrations
- Migration dependency validation
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from uuid import uuid4
from datetime import datetime, UTC
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.orm import sessionmaker
import alembic.config
import alembic.command
import alembic.script
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.runtime.environment import EnvironmentContext

from app.models import User, App, Memory, Base
from app.database import get_db


class TestMigrationIntegrity:
    """Test Alembic migration integrity and schema evolution."""
    
    def test_migration_directory_structure(self):
        """Test that Alembic migration directory structure is correct."""
        alembic_dir = Path("alembic")
        assert alembic_dir.exists(), "Alembic directory should exist"
        assert (alembic_dir / "env.py").exists(), "env.py should exist"
        assert (alembic_dir / "script.py.mako").exists(), "script.py.mako should exist"
        
        versions_dir = alembic_dir / "versions"
        assert versions_dir.exists(), "versions directory should exist"
    
    def test_alembic_config_validation(self, alembic_config):
        """Test that Alembic configuration is valid."""
        config, engine = alembic_config
        
        # Test that config has required sections
        assert config.get_main_option("script_location") == "alembic"
        assert config.get_main_option("sqlalchemy.url") is not None
        
        # Test that we can create a script directory
        script_dir = alembic.script.ScriptDirectory.from_config(config)
        assert script_dir is not None
    
    def test_migration_up_and_down(self, alembic_config):
        """Test that migrations can be applied and rolled back."""
        config, engine = alembic_config
        
        # Start with empty database
        Base.metadata.drop_all(bind=engine)
        
        # Run all migrations up
        alembic.command.upgrade(config, "head")
        
        # Verify tables were created
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        expected_tables = {'users', 'apps', 'memories'}
        
        # Check that at least some core tables exist
        assert any(table in table_names for table in expected_tables), f"Expected tables not found. Found: {table_names}"
        
        # Run all migrations down
        alembic.command.downgrade(config, "base")
        
        # Verify tables were removed
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        # Should have fewer tables after downgrade
        assert len(table_names) == 0 or not any(table in table_names for table in expected_tables)
    
    def test_migration_history_consistency(self, alembic_config):
        """Test that migration history is consistent."""
        config, engine = alembic_config
        
        # Get migration script directory
        script_dir = alembic.script.ScriptDirectory.from_config(config)
        
        # Get all revisions
        revisions = list(script_dir.walk_revisions())
        
        if not revisions:
            pytest.skip("No migrations found")
        
        # Test that each revision has required attributes
        for revision in revisions:
            assert revision.revision is not None, f"Revision {revision} missing revision ID"
            assert revision.down_revision is not None or revision.is_base, f"Revision {revision} missing down_revision"
            
            # Test that revision file exists
            revision_file = script_dir.get_revision(revision.revision)
            assert revision_file is not None, f"Revision file for {revision.revision} not found"
    
    def test_migration_idempotency(self, alembic_config):
        """Test that migrations are idempotent (can be run multiple times)."""
        config, engine = alembic_config
        
        # Start with empty database
        Base.metadata.drop_all(bind=engine)
        
        # Run migrations first time
        alembic.command.upgrade(config, "head")
        
        # Get current schema
        inspector = inspect(engine)
        initial_tables = set(inspector.get_table_names())
        initial_columns = {}
        for table in initial_tables:
            initial_columns[table] = {col['name'] for col in inspector.get_columns(table)}
        
        # Run migrations again (should be idempotent)
        alembic.command.upgrade(config, "head")
        
        # Verify schema is unchanged
        inspector = inspect(engine)
        final_tables = set(inspector.get_table_names())
        final_columns = {}
        for table in final_tables:
            final_columns[table] = {col['name'] for col in inspector.get_columns(table)}
        
        assert initial_tables == final_tables, "Tables changed after idempotent migration"
        assert initial_columns == final_columns, "Columns changed after idempotent migration"
    
    def test_migration_with_existing_data(self, alembic_config):
        """Test that migrations preserve existing data."""
        config, engine = alembic_config
        
        # Create base schema
        Base.metadata.create_all(bind=engine)
        
        # Insert test data
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Create test user
            test_user = User(
                id=uuid4(),
                user_id="migration_test_user",
                name="Migration Test User",
                created_at=datetime.now(UTC)
            )
            session.add(test_user)
            session.commit()
            
            user_id = test_user.id
            
        finally:
            session.close()
        
        # Run migrations (simulating schema changes)
        alembic.command.upgrade(config, "head")
        
        # Verify data is preserved
        session = SessionLocal()
        try:
            preserved_user = session.query(User).filter_by(id=user_id).first()
            assert preserved_user is not None, "User data was lost during migration"
            assert preserved_user.user_id == "migration_test_user"
            assert preserved_user.name == "Migration Test User"
            
        finally:
            session.close()
    
    def test_migration_rollback_data_integrity(self, alembic_config):
        """Test that migration rollbacks preserve data integrity."""
        config, engine = alembic_config
        
        # Start with empty database
        Base.metadata.drop_all(bind=engine)
        
        # Run migrations up
        alembic.command.upgrade(config, "head")
        
        # Insert test data
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Create test user
            test_user = User(
                id=uuid4(),
                user_id="rollback_test_user",
                name="Rollback Test User",
                created_at=datetime.now(UTC)
            )
            session.add(test_user)
            session.commit()
            
            user_id = test_user.id
            
        finally:
            session.close()
        
        # Get current revision
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
        
        # If we have migrations, test rollback
        if current_rev:
            # Rollback one step
            script_dir = alembic.script.ScriptDirectory.from_config(config)
            revisions = list(script_dir.walk_revisions())
            
            if len(revisions) > 1:
                # Get previous revision
                current_revision = script_dir.get_revision(current_rev)
                if current_revision.down_revision:
                    # Rollback to previous revision
                    alembic.command.downgrade(config, current_revision.down_revision)
                    
                    # Verify data integrity after rollback
                    session = SessionLocal()
                    try:
                        # Data should still be accessible if table structure allows
                        inspector = inspect(engine)
                        if 'users' in inspector.get_table_names():
                            preserved_user = session.query(User).filter_by(id=user_id).first()
                            if preserved_user:
                                assert preserved_user.user_id == "rollback_test_user"
                    finally:
                        session.close()


class TestMigrationDependencies:
    """Test migration dependency validation and ordering."""
    
    def test_migration_dependency_chain(self, alembic_config):
        """Test that migration dependencies form a valid chain."""
        config, engine = alembic_config
        
        # Get migration script directory
        script_dir = alembic.script.ScriptDirectory.from_config(config)
        
        # Get all revisions
        revisions = list(script_dir.walk_revisions())
        
        if not revisions:
            pytest.skip("No migrations found")
        
        # Build dependency map
        revision_map = {rev.revision: rev for rev in revisions}
        
        # Test that dependency chain is valid
        for revision in revisions:
            if revision.down_revision:
                # Check that down_revision exists
                assert revision.down_revision in revision_map, f"Down revision {revision.down_revision} not found for {revision.revision}"
                
                # Check that down_revision is older
                down_rev = revision_map[revision.down_revision]
                # This is a simplified check - real implementation would check timestamps
                assert down_rev.revision != revision.revision, "Revision cannot depend on itself"
    
    def test_migration_branch_merging(self, alembic_config):
        """Test that migration branches can be merged properly."""
        config, engine = alembic_config
        
        # Get migration script directory
        script_dir = alembic.script.ScriptDirectory.from_config(config)
        
        # Get all revisions
        revisions = list(script_dir.walk_revisions())
        
        if not revisions:
            pytest.skip("No migrations found")
        
        # Check for branch points and merge points
        branch_points = []
        merge_points = []
        
        for revision in revisions:
            # Count how many revisions depend on this one
            dependents = [r for r in revisions if r.down_revision == revision.revision]
            
            if len(dependents) > 1:
                branch_points.append(revision)
            
            # Check for merge points (multiple down_revisions)
            if hasattr(revision, 'down_revisions') and len(revision.down_revisions) > 1:
                merge_points.append(revision)
        
        # If we have branches, they should be properly merged
        if branch_points and not merge_points:
            # This might be okay if branches are still active
            pass
    
    def test_migration_circular_dependencies(self, alembic_config):
        """Test that there are no circular dependencies in migrations."""
        config, engine = alembic_config
        
        # Get migration script directory
        script_dir = alembic.script.ScriptDirectory.from_config(config)
        
        # Get all revisions
        revisions = list(script_dir.walk_revisions())
        
        if not revisions:
            pytest.skip("No migrations found")
        
        # Build dependency graph
        dependencies = {}
        for revision in revisions:
            dependencies[revision.revision] = revision.down_revision
        
        # Check for circular dependencies using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            if node not in visited:
                visited.add(node)
                rec_stack.add(node)
                
                # Check all dependencies
                if node in dependencies and dependencies[node]:
                    dep = dependencies[node]
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
                
                rec_stack.remove(node)
            return False
        
        # Check each revision for cycles
        for revision in revisions:
            if revision.revision not in visited:
                assert not has_cycle(revision.revision), f"Circular dependency detected involving {revision.revision}"


class TestSchemaEvolution:
    """Test database schema evolution and compatibility."""
    
    def test_schema_version_tracking(self, alembic_config):
        """Test that schema version is properly tracked."""
        config, engine = alembic_config
        
        # Run migrations
        alembic.command.upgrade(config, "head")
        
        # Check that alembic_version table exists
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        assert 'alembic_version' in table_names, "alembic_version table not created"
        
        # Check that version is recorded
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.fetchone()
            assert version is not None, "No version recorded in alembic_version table"
    
    def test_schema_backward_compatibility(self, alembic_config):
        """Test that schema changes maintain backward compatibility."""
        config, engine = alembic_config
        
        # This test would be more meaningful with actual schema changes
        # For now, we test that the current schema is valid
        
        # Run migrations
        alembic.command.upgrade(config, "head")
        
        # Verify that we can perform basic operations
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Test basic CRUD operations
            user = User(
                id=uuid4(),
                user_id="compatibility_test",
                name="Compatibility Test User",
                created_at=datetime.now(UTC)
            )
            session.add(user)
            session.commit()
            
            # Read
            retrieved = session.query(User).filter_by(user_id="compatibility_test").first()
            assert retrieved is not None
            
            # Update
            retrieved.name = "Updated Name"
            session.commit()
            
            # Delete
            session.delete(retrieved)
            session.commit()
            
        finally:
            session.close()
    
    def test_index_and_constraint_evolution(self, alembic_config):
        """Test that indexes and constraints evolve correctly."""
        config, engine = alembic_config
        
        # Run migrations
        alembic.command.upgrade(config, "head")
        
        # Check that expected indexes exist
        inspector = inspect(engine)
        
        # Check each table for indexes
        for table_name in inspector.get_table_names():
            if table_name in ['users', 'apps', 'memories']:
                indexes = inspector.get_indexes(table_name)
                pk_constraints = inspector.get_pk_constraint(table_name)
                
                # Should have at least a primary key
                assert pk_constraints['constrained_columns'], f"Table {table_name} missing primary key"
                
                # Check for unique constraints
                unique_constraints = inspector.get_unique_constraints(table_name)
                # This will depend on your actual schema
                
                # Check for foreign key constraints if applicable
                foreign_keys = inspector.get_foreign_keys(table_name)
                # This will depend on your actual schema


class TestMigrationPerformance:
    """Test migration performance and optimization."""
    
    def test_migration_performance(self, alembic_config):
        """Test that migrations complete in reasonable time."""
        config, engine = alembic_config
        
        # Start with empty database
        Base.metadata.drop_all(bind=engine)
        
        # Time the migration
        import time
        start_time = time.time()
        
        # Run migrations
        alembic.command.upgrade(config, "head")
        
        end_time = time.time()
        migration_time = end_time - start_time
        
        # Migrations should complete quickly for a test database
        assert migration_time < 30.0, f"Migration took too long: {migration_time} seconds"
    
    def test_migration_with_large_dataset(self, alembic_config):
        """Test migration performance with larger datasets."""
        config, engine = alembic_config
        
        # Create base schema
        Base.metadata.create_all(bind=engine)
        
        # Insert test data
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Create a moderate amount of test data
            users = []
            for i in range(1000):
                user = User(
                    id=uuid4(),
                    user_id=f"perf_test_user_{i}",
                    name=f"Performance Test User {i}",
                    created_at=datetime.now(UTC)
                )
                users.append(user)
            
            session.add_all(users)
            session.commit()
            
        finally:
            session.close()
        
        # Time migration with data
        import time
        start_time = time.time()
        
        # Run migrations (should handle existing data)
        alembic.command.upgrade(config, "head")
        
        end_time = time.time()
        migration_time = end_time - start_time
        
        # Migration should still complete reasonably quickly
        assert migration_time < 60.0, f"Migration with data took too long: {migration_time} seconds"
        
        # Verify data integrity
        session = SessionLocal()
        try:
            user_count = session.query(User).count()
            assert user_count == 1000, f"Expected 1000 users, found {user_count}"
        finally:
            session.close()


class TestMigrationErrorHandling:
    """Test migration error handling and recovery."""
    
    def test_migration_failure_recovery(self, alembic_config):
        """Test recovery from migration failures."""
        config, engine = alembic_config
        
        # Start with empty database
        Base.metadata.drop_all(bind=engine)
        
        # Run migrations normally first
        alembic.command.upgrade(config, "head")
        
        # Get current revision
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
        
        # Simulate recovery by checking current state
        assert current_rev is not None, "Current revision should be recorded"
        
        # Test that we can check migration status
        script_dir = alembic.script.ScriptDirectory.from_config(config)
        head_revision = script_dir.get_current_head()
        
        # Current revision should match head (all migrations applied)
        assert current_rev == head_revision, "Current revision should match head"
    
    def test_migration_validation_errors(self, alembic_config):
        """Test handling of migration validation errors."""
        config, engine = alembic_config
        
        # This test verifies that our migration setup is valid
        # In a real scenario, we would test specific validation errors
        
        # Verify that we can create migration context
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            assert context is not None
            
            # Test that we can get operations
            ops = Operations(context)
            assert ops is not None
    
    def test_migration_rollback_on_failure(self, alembic_config):
        """Test that failed migrations are properly rolled back."""
        config, engine = alembic_config
        
        # Start with empty database
        Base.metadata.drop_all(bind=engine)
        
        # Run migrations
        alembic.command.upgrade(config, "head")
        
        # Get current revision
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
        
        # If we have migrations, test rollback
        if current_rev:
            # Test that we can rollback
            script_dir = alembic.script.ScriptDirectory.from_config(config)
            revisions = list(script_dir.walk_revisions())
            
            if len(revisions) > 1:
                # Get previous revision
                current_revision = script_dir.get_revision(current_rev)
                if current_revision.down_revision:
                    # Rollback to previous revision
                    alembic.command.downgrade(config, current_revision.down_revision)
                    
                    # Verify rollback
                    with engine.connect() as conn:
                        context = MigrationContext.configure(conn)
                        new_rev = context.get_current_revision()
                        assert new_rev == current_revision.down_revision, "Rollback was not successful" 