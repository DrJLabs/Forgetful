"""
Unit tests for database models
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from app.models import User, App, Memory, MemoryState, Category, MemoryAccessLog
from app.database import Base


@pytest.mark.unit
class TestUserModel:
    """Test User model"""
    
    def test_user_creation(self, test_db_session):
        """Test creating a new user"""
        user = User(
            id=uuid4(),
            user_id="test_user",
            name="Test User",
            created_at=datetime.now(UTC)
        )
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        
        assert user.id is not None
        assert user.user_id == "test_user"
        assert user.name == "Test User"
        assert user.created_at is not None
    
    def test_user_unique_constraint(self, test_db_session):
        """Test user_id unique constraint"""
        user1 = User(
            id=uuid4(),
            user_id="duplicate_user",
            name="User 1",
            created_at=datetime.now(UTC)
        )
        user2 = User(
            id=uuid4(),
            user_id="duplicate_user",
            name="User 2",
            created_at=datetime.now(UTC)
        )
        
        test_db_session.add(user1)
        test_db_session.commit()
        
        test_db_session.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_db_session.commit()


@pytest.mark.unit
class TestAppModel:
    """Test App model"""
    
    def test_app_creation(self, test_db_session, test_user):
        """Test creating a new app"""
        app = App(
            id=uuid4(),
            name="test_app",
            owner_id=test_user.id,
            is_active=True,
            created_at=datetime.now(UTC)
        )
        test_db_session.add(app)
        test_db_session.commit()
        test_db_session.refresh(app)
        
        assert app.id is not None
        assert app.name == "test_app"
        assert app.owner_id == test_user.id
        assert app.is_active is True
        assert app.created_at is not None
    
    def test_app_user_relationship(self, test_db_session, test_user):
        """Test app-user relationship"""
        app = App(
            id=uuid4(),
            name="test_app",
            owner_id=test_user.id,
            is_active=True,
            created_at=datetime.now(UTC)
        )
        test_db_session.add(app)
        test_db_session.commit()
        
        # Test relationship
        assert app.owner == test_user
        assert app in test_user.apps
    
    def test_app_default_values(self, test_db_session, test_user):
        """Test app default values"""
        app = App(
            id=uuid4(),
            name="test_app",
            owner_id=test_user.id,
            created_at=datetime.now(UTC)
        )
        test_db_session.add(app)
        test_db_session.commit()
        
        assert app.is_active is True  # Default value


@pytest.mark.unit
class TestMemoryModel:
    """Test Memory model"""
    
    def test_memory_creation(self, test_db_session, test_user, test_app):
        """Test creating a new memory"""
        memory = Memory(
            id=uuid4(),
            content="Test memory content",
            user_id=test_user.id,
            app_id=test_app.id,
            state=MemoryState.active,
            created_at=datetime.now(UTC),
            metadata_={"test": "data"}
        )
        test_db_session.add(memory)
        test_db_session.commit()
        test_db_session.refresh(memory)
        
        assert memory.id is not None
        assert memory.content == "Test memory content"
        assert memory.user_id == test_user.id
        assert memory.app_id == test_app.id
        assert memory.state == MemoryState.active
        assert memory.metadata_ == {"test": "data"}
    
    def test_memory_relationships(self, test_db_session, test_user, test_app):
        """Test memory relationships"""
        memory = Memory(
            id=uuid4(),
            content="Test memory content",
            user_id=test_user.id,
            app_id=test_app.id,
            state=MemoryState.active,
            created_at=datetime.now(UTC)
        )
        test_db_session.add(memory)
        test_db_session.commit()
        
        # Test relationships
        assert memory.user == test_user
        assert memory.app == test_app
        assert memory in test_user.memories
        assert memory in test_app.memories
    
    def test_memory_state_enum(self, test_db_session, test_user, test_app):
        """Test memory state enumeration"""
        memory = Memory(
            id=uuid4(),
            content="Test memory content",
            user_id=test_user.id,
            app_id=test_app.id,
            state=MemoryState.paused,
            created_at=datetime.now(UTC)
        )
        test_db_session.add(memory)
        test_db_session.commit()
        
        assert memory.state == MemoryState.paused
        assert memory.state.value == "paused"
    
    def test_memory_default_values(self, test_db_session, test_user, test_app):
        """Test memory default values"""
        memory = Memory(
            id=uuid4(),
            content="Test memory content",
            user_id=test_user.id,
            app_id=test_app.id,
            created_at=datetime.now(UTC)
        )
        test_db_session.add(memory)
        test_db_session.commit()
        
        assert memory.state == MemoryState.active  # Default value
        assert memory.metadata_ == {}  # Default empty dict


@pytest.mark.unit
class TestCategoryModel:
    """Test Category model"""
    
    def test_category_creation(self, test_db_session):
        """Test creating a new category"""
        category = Category(
            id=uuid4(),
            name="test_category",
            created_at=datetime.now(UTC)
        )
        test_db_session.add(category)
        test_db_session.commit()
        test_db_session.refresh(category)
        
        assert category.id is not None
        assert category.name == "test_category"
        assert category.created_at is not None
    
    def test_category_memory_relationship(self, test_db_session, test_user, test_app):
        """Test category-memory many-to-many relationship"""
        category = Category(
            id=uuid4(),
            name="test_category",
            created_at=datetime.now(UTC)
        )
        memory = Memory(
            id=uuid4(),
            content="Test memory content",
            user_id=test_user.id,
            app_id=test_app.id,
            state=MemoryState.active,
            created_at=datetime.now(UTC)
        )
        
        # Add category to memory
        memory.categories.append(category)
        
        test_db_session.add(category)
        test_db_session.add(memory)
        test_db_session.commit()
        
        # Test relationship
        assert category in memory.categories
        assert memory in category.memories


@pytest.mark.unit
class TestMemoryAccessLogModel:
    """Test MemoryAccessLog model"""
    
    def test_access_log_creation(self, test_db_session, test_user, test_app, test_memory):
        """Test creating a memory access log"""
        access_log = MemoryAccessLog(
            id=uuid4(),
            memory_id=test_memory.id,
            user_id=test_user.id,
            app_id=test_app.id,
            accessed_at=datetime.now(UTC),
            access_type="read"
        )
        test_db_session.add(access_log)
        test_db_session.commit()
        test_db_session.refresh(access_log)
        
        assert access_log.id is not None
        assert access_log.memory_id == test_memory.id
        assert access_log.user_id == test_user.id
        assert access_log.app_id == test_app.id
        assert access_log.access_type == "read"
    
    def test_access_log_relationships(self, test_db_session, test_user, test_app, test_memory):
        """Test access log relationships"""
        access_log = MemoryAccessLog(
            id=uuid4(),
            memory_id=test_memory.id,
            user_id=test_user.id,
            app_id=test_app.id,
            accessed_at=datetime.now(UTC),
            access_type="read"
        )
        test_db_session.add(access_log)
        test_db_session.commit()
        
        # Test relationships
        assert access_log.memory == test_memory
        assert access_log.user == test_user
        assert access_log.app == test_app
    
    def test_access_log_default_values(self, test_db_session, test_user, test_app, test_memory):
        """Test access log default values"""
        access_log = MemoryAccessLog(
            id=uuid4(),
            memory_id=test_memory.id,
            user_id=test_user.id,
            app_id=test_app.id,
            accessed_at=datetime.now(UTC)
        )
        test_db_session.add(access_log)
        test_db_session.commit()
        
        assert access_log.access_type == "read"  # Default value 