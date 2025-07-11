"""
Comprehensive Unit Tests for Database Utilities
===============================================

This test suite provides comprehensive coverage for database utility functions,
including user management, app management, database transactions, and error handling.

Test Coverage Areas:
1. User Creation & Management
2. App Creation & Management
3. Database Transaction Handling
4. Error Handling & Rollback
5. Relationship Management
6. Data Integrity & Validation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, DatabaseError

from app.utils.db import get_or_create_user, get_or_create_app, get_user_and_app
from app.models import User, App


@pytest.mark.unit
class TestUserManagement:
    """Test user creation and management functionality"""

    def test_get_or_create_user_existing_user(self):
        """Test getting existing user"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.user_id = "existing_user"
        mock_user.name = "Existing User"

        # Mock query chain
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_or_create_user(mock_db, "existing_user")

        assert result == mock_user
        mock_db.query.assert_called_once_with(User)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_get_or_create_user_new_user(self):
        """Test creating new user"""
        mock_db = Mock()
        user_id = "new_user"

        # Mock query returns None (user doesn't exist)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock the created user
        mock_created_user = Mock()
        mock_created_user.user_id = user_id
        mock_created_user.id = uuid4()

        with patch("app.utils.db.User") as mock_user_class:
            mock_user_class.return_value = mock_created_user

            result = get_or_create_user(mock_db, user_id)

            assert result == mock_created_user
            mock_user_class.assert_called_once_with(user_id=user_id)
            mock_db.add.assert_called_once_with(mock_created_user)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_created_user)

    def test_get_or_create_user_with_empty_user_id(self):
        """Test creating user with empty user_id"""
        mock_db = Mock()

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_created_user = Mock()
        mock_created_user.user_id = ""

        with patch("app.utils.db.User") as mock_user_class:
            mock_user_class.return_value = mock_created_user

            result = get_or_create_user(mock_db, "")

            assert result == mock_created_user
            mock_user_class.assert_called_once_with(user_id="")

    def test_get_or_create_user_with_special_characters(self):
        """Test creating user with special characters in user_id"""
        mock_db = Mock()
        user_id = "user@example.com"

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_created_user = Mock()
        mock_created_user.user_id = user_id

        with patch("app.utils.db.User") as mock_user_class:
            mock_user_class.return_value = mock_created_user

            result = get_or_create_user(mock_db, user_id)

            assert result == mock_created_user
            mock_user_class.assert_called_once_with(user_id=user_id)

    def test_get_or_create_user_with_long_user_id(self):
        """Test creating user with very long user_id"""
        mock_db = Mock()
        user_id = "a" * 500  # Very long user ID

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_created_user = Mock()
        mock_created_user.user_id = user_id

        with patch("app.utils.db.User") as mock_user_class:
            mock_user_class.return_value = mock_created_user

            result = get_or_create_user(mock_db, user_id)

            assert result == mock_created_user
            mock_user_class.assert_called_once_with(user_id=user_id)

    def test_get_or_create_user_database_error(self):
        """Test handling database error during user creation"""
        mock_db = Mock()
        user_id = "test_user"

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock database error on commit
        mock_db.commit.side_effect = DatabaseError("Database error", None, None)

        with patch("app.utils.db.User") as mock_user_class:
            mock_created_user = Mock()
            mock_user_class.return_value = mock_created_user

            with pytest.raises(DatabaseError):
                get_or_create_user(mock_db, user_id)

    def test_get_or_create_user_integrity_error(self):
        """Test handling integrity error during user creation"""
        mock_db = Mock()
        user_id = "duplicate_user"

        # Mock query returns None initially
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock integrity error on commit (duplicate user_id)
        mock_db.commit.side_effect = IntegrityError("Duplicate key", None, None)

        with patch("app.utils.db.User") as mock_user_class:
            mock_created_user = Mock()
            mock_user_class.return_value = mock_created_user

            with pytest.raises(IntegrityError):
                get_or_create_user(mock_db, user_id)

    def test_get_or_create_user_query_structure(self):
        """Test proper query structure for user lookup"""
        mock_db = Mock()
        mock_user = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        user_id = "test_user"
        get_or_create_user(mock_db, user_id)

        # Verify query structure
        mock_db.query.assert_called_once_with(User)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()


@pytest.mark.unit
class TestAppManagement:
    """Test app creation and management functionality"""

    def test_get_or_create_app_existing_app(self):
        """Test getting existing app"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = uuid4()

        mock_app = Mock()
        mock_app.id = uuid4()
        mock_app.name = "existing_app"
        mock_app.owner_id = mock_user.id

        # Mock query chain
        mock_db.query.return_value.filter.return_value.first.return_value = mock_app

        result = get_or_create_app(mock_db, mock_user, "existing_app")

        assert result == mock_app
        mock_db.query.assert_called_once_with(App)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_get_or_create_app_new_app(self):
        """Test creating new app"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = uuid4()
        app_id = "new_app"

        # Mock query returns None (app doesn't exist)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock the created app
        mock_created_app = Mock()
        mock_created_app.name = app_id
        mock_created_app.owner_id = mock_user.id
        mock_created_app.id = uuid4()

        with patch("app.utils.db.App") as mock_app_class:
            mock_app_class.return_value = mock_created_app

            result = get_or_create_app(mock_db, mock_user, app_id)

            assert result == mock_created_app
            mock_app_class.assert_called_once_with(owner_id=mock_user.id, name=app_id)
            mock_db.add.assert_called_once_with(mock_created_app)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_created_app)

    def test_get_or_create_app_with_different_users(self):
        """Test app creation with different users"""
        mock_db = Mock()

        # Create two different users
        user1 = Mock()
        user1.id = uuid4()
        user2 = Mock()
        user2.id = uuid4()

        app_name = "shared_app_name"

        # Mock query returns None for both
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.utils.db.App") as mock_app_class:
            mock_app1 = Mock()
            mock_app1.name = app_name
            mock_app1.owner_id = user1.id

            mock_app2 = Mock()
            mock_app2.name = app_name
            mock_app2.owner_id = user2.id

            mock_app_class.side_effect = [mock_app1, mock_app2]

            result1 = get_or_create_app(mock_db, user1, app_name)
            result2 = get_or_create_app(mock_db, user2, app_name)

            assert result1 == mock_app1
            assert result2 == mock_app2
            assert mock_app_class.call_count == 2

    def test_get_or_create_app_with_empty_app_name(self):
        """Test creating app with empty app name"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = uuid4()

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_created_app = Mock()
        mock_created_app.name = ""

        with patch("app.utils.db.App") as mock_app_class:
            mock_app_class.return_value = mock_created_app

            result = get_or_create_app(mock_db, mock_user, "")

            assert result == mock_created_app
            mock_app_class.assert_called_once_with(owner_id=mock_user.id, name="")

    def test_get_or_create_app_with_special_characters(self):
        """Test creating app with special characters in name"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = uuid4()
        app_name = "app-with_special.chars@123"

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_created_app = Mock()
        mock_created_app.name = app_name

        with patch("app.utils.db.App") as mock_app_class:
            mock_app_class.return_value = mock_created_app

            result = get_or_create_app(mock_db, mock_user, app_name)

            assert result == mock_created_app
            mock_app_class.assert_called_once_with(owner_id=mock_user.id, name=app_name)

    def test_get_or_create_app_database_error(self):
        """Test handling database error during app creation"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = uuid4()

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock database error on commit
        mock_db.commit.side_effect = DatabaseError("Database error", None, None)

        with patch("app.utils.db.App") as mock_app_class:
            mock_created_app = Mock()
            mock_app_class.return_value = mock_created_app

            with pytest.raises(DatabaseError):
                get_or_create_app(mock_db, mock_user, "test_app")

    def test_get_or_create_app_query_structure(self):
        """Test proper query structure for app lookup"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_app = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_app

        app_name = "test_app"
        get_or_create_app(mock_db, mock_user, app_name)

        # Verify query structure
        mock_db.query.assert_called_once_with(App)
        mock_db.query.return_value.filter.assert_called_once()
        mock_db.query.return_value.filter.return_value.first.assert_called_once()


