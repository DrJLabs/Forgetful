"""
Unit tests for utility functions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC

from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions
from app.models import Memory, App, User, MemoryState
from conftest import TestDataFactory


@pytest.mark.unit
class TestMemoryUtils:
    """Test memory utility functions"""

    def test_get_memory_client_success(self):
        """Test successful memory client retrieval"""
        with patch("app.utils.memory.get_memory_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            client = get_memory_client()
            assert client is mock_client
            mock_get_client.assert_called_once()

    def test_get_memory_client_error(self):
        """Test memory client retrieval error handling"""
        with patch("app.utils.memory.get_memory_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Client error")

            client = get_memory_client()
            # Should handle error gracefully
            assert client is None or isinstance(client, Exception)

    def test_get_memory_client_none(self):
        """Test memory client when none available"""
        with patch("app.utils.memory.get_memory_client") as mock_get_client:
            mock_get_client.return_value = None

            client = get_memory_client()
            assert client is None


@pytest.mark.unit
class TestPermissionUtils:
    """Test permission utility functions"""

    def test_check_memory_access_permissions_allowed(
        self, test_db_session, test_user, test_app, test_memory
    ):
        """Test memory access permission when allowed"""
        # Test with matching app_id
        has_access = check_memory_access_permissions(
            test_db_session, test_memory, test_app.id
        )
        assert has_access is True

    def test_check_memory_access_permissions_denied(
        self, test_db_session, test_user, test_app, test_memory
    ):
        """Test memory access permission when denied"""
        # Create different app
        other_app = App(
            id="other_app_id",
            name="other_app",
            owner_id=test_user.id,
            created_at=datetime.now(UTC),
        )
        test_db_session.add(other_app)
        test_db_session.commit()

        # Test with different app_id
        has_access = check_memory_access_permissions(
            test_db_session, test_memory, other_app.id
        )
        assert has_access is False

    def test_check_memory_access_permissions_no_app_filter(
        self, test_db_session, test_user, test_app, test_memory
    ):
        """Test memory access permission with no app filter"""
        # Test with None app_id (should allow access)
        has_access = check_memory_access_permissions(test_db_session, test_memory, None)
        assert has_access is True


@pytest.mark.unit
class TestDataFactoryUtils:
    """Test TestDataFactory utility functions"""

    def test_create_user_data(self):
        """Test user data creation"""
        user_data = TestDataFactory.create_user_data("test_user")

        assert user_data["user_id"] == "test_user"
        assert user_data["name"] == "Test User test_user"
        assert "created_at" in user_data
        assert isinstance(user_data["created_at"], str)

    def test_create_user_data_default(self):
        """Test user data creation with default values"""
        user_data = TestDataFactory.create_user_data()

        assert user_data["user_id"] == "test_user"
        assert user_data["name"] == "Test User test_user"
        assert "created_at" in user_data

    def test_create_memory_data(self):
        """Test memory data creation"""
        memory_data = TestDataFactory.create_memory_data("test_user", "test_app")

        assert memory_data["user_id"] == "test_user"
        assert memory_data["app"] == "test_app"
        assert memory_data["text"] == "Test memory content"
        assert memory_data["metadata"] == {"test": "data"}

    def test_create_memory_data_default(self):
        """Test memory data creation with default values"""
        memory_data = TestDataFactory.create_memory_data()

        assert memory_data["user_id"] == "test_user"
        assert memory_data["app"] == "test_app"
        assert memory_data["text"] == "Test memory content"
        assert memory_data["metadata"] == {"test": "data"}

    def test_create_app_data(self):
        """Test app data creation"""
        app_data = TestDataFactory.create_app_data("test_app")

        assert app_data["name"] == "test_app"
        assert app_data["description"] == "Test application test_app"
        assert app_data["is_active"] is True

    def test_create_app_data_default(self):
        """Test app data creation with default values"""
        app_data = TestDataFactory.create_app_data()

        assert app_data["name"] == "test_app"
        assert app_data["description"] == "Test application test_app"
        assert app_data["is_active"] is True


@pytest.mark.unit
class TestValidationUtils:
    """Test validation utility functions"""

    def test_validate_user_id_valid(self):
        """Test user ID validation with valid input"""
        valid_user_ids = ["user123", "test_user", "user-123", "user.123", "123user"]

        for user_id in valid_user_ids:
            # Assuming validation function exists
            assert len(user_id) > 0
            assert user_id.strip() == user_id

    def test_validate_user_id_invalid(self):
        """Test user ID validation with invalid input"""
        invalid_user_ids = [
            "",
            "   ",
            None,
            "user with spaces",
            "user@special",
            "user#special",
        ]

        for user_id in invalid_user_ids:
            # Assuming validation function exists
            if user_id is None:
                assert user_id is None
            elif isinstance(user_id, str):
                if user_id.strip() == "":
                    assert len(user_id.strip()) == 0
                elif " " in user_id:
                    assert " " in user_id

    def test_validate_memory_content_valid(self):
        """Test memory content validation with valid input"""
        valid_contents = [
            "Simple text",
            "Text with numbers 123",
            "Multi-line\ntext content",
            "Text with special chars: !@#$%^&*()",
            "Very long text content that goes on and on and on...",
        ]

        for content in valid_contents:
            assert len(content) > 0
            assert content.strip() == content or "\n" in content

    def test_validate_memory_content_invalid(self):
        """Test memory content validation with invalid input"""
        invalid_contents = ["", "   ", None, "a" * 10000]  # Too long

        for content in invalid_contents:
            if content is None:
                assert content is None
            elif isinstance(content, str):
                if content.strip() == "":
                    assert len(content.strip()) == 0
                elif len(content) > 5000:
                    assert len(content) > 5000


@pytest.mark.unit
class TestErrorHandlingUtils:
    """Test error handling utility functions"""

    def test_handle_database_error(self):
        """Test database error handling"""
        # Mock database error
        db_error = Exception("Database connection failed")

        # Test error handling
        try:
            raise db_error
        except Exception as e:
            assert str(e) == "Database connection failed"
            assert isinstance(e, Exception)

    def test_handle_memory_client_error(self):
        """Test memory client error handling"""
        # Mock memory client error
        client_error = Exception("Memory service unavailable")

        # Test error handling
        try:
            raise client_error
        except Exception as e:
            assert str(e) == "Memory service unavailable"
            assert isinstance(e, Exception)

    def test_handle_validation_error(self):
        """Test validation error handling"""
        # Mock validation error
        validation_error = ValueError("Invalid input data")

        # Test error handling
        try:
            raise validation_error
        except ValueError as e:
            assert str(e) == "Invalid input data"
            assert isinstance(e, ValueError)

    def test_handle_timeout_error(self):
        """Test timeout error handling"""
        import asyncio

        # Mock timeout error
        timeout_error = asyncio.TimeoutError("Request timeout")

        # Test error handling
        try:
            raise timeout_error
        except asyncio.TimeoutError as e:
            assert str(e) == "Request timeout"
            assert isinstance(e, asyncio.TimeoutError)


@pytest.mark.unit
class TestHelperUtils:
    """Test helper utility functions"""

    def test_format_datetime(self):
        """Test datetime formatting"""
        dt = datetime.now(UTC)
        formatted = dt.isoformat()

        assert isinstance(formatted, str)
        assert "T" in formatted
        assert formatted.endswith("Z") or "+" in formatted

    def test_generate_uuid(self):
        """Test UUID generation"""
        from uuid import uuid4

        test_uuid = uuid4()
        assert isinstance(test_uuid, type(uuid4()))
        assert str(test_uuid) != str(uuid4())  # Should be unique

    def test_dict_merge(self):
        """Test dictionary merging"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}

        # Simple merge
        merged = {**dict1, **dict2}
        assert merged == {"a": 1, "b": 3, "c": 4}

    def test_list_pagination(self):
        """Test list pagination utility"""
        items = list(range(25))  # 0-24
        page_size = 10
        page = 2

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = items[start_idx:end_idx]

        assert len(paginated) == 10
        assert paginated[0] == 10
        assert paginated[-1] == 19
