"""
Unit tests for OpenMemory API database models.
"""

import pytest
import datetime
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import User, App, Memory, Base
from app.config import USER_ID, DEFAULT_APP_ID


class TestUserModel:
    """Test cases for User model."""

    def test_user_creation(self, test_db):
        """Test creating a new user."""
        user = User(
            user_id="test_user_123",
            name="Test User",
            email="test@example.com"
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.id is not None
        assert user.user_id == "test_user_123"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_unique_user_id(self, test_db):
        """Test that user_id must be unique."""
        user1 = User(user_id="duplicate_user", name="User 1")
        user2 = User(user_id="duplicate_user", name="User 2")
        
        test_db.add(user1)
        test_db.commit()
        
        test_db.add(user2)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_user_optional_fields(self, test_db):
        """Test user creation with optional fields."""
        user = User(user_id="minimal_user")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.name is None
        assert user.email is None
        assert user.created_at is not None

    def test_user_string_representation(self, test_db):
        """Test user string representation."""
        user = User(user_id="repr_test", name="Test User")
        assert "repr_test" in str(user)

    def test_user_relationships(self, test_db):
        """Test user relationships with apps and memories."""
        user = User(user_id="relationship_test", name="Test User")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        # Test apps relationship
        app = App(
            app_id="test_app",
            name="Test App",
            user_id=user.user_id
        )
        test_db.add(app)
        test_db.commit()

        # Verify relationship
        assert len(user.apps) == 1
        assert user.apps[0].app_id == "test_app"


class TestAppModel:
    """Test cases for App model."""

    def test_app_creation(self, test_db, test_user):
        """Test creating a new app."""
        app = App(
            app_id="test_app_123",
            name="Test Application",
            description="A test application",
            user_id=test_user.user_id
        )
        test_db.add(app)
        test_db.commit()
        test_db.refresh(app)

        assert app.id is not None
        assert app.app_id == "test_app_123"
        assert app.name == "Test Application"
        assert app.description == "A test application"
        assert app.user_id == test_user.user_id
        assert app.created_at is not None
        assert app.updated_at is not None

    def test_app_unique_app_id(self, test_db, test_user):
        """Test that app_id must be unique."""
        app1 = App(app_id="duplicate_app", name="App 1", user_id=test_user.user_id)
        app2 = App(app_id="duplicate_app", name="App 2", user_id=test_user.user_id)
        
        test_db.add(app1)
        test_db.commit()
        
        test_db.add(app2)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_app_foreign_key_constraint(self, test_db):
        """Test that app requires valid user_id."""
        app = App(
            app_id="invalid_user_app",
            name="Test App",
            user_id="nonexistent_user"
        )
        test_db.add(app)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_app_optional_description(self, test_db, test_user):
        """Test app creation without description."""
        app = App(
            app_id="minimal_app",
            name="Minimal App",
            user_id=test_user.user_id
        )
        test_db.add(app)
        test_db.commit()
        test_db.refresh(app)

        assert app.description is None
        assert app.name == "Minimal App"

    def test_app_user_relationship(self, test_db, test_user):
        """Test app-user relationship."""
        app = App(
            app_id="relationship_app",
            name="Relationship Test App",
            user_id=test_user.user_id
        )
        test_db.add(app)
        test_db.commit()
        test_db.refresh(app)

        # Test relationship
        assert app.user.user_id == test_user.user_id
        assert app.user.name == test_user.name


class TestMemoryModel:
    """Test cases for Memory model."""

    def test_memory_creation(self, test_db, test_user, test_app):
        """Test creating a new memory."""
        memory = Memory(
            memory_id="test_memory_123",
            content="Test memory content",
            user_id=test_user.user_id,
            app_id=test_app.app_id,
            metadata={"category": "test", "priority": "high"}
        )
        test_db.add(memory)
        test_db.commit()
        test_db.refresh(memory)

        assert memory.id is not None
        assert memory.memory_id == "test_memory_123"
        assert memory.content == "Test memory content"
        assert memory.user_id == test_user.user_id
        assert memory.app_id == test_app.app_id
        assert memory.metadata == {"category": "test", "priority": "high"}
        assert memory.created_at is not None
        assert memory.updated_at is not None

    def test_memory_unique_memory_id(self, test_db, test_user, test_app):
        """Test that memory_id must be unique."""
        memory1 = Memory(
            memory_id="duplicate_memory",
            content="Content 1",
            user_id=test_user.user_id,
            app_id=test_app.app_id
        )
        memory2 = Memory(
            memory_id="duplicate_memory",
            content="Content 2",
            user_id=test_user.user_id,
            app_id=test_app.app_id
        )
        
        test_db.add(memory1)
        test_db.commit()
        
        test_db.add(memory2)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_memory_foreign_key_constraints(self, test_db):
        """Test that memory requires valid user_id and app_id."""
        memory = Memory(
            memory_id="invalid_refs_memory",
            content="Test content",
            user_id="nonexistent_user",
            app_id="nonexistent_app"
        )
        test_db.add(memory)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_memory_optional_fields(self, test_db, test_user, test_app):
        """Test memory creation with optional fields."""
        memory = Memory(
            memory_id="minimal_memory",
            content="Minimal content",
            user_id=test_user.user_id,
            app_id=test_app.app_id
        )
        test_db.add(memory)
        test_db.commit()
        test_db.refresh(memory)

        assert memory.metadata is None
        assert memory.vector is None
        assert memory.score is None

    def test_memory_relationships(self, test_db, test_user, test_app):
        """Test memory relationships with user and app."""
        memory = Memory(
            memory_id="relationship_memory",
            content="Relationship test content",
            user_id=test_user.user_id,
            app_id=test_app.app_id
        )
        test_db.add(memory)
        test_db.commit()
        test_db.refresh(memory)

        # Test relationships
        assert memory.user.user_id == test_user.user_id
        assert memory.app.app_id == test_app.app_id

    def test_memory_vector_storage(self, test_db, test_user, test_app):
        """Test storing vector embeddings."""
        test_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        memory = Memory(
            memory_id="vector_memory",
            content="Vector test content",
            user_id=test_user.user_id,
            app_id=test_app.app_id,
            vector=test_vector
        )
        test_db.add(memory)
        test_db.commit()
        test_db.refresh(memory)

        assert memory.vector == test_vector

    def test_memory_score_validation(self, test_db, test_user, test_app):
        """Test memory score validation."""
        memory = Memory(
            memory_id="score_memory",
            content="Score test content",
            user_id=test_user.user_id,
            app_id=test_app.app_id,
            score=0.95
        )
        test_db.add(memory)
        test_db.commit()
        test_db.refresh(memory)

        assert memory.score == 0.95

    def test_memory_metadata_json(self, test_db, test_user, test_app):
        """Test complex metadata JSON storage."""
        complex_metadata = {
            "tags": ["important", "project", "meeting"],
            "context": {
                "meeting_id": "meeting_123",
                "participants": ["user1", "user2"],
                "duration": 45
            },
            "priority": 8,
            "processed": True
        }
        
        memory = Memory(
            memory_id="complex_metadata_memory",
            content="Complex metadata content",
            user_id=test_user.user_id,
            app_id=test_app.app_id,
            metadata=complex_metadata
        )
        test_db.add(memory)
        test_db.commit()
        test_db.refresh(memory)

        assert memory.metadata == complex_metadata
        assert memory.metadata["tags"] == ["important", "project", "meeting"]
        assert memory.metadata["context"]["meeting_id"] == "meeting_123"

    def test_memory_updated_at_changes(self, test_db, test_user, test_app):
        """Test that updated_at changes on update."""
        memory = Memory(
            memory_id="update_test_memory",
            content="Original content",
            user_id=test_user.user_id,
            app_id=test_app.app_id
        )
        test_db.add(memory)
        test_db.commit()
        test_db.refresh(memory)
        
        original_updated_at = memory.updated_at
        
        # Update the memory
        memory.content = "Updated content"
        test_db.commit()
        test_db.refresh(memory)
        
        assert memory.updated_at > original_updated_at
        assert memory.content == "Updated content"


class TestModelValidation:
    """Test model validation and constraints."""

    def test_user_id_not_null(self, test_db):
        """Test that user_id cannot be null."""
        user = User(name="Test User")
        test_db.add(user)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_memory_content_not_null(self, test_db, test_user, test_app):
        """Test that memory content cannot be null."""
        memory = Memory(
            memory_id="null_content_memory",
            user_id=test_user.user_id,
            app_id=test_app.app_id
        )
        test_db.add(memory)
        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_app_name_not_null(self, test_db, test_user):
        """Test that app name cannot be null."""
        app = App(
            app_id="null_name_app",
            user_id=test_user.user_id
        )
        test_db.add(app)
        with pytest.raises(IntegrityError):
            test_db.commit()


class TestModelCascades:
    """Test cascading deletes and updates."""

    def test_user_deletion_cascade(self, test_db):
        """Test that deleting a user cascades to apps and memories."""
        # Create user, app, and memory
        user = User(user_id="cascade_user", name="Cascade Test User")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        app = App(
            app_id="cascade_app",
            name="Cascade Test App",
            user_id=user.user_id
        )
        test_db.add(app)
        test_db.commit()

        memory = Memory(
            memory_id="cascade_memory",
            content="Cascade test content",
            user_id=user.user_id,
            app_id=app.app_id
        )
        test_db.add(memory)
        test_db.commit()

        # Delete user
        test_db.delete(user)
        test_db.commit()

        # Verify cascaded deletions
        assert test_db.query(User).filter_by(user_id="cascade_user").first() is None
        assert test_db.query(App).filter_by(app_id="cascade_app").first() is None
        assert test_db.query(Memory).filter_by(memory_id="cascade_memory").first() is None

    def test_app_deletion_cascade(self, test_db, test_user):
        """Test that deleting an app cascades to memories."""
        app = App(
            app_id="cascade_app_2",
            name="Cascade Test App 2",
            user_id=test_user.user_id
        )
        test_db.add(app)
        test_db.commit()

        memory = Memory(
            memory_id="cascade_memory_2",
            content="Cascade test content 2",
            user_id=test_user.user_id,
            app_id=app.app_id
        )
        test_db.add(memory)
        test_db.commit()

        # Delete app
        test_db.delete(app)
        test_db.commit()

        # Verify memory was deleted
        assert test_db.query(Memory).filter_by(memory_id="cascade_memory_2").first() is None
        # Verify user still exists
        assert test_db.query(User).filter_by(user_id=test_user.user_id).first() is not None