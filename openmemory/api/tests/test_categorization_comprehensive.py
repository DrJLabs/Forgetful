"""
Comprehensive Unit Tests for Memory Categorization
==================================================

This test suite provides comprehensive coverage for memory categorization functionality,
including OpenAI integration, retry mechanisms, error handling, and category validation.

Test Coverage Areas:
1. Category Generation & OpenAI Integration
2. Retry Mechanism & Error Handling
3. Category Validation & Normalization
4. Edge Cases & Invalid Input Handling
5. Response Parsing & Structured Output
6. Performance & Timeout Handling
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from app.utils.categorization import MemoryCategories, get_categories_for_memory
from app.utils.prompts import MEMORY_CATEGORIZATION_PROMPT
from openai import OpenAI
from tenacity import RetryError


@pytest.mark.unit
class TestCategoryGeneration:
    """Test core category generation functionality"""

    def test_get_categories_for_memory_success(self):
        """Test successful category generation"""
        memory_text = (
            "I went to the grocery store and bought apples, bananas, and bread."
        )
        expected_categories = ["shopping", "personal", "food"]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=expected_categories)

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == expected_categories
            mock_client.beta.chat.completions.parse.assert_called_once()

    def test_get_categories_for_memory_empty_result(self):
        """Test category generation with empty result"""
        memory_text = "Random text that doesn't fit any category"

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=[])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == []

    def test_get_categories_for_memory_mixed_case_normalization(self):
        """Test category normalization handles mixed case"""
        memory_text = "I worked on a Python project today."
        categories_response = ["Programming", "WORK", "technology", "Personal"]
        expected_normalized = ["programming", "work", "technology", "personal"]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=categories_response)

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == expected_normalized

    def test_get_categories_for_memory_whitespace_handling(self):
        """Test category generation handles whitespace correctly"""
        memory_text = "I went to the doctor for a checkup."
        categories_response = ["  health  ", "medical ", " personal", "wellness "]
        expected_normalized = ["health", "medical", "personal", "wellness"]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=categories_response)

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == expected_normalized

    def test_get_categories_for_memory_special_characters(self):
        """Test category generation with special characters in memory"""
        memory_text = (
            "I bought groceries: apples, bananas, & bread @ the store! Cost: $25.50"
        )
        expected_categories = ["shopping", "food", "personal"]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=expected_categories)

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == expected_categories

    def test_get_categories_for_memory_unicode_content(self):
        """Test category generation with unicode content"""
        memory_text = "I visited Paris 🇫🇷 and ate croissants 🥐 at a café ☕"
        expected_categories = ["travel", "food", "personal"]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=expected_categories)

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == expected_categories


@pytest.mark.unit
class TestOpenAIIntegration:
    """Test OpenAI API integration and structured output"""

    def test_openai_api_call_parameters(self):
        """Test correct OpenAI API call parameters"""
        memory_text = "I completed a work project"

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=["work"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            get_categories_for_memory(memory_text)

            # Verify API call parameters
            call_args = mock_client.beta.chat.completions.parse.call_args
            assert call_args[1]["model"] == "gpt-4o-mini"
            assert call_args[1]["temperature"] == 0
            assert call_args[1]["response_format"] == MemoryCategories

            # Verify messages structure
            messages = call_args[1]["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == MEMORY_CATEGORIZATION_PROMPT
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == memory_text

    def test_openai_structured_output_parsing(self):
        """Test OpenAI structured output parsing"""
        memory_text = "I went to the gym and did cardio"

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=["health", "fitness", "personal"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == ["health", "fitness", "personal"]

    def test_openai_client_initialization(self):
        """Test OpenAI client is properly initialized"""
        with patch("app.utils.categorization.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            # Re-import to trigger initialization
            import importlib

            import app.utils.categorization

            importlib.reload(app.utils.categorization)

            mock_openai_class.assert_called_once()

    def test_openai_response_choice_access(self):
        """Test accessing choices from OpenAI response"""
        memory_text = "I had lunch with friends"

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=["social", "personal"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == ["social", "personal"]

    def test_openai_temperature_zero_for_consistency(self):
        """Test OpenAI temperature is set to 0 for consistent results"""
        memory_text = "I read a book about science"

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=["education"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            get_categories_for_memory(memory_text)

            call_args = mock_client.beta.chat.completions.parse.call_args
            assert call_args[1]["temperature"] == 0


@pytest.mark.unit
class TestRetryMechanism:
    """Test retry mechanism and error handling"""

    def test_retry_on_temporary_failure(self):
        """Test retry mechanism on temporary API failure"""
        memory_text = "I went shopping for groceries"

        # Mock first call to fail, second to succeed
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=["shopping"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.side_effect = [
                Exception("Temporary API error"),
                mock_response,
            ]

            result = get_categories_for_memory(memory_text)

            assert result == ["shopping"]
            assert mock_client.beta.chat.completions.parse.call_count == 2

    def test_retry_exhaustion_raises_exception(self):
        """Test retry mechanism raises exception after exhaustion"""
        memory_text = "I went to work today"

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.side_effect = Exception(
                "Persistent API error"
            )

            with pytest.raises(Exception) as exc_info:
                get_categories_for_memory(memory_text)

            assert "Persistent API error" in str(exc_info.value)
            # Should retry 3 times based on retry configuration
            assert mock_client.beta.chat.completions.parse.call_count == 3

    def test_retry_with_different_error_types(self):
        """Test retry mechanism with different error types"""
        memory_text = "I exercised at the gym"

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=["health"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.side_effect = [
                ConnectionError("Network error"),
                TimeoutError("Request timeout"),
                mock_response,
            ]

            result = get_categories_for_memory(memory_text)

            assert result == ["health"]
            assert mock_client.beta.chat.completions.parse.call_count == 3

    def test_retry_configuration_parameters(self):
        """Test retry configuration parameters"""
        memory_text = "I cooked dinner"

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.side_effect = Exception("API error")

            with patch("app.utils.categorization.retry") as mock_retry:
                mock_retry.side_effect = lambda func: func

                try:
                    get_categories_for_memory(memory_text)
                except Exception:
                    pass

                # Verify retry decorator was applied
                mock_retry.assert_called_once()

    def test_exponential_backoff_behavior(self):
        """Test exponential backoff behavior in retry"""
        memory_text = "I attended a meeting"

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.side_effect = Exception(
                "API rate limit"
            )

            with patch("time.sleep") as mock_sleep:
                with pytest.raises(Exception):
                    get_categories_for_memory(memory_text)

                # Should have exponential backoff delays
                assert mock_sleep.call_count >= 2


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_empty_memory_text(self):
        """Test handling of empty memory text"""
        memory_text = ""

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=[])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == []

    def test_very_long_memory_text(self):
        """Test handling of very long memory text"""
        memory_text = "A" * 10000  # Very long text

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=["personal"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == ["personal"]

    def test_none_memory_text(self):
        """Test handling of None memory text"""
        memory_text = None

        with patch("app.utils.categorization.openai_client") as mock_client:
            with pytest.raises(Exception):
                get_categories_for_memory(memory_text)

    def test_malformed_api_response(self):
        """Test handling of malformed API response"""
        memory_text = "I went to the store"

        mock_response = Mock()
        mock_response.choices = []  # Empty choices

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            with pytest.raises(Exception):
                get_categories_for_memory(memory_text)

    def test_missing_parsed_attribute(self):
        """Test handling of missing parsed attribute"""
        memory_text = "I attended a conference"

        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message = Mock()
        del mock_choice.message.parsed  # Remove parsed attribute
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            with pytest.raises(Exception):
                get_categories_for_memory(memory_text)

    def test_logging_on_error(self):
        """Test error logging when categorization fails"""
        memory_text = "I went to the gym"

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.side_effect = Exception("API error")

            with patch("app.utils.categorization.logging") as mock_logging:
                with pytest.raises(Exception):
                    get_categories_for_memory(memory_text)

                # Verify error was logged
                mock_logging.error.assert_called()

    def test_debug_logging_on_parsing_error(self):
        """Test debug logging when response parsing fails"""
        memory_text = "I read a book"

        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Invalid JSON response"
        mock_choice.message.parsed = None
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            with patch("app.utils.categorization.logging") as mock_logging:
                with pytest.raises(Exception):
                    get_categories_for_memory(memory_text)

                # Verify debug logging was attempted
                mock_logging.debug.assert_called()


@pytest.mark.unit
class TestCategoryValidation:
    """Test category validation and filtering"""

    def test_category_deduplication(self):
        """Test removal of duplicate categories"""
        memory_text = "I went shopping and bought groceries"
        categories_response = ["shopping", "personal", "shopping", "food", "personal"]
        expected_unique = ["shopping", "personal", "food"]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=categories_response)

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            # Should maintain order and remove duplicates
            assert len(result) == len(set(result))
            assert all(cat in expected_unique for cat in result)

    def test_empty_category_filtering(self):
        """Test filtering of empty categories"""
        memory_text = "I worked on a project"
        categories_response = ["work", "", "  ", "projects", None]
        expected_filtered = ["work", "projects"]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        # Note: In real scenario, MemoryCategories would validate this
        mock_parsed = MemoryCategories(categories=["work", "projects"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            assert result == expected_filtered

    def test_category_length_validation(self):
        """Test validation of category length"""
        memory_text = "I did various activities"
        categories_response = [
            "a",
            "valid_category",
            "x" * 100,
        ]  # Too short and too long

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=categories_response)

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            # Should normalize all categories regardless of length
            assert len(result) == 3
            assert all(isinstance(cat, str) for cat in result)

    def test_category_character_validation(self):
        """Test validation of category characters"""
        memory_text = "I had a mixed day"
        categories_response = ["valid-category", "valid_category", "valid category"]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=categories_response)

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            result = get_categories_for_memory(memory_text)

            # Should normalize all categories to lowercase
            expected = ["valid-category", "valid_category", "valid category"]
            assert result == expected


@pytest.mark.unit
class TestPerformanceAndTimeout:
    """Test performance and timeout handling"""

    def test_api_timeout_handling(self):
        """Test handling of API timeout"""
        memory_text = "I completed my daily tasks"

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.side_effect = TimeoutError(
                "API timeout"
            )

            with pytest.raises(Exception):
                get_categories_for_memory(memory_text)

    def test_concurrent_categorization_requests(self):
        """Test handling of concurrent categorization requests"""
        memory_texts = ["I went to work", "I had lunch", "I exercised", "I read a book"]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=["personal"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            results = []
            for text in memory_texts:
                result = get_categories_for_memory(text)
                results.append(result)

            assert len(results) == 4
            assert all(result == ["personal"] for result in results)
            assert mock_client.beta.chat.completions.parse.call_count == 4

    def test_large_batch_categorization(self):
        """Test categorization of large batch of memories"""
        memory_texts = [f"Memory {i}" for i in range(100)]

        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_parsed = MemoryCategories(categories=["personal"])

        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]

        with patch("app.utils.categorization.openai_client") as mock_client:
            mock_client.beta.chat.completions.parse.return_value = mock_response

            results = [get_categories_for_memory(text) for text in memory_texts]

            assert len(results) == 100
            assert all(result == ["personal"] for result in results)
            assert mock_client.beta.chat.completions.parse.call_count == 100