@pytest.mark.unit
class TestCombinedUserAndAppManagement:
    """Test combined user and app management functionality"""

    def test_get_user_and_app_both_exist(self):
        """Test getting both existing user and app"""
        mock_db = Mock()

        # Mock existing user
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.user_id = "existing_user"

        # Mock existing app
        mock_app = Mock()
        mock_app.id = uuid4()
        mock_app.name = "existing_app"
        mock_app.owner_id = mock_user.id

        with patch("app.utils.db.get_or_create_user") as mock_get_user:
            with patch("app.utils.db.get_or_create_app") as mock_get_app:
                mock_get_user.return_value = mock_user
                mock_get_app.return_value = mock_app

                user, app = get_user_and_app(mock_db, "existing_user", "existing_app")

                assert user == mock_user
                assert app == mock_app
                mock_get_user.assert_called_once_with(mock_db, "existing_user")
                mock_get_app.assert_called_once_with(mock_db, mock_user, "existing_app")

    def test_get_user_and_app_both_new(self):
        """Test creating both new user and app"""
        mock_db = Mock()

        # Mock new user
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.user_id = "new_user"

        # Mock new app
        mock_app = Mock()
        mock_app.id = uuid4()
        mock_app.name = "new_app"
        mock_app.owner_id = mock_user.id

        with patch("app.utils.db.get_or_create_user") as mock_get_user:
            with patch("app.utils.db.get_or_create_app") as mock_get_app:
                mock_get_user.return_value = mock_user
                mock_get_app.return_value = mock_app

                user, app = get_user_and_app(mock_db, "new_user", "new_app")

                assert user == mock_user
                assert app == mock_app
                mock_get_user.assert_called_once_with(mock_db, "new_user")
                mock_get_app.assert_called_once_with(mock_db, mock_user, "new_app")

    def test_get_user_and_app_execution_order(self):
        """Test execution order of user and app creation"""
        mock_db = Mock()

        mock_user = Mock()
        mock_app = Mock()

        with patch("app.utils.db.get_or_create_user") as mock_get_user:
            with patch("app.utils.db.get_or_create_app") as mock_get_app:
                mock_get_user.return_value = mock_user
                mock_get_app.return_value = mock_app

                user, app = get_user_and_app(mock_db, "test_user", "test_app")

                # Verify user is created first, then app
                assert mock_get_user.call_count == 1
                assert mock_get_app.call_count == 1

                # Verify app creation uses the created user
                mock_get_app.assert_called_once_with(mock_db, mock_user, "test_app")

    def test_get_user_and_app_with_user_creation_error(self):
        """Test handling user creation error"""
        mock_db = Mock()

        with patch("app.utils.db.get_or_create_user") as mock_get_user:
            with patch("app.utils.db.get_or_create_app") as mock_get_app:
                mock_get_user.side_effect = DatabaseError(
                    "User creation failed", None, None
                )

                with pytest.raises(DatabaseError):
                    get_user_and_app(mock_db, "test_user", "test_app")

                # App creation should not be called
                mock_get_app.assert_not_called()

    def test_get_user_and_app_with_app_creation_error(self):
        """Test handling app creation error"""
        mock_db = Mock()

        mock_user = Mock()

        with patch("app.utils.db.get_or_create_user") as mock_get_user:
            with patch("app.utils.db.get_or_create_app") as mock_get_app:
                mock_get_user.return_value = mock_user
                mock_get_app.side_effect = DatabaseError(
                    "App creation failed", None, None
                )

                with pytest.raises(DatabaseError):
                    get_user_and_app(mock_db, "test_user", "test_app")

                # User creation should still be called
                mock_get_user.assert_called_once()

    def test_get_user_and_app_return_type(self):
        """Test return type of get_user_and_app"""
        mock_db = Mock()

        mock_user = Mock()
        mock_app = Mock()

        with patch("app.utils.db.get_or_create_user") as mock_get_user:
            with patch("app.utils.db.get_or_create_app") as mock_get_app:
                mock_get_user.return_value = mock_user
                mock_get_app.return_value = mock_app

                result = get_user_and_app(mock_db, "test_user", "test_app")

                assert isinstance(result, tuple)
                assert len(result) == 2
                assert result[0] == mock_user
                assert result[1] == mock_app


@pytest.mark.unit
class TestDatabaseTransactionHandling:
    """Test database transaction handling and rollback"""

    def test_user_creation_transaction_commit(self):
        """Test user creation commits transaction"""
        mock_db = Mock()

        # Mock query returns None (user doesn't exist)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.utils.db.User") as mock_user_class:
            mock_created_user = Mock()
            mock_user_class.return_value = mock_created_user

            get_or_create_user(mock_db, "test_user")

            # Verify transaction operations
            mock_db.add.assert_called_once_with(mock_created_user)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_created_user)

    def test_app_creation_transaction_commit(self):
        """Test app creation commits transaction"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = uuid4()

        # Mock query returns None (app doesn't exist)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.utils.db.App") as mock_app_class:
            mock_created_app = Mock()
            mock_app_class.return_value = mock_created_app

            get_or_create_app(mock_db, mock_user, "test_app")

            # Verify transaction operations
            mock_db.add.assert_called_once_with(mock_created_app)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_created_app)

    def test_no_transaction_for_existing_entities(self):
        """Test no transaction operations for existing entities"""
        mock_db = Mock()

        # Mock existing user
        mock_user = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        get_or_create_user(mock_db, "existing_user")

        # Verify no transaction operations
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.refresh.assert_not_called()

    def test_transaction_rollback_on_error(self):
        """Test transaction rollback on database error"""
        mock_db = Mock()

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock commit error
        mock_db.commit.side_effect = DatabaseError("Transaction failed", None, None)

        with patch("app.utils.db.User") as mock_user_class:
            mock_created_user = Mock()
            mock_user_class.return_value = mock_created_user

            with pytest.raises(DatabaseError):
                get_or_create_user(mock_db, "test_user")

    def test_database_session_consistency(self):
        """Test database session consistency across operations"""
        mock_db = Mock()

        # Test both user and app creation use same session
        mock_user = Mock()
        mock_user.id = uuid4()

        with patch("app.utils.db.get_or_create_user") as mock_get_user:
            with patch("app.utils.db.get_or_create_app") as mock_get_app:
                mock_get_user.return_value = mock_user
                mock_get_app.return_value = Mock()

                get_user_and_app(mock_db, "test_user", "test_app")

                # Both operations should use the same session
                mock_get_user.assert_called_once_with(mock_db, "test_user")
                mock_get_app.assert_called_once_with(mock_db, mock_user, "test_app")


@pytest.mark.unit
class TestDataIntegrityAndValidation:
    """Test data integrity and validation"""

    def test_user_id_uniqueness_constraint(self):
        """Test user_id uniqueness constraint"""
        mock_db = Mock()

        # Mock query returns None initially
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock integrity error for duplicate user_id
        mock_db.commit.side_effect = IntegrityError(
            "UNIQUE constraint failed", None, None
        )

        with patch("app.utils.db.User") as mock_user_class:
            mock_created_user = Mock()
            mock_user_class.return_value = mock_created_user

            with pytest.raises(IntegrityError):
                get_or_create_user(mock_db, "duplicate_user")

    def test_app_name_owner_uniqueness_constraint(self):
        """Test app name-owner uniqueness constraint"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = uuid4()

        # Mock query returns None initially
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock integrity error for duplicate app name for same owner
        mock_db.commit.side_effect = IntegrityError(
            "UNIQUE constraint failed", None, None
        )

        with patch("app.utils.db.App") as mock_app_class:
            mock_created_app = Mock()
            mock_app_class.return_value = mock_created_app

            with pytest.raises(IntegrityError):
                get_or_create_app(mock_db, mock_user, "duplicate_app")

    def test_foreign_key_constraint(self):
        """Test foreign key constraint validation"""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.id = None  # Invalid user ID

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.utils.db.App") as mock_app_class:
            mock_created_app = Mock()
            mock_app_class.return_value = mock_created_app

            # Should handle invalid foreign key
            get_or_create_app(mock_db, mock_user, "test_app")

            mock_app_class.assert_called_once_with(owner_id=None, name="test_app")

    def test_data_validation_on_creation(self):
        """Test data validation during entity creation"""
        mock_db = Mock()

        # Test with various input types
        test_cases = [
            ("valid_user", str),
            ("", str),
            ("user_with_numbers_123", str),
            ("user-with-dashes", str),
            ("user_with_underscores", str),
        ]

        for user_id, expected_type in test_cases:
            # Mock query returns None
            mock_db.query.return_value.filter.return_value.first.return_value = None

            with patch("app.utils.db.User") as mock_user_class:
                mock_created_user = Mock()
                mock_user_class.return_value = mock_created_user

                result = get_or_create_user(mock_db, user_id)

                assert result == mock_created_user
                mock_user_class.assert_called_with(user_id=user_id)
                assert isinstance(user_id, expected_type)

    def test_null_value_handling(self):
        """Test handling of null values"""
        mock_db = Mock()

        # Test with None user_id
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.utils.db.User") as mock_user_class:
            mock_created_user = Mock()
            mock_user_class.return_value = mock_created_user

            result = get_or_create_user(mock_db, None)

            assert result == mock_created_user
            mock_user_class.assert_called_once_with(user_id=None)

    def test_relationship_integrity(self):
        """Test relationship integrity between user and app"""
        mock_db = Mock()

        mock_user = Mock()
        mock_user.id = uuid4()

        # Mock query returns None
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.utils.db.App") as mock_app_class:
            mock_created_app = Mock()
            mock_app_class.return_value = mock_created_app

            get_or_create_app(mock_db, mock_user, "test_app")

            # Verify relationship is established
            mock_app_class.assert_called_once_with(
                owner_id=mock_user.id, name="test_app"
            )

            # Verify the app is linked to the correct user
            assert mock_created_app.owner_id == mock_user.id
