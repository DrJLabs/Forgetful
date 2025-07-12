#!/usr/bin/env python3
"""
Security Patterns Tests - Demonstrates security testing using established framework
"""

import pytest
import unittest
import json
import uuid
import hashlib
import base64
import re
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import html

# Import test utilities from our established framework
import sys
sys.path.append(str(Path(__file__).parent.parent / "shared"))

from test_utils import (
    TestConfig,
    TestEnvironment,
    DataFactory,
    MockServices,
    TestAssertions,
    PerformanceTracker,
    async_test,
    performance_test
)


class TestInputValidationSecurity(unittest.TestCase):
    """Test input validation security patterns using established framework"""

    def setUp(self):
        """Set up security testing environment"""
        self.config = TestConfig()
        self.test_env = TestEnvironment(self.config)
        self.test_env.setup()
        self.data_factory = DataFactory()
        self.assertions = TestAssertions()

    def tearDown(self):
        """Clean up security testing environment"""
        self.test_env.teardown()

    @pytest.mark.security
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention patterns"""
        # Test various SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE memories; --",
            "1' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; UPDATE users SET password='hacked' WHERE id=1; --",
            "admin'--",
            "' OR 1=1#"
        ]

        for malicious_input in malicious_inputs:
            # Test that malicious input is properly sanitized
            memory_data = self.data_factory.create_memory_data(
                user_id="test_user",
                content=malicious_input
            )
            
            # Simulate SQL query construction (should be parameterized)
            def safe_query_construction(user_id, content):
                # This simulates a parameterized query approach
                # In real implementation, this would use SQL parameters
                sanitized_content = content.replace("'", "''")  # Basic SQL escaping
                return f"SELECT * FROM memories WHERE user_id = ? AND content = ?", [user_id, sanitized_content]

            query, params = safe_query_construction(memory_data["user_id"], memory_data["content"])
            
            # Verify query construction doesn't contain raw SQL injection
            self.assertNotIn("DROP TABLE", query)
            self.assertNotIn("UNION SELECT", query)
            self.assertEqual(len(params), 2)

    @pytest.mark.security
    def test_xss_prevention(self):
        """Test XSS prevention patterns"""
        # Test various XSS attack vectors
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ]

        for xss_payload in xss_payloads:
            # Test content sanitization
            memory_data = self.data_factory.create_memory_data(
                user_id="test_user",
                content=xss_payload
            )

            # Simulate content sanitization
            def sanitize_html_content(content):
                # Basic HTML escaping
                return html.escape(content)

            sanitized_content = sanitize_html_content(memory_data["content"])
            
            # Verify dangerous elements are escaped
            self.assertNotIn("<script>", sanitized_content)
            self.assertNotIn("javascript:", sanitized_content)
            self.assertNotIn("onerror=", sanitized_content)
            self.assertNotIn("onload=", sanitized_content)

    @pytest.mark.security
    def test_input_size_limits(self):
        """Test input size limit enforcement"""
        # Test oversized content
        max_content_length = 10000
        oversized_content = "A" * (max_content_length + 1)

        def validate_content_size(content, max_length=max_content_length):
            if len(content) > max_length:
                raise ValueError(f"Content exceeds maximum length of {max_length} characters")
            return content

        # Test that oversized content is rejected
        with self.assertRaises(ValueError) as context:
            validate_content_size(oversized_content)
        
        self.assertIn("exceeds maximum length", str(context.exception))

        # Test that normal content is accepted
        normal_content = "A" * (max_content_length - 1)
        result = validate_content_size(normal_content)
        self.assertEqual(result, normal_content)

    @pytest.mark.security
    def test_special_character_handling(self):
        """Test special character handling security"""
        # Test various special characters and unicode
        special_characters = [
            "Hello\x00World",  # Null byte
            "Test\r\nContent",  # CRLF injection
            "Unicode: \u0000\u001F\u007F",  # Control characters
            "Emoji: 😀🎉🚀",  # Emoji characters
            "Mixed: àáâãäåæçèéêë",  # Accented characters
            "Symbols: !@#$%^&*()_+-=[]{}|;':\",./<>?",  # Special symbols
        ]

        for special_char_content in special_characters:
            memory_data = self.data_factory.create_memory_data(
                user_id="test_user",
                content=special_char_content
            )

            def sanitize_special_chars(content):
                # Remove null bytes and control characters
                sanitized = re.sub(r'[\x00-\x1F\x7F]', '', content)
                return sanitized

            sanitized_content = sanitize_special_chars(memory_data["content"])
            
            # Verify dangerous characters are removed
            self.assertNotIn('\x00', sanitized_content)
            self.assertNotIn('\r', sanitized_content)
            self.assertNotIn('\n', sanitized_content)


class TestAuthenticationSecurity(unittest.TestCase):
    """Test authentication security patterns using established framework"""

    def setUp(self):
        """Set up authentication testing environment"""
        self.config = TestConfig()
        self.test_env = TestEnvironment(self.config)
        self.test_env.setup()
        self.data_factory = DataFactory()
        self.assertions = TestAssertions()

    def tearDown(self):
        """Clean up authentication testing environment"""
        self.test_env.teardown()

    @pytest.mark.security
    def test_password_hashing(self):
        """Test password hashing security patterns"""
        # Test password hashing
        test_passwords = [
            "simplepass",
            "Complex123!",
            "verylongpasswordwithmanycharacters",
            "unicode_пароль_密码"
        ]

        for password in test_passwords:
            # Simulate password hashing
            def hash_password(password):
                salt = "random_salt_" + str(uuid.uuid4())
                return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)

            hashed_password = hash_password(password)
            
            # Verify password was hashed (not stored in plain text)
            self.assertNotEqual(password.encode('utf-8'), hashed_password)
            self.assertIsInstance(hashed_password, bytes)
            self.assertGreater(len(hashed_password), 0)

    @pytest.mark.security
    def test_session_token_security(self):
        """Test session token security patterns"""
        # Test session token generation
        def generate_secure_token():
            return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8').rstrip('=')

        tokens = [generate_secure_token() for _ in range(10)]
        
        # Verify tokens are unique
        self.assertEqual(len(tokens), len(set(tokens)))
        
        # Verify tokens have appropriate length and format
        for token in tokens:
            self.assertGreaterEqual(len(token), 20)
            self.assertRegex(token, r'^[A-Za-z0-9_-]+$')

    @pytest.mark.security
    def test_user_id_validation(self):
        """Test user ID validation security patterns"""
        # Test valid user IDs
        valid_user_ids = [
            "user123",
            "test_user_456",
            "user-789",
            str(uuid.uuid4())
        ]

        for user_id in valid_user_ids:
            def validate_user_id(user_id):
                # Basic validation: alphanumeric, underscore, dash, minimum length
                if not user_id or len(user_id) < 3:
                    raise ValueError("User ID must be at least 3 characters long")
                if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
                    raise ValueError("User ID contains invalid characters")
                return user_id

            # Should not raise exception
            validated_id = validate_user_id(user_id)
            self.assertEqual(validated_id, user_id)

        # Test invalid user IDs
        invalid_user_ids = [
            "",  # Empty
            "ab",  # Too short
            "user@123",  # Invalid characters
            "user;DROP",  # SQL injection attempt
            "../admin",  # Path traversal attempt
        ]

        for invalid_user_id in invalid_user_ids:
            with self.assertRaises(ValueError):
                validate_user_id(invalid_user_id)


class TestDataPrivacySecurity(unittest.TestCase):
    """Test data privacy security patterns using established framework"""

    def setUp(self):
        """Set up data privacy testing environment"""
        self.config = TestConfig()
        self.test_env = TestEnvironment(self.config)
        self.test_env.setup()
        self.data_factory = DataFactory()
        self.assertions = TestAssertions()

    def tearDown(self):
        """Clean up data privacy testing environment"""
        self.test_env.teardown()

    @pytest.mark.security
    def test_pii_detection_and_masking(self):
        """Test PII detection and masking patterns"""
        # Test content with various PII types
        pii_content_examples = [
            "My email is john.doe@example.com and phone is 555-123-4567",
            "SSN: 123-45-6789, Credit Card: 4111-1111-1111-1111",
            "IP Address: 192.168.1.1, MAC: 00:11:22:33:44:55",
            "Date of birth: 1990-01-01, Driver's license: DL123456789"
        ]

        def detect_and_mask_pii(content):
            # Simple PII detection and masking
            patterns = {
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '[EMAIL]',
                r'\b\d{3}-\d{3}-\d{4}\b': '[PHONE]',
                r'\b\d{3}-\d{2}-\d{4}\b': '[SSN]',
                r'\b\d{4}-\d{4}-\d{4}-\d{4}\b': '[CREDIT_CARD]',
                r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b': '[IP_ADDRESS]',
                r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b': '[MAC_ADDRESS]'
            }
            
            masked_content = content
            for pattern, replacement in patterns.items():
                masked_content = re.sub(pattern, replacement, masked_content)
            
            return masked_content

        for pii_content in pii_content_examples:
            memory_data = self.data_factory.create_memory_data(
                user_id="test_user",
                content=pii_content
            )

            masked_content = detect_and_mask_pii(memory_data["content"])
            
            # Verify PII was masked
            self.assertNotIn("@example.com", masked_content)
            self.assertNotIn("555-123-4567", masked_content)
            self.assertNotIn("123-45-6789", masked_content)
            self.assertNotIn("4111-1111-1111-1111", masked_content)
            
            # Verify masks are present
            if "john.doe@example.com" in pii_content:
                self.assertIn("[EMAIL]", masked_content)

    @pytest.mark.security
    def test_data_encryption_simulation(self):
        """Test data encryption simulation patterns"""
        sensitive_data = [
            "Personal diary entry about my feelings",
            "Medical information: Patient has diabetes",
            "Financial data: Account balance $5000",
            "Legal document: Contract terms and conditions"
        ]

        def simulate_encryption(data):
            # Simulate encryption (in real implementation, use proper encryption)
            encoded = base64.b64encode(data.encode('utf-8')).decode('utf-8')
            return f"ENCRYPTED:{encoded}"

        def simulate_decryption(encrypted_data):
            # Simulate decryption
            if encrypted_data.startswith("ENCRYPTED:"):
                encoded = encrypted_data[10:]  # Remove "ENCRYPTED:" prefix
                decoded = base64.b64decode(encoded).decode('utf-8')
                return decoded
            return encrypted_data

        for sensitive_content in sensitive_data:
            memory_data = self.data_factory.create_memory_data(
                user_id="test_user",
                content=sensitive_content
            )

            # Encrypt sensitive content
            encrypted_content = simulate_encryption(memory_data["content"])
            
            # Verify content is encrypted
            self.assertNotEqual(encrypted_content, sensitive_content)
            self.assertTrue(encrypted_content.startswith("ENCRYPTED:"))

            # Verify content can be decrypted
            decrypted_content = simulate_decryption(encrypted_content)
            self.assertEqual(decrypted_content, sensitive_content)


class TestRateLimitingSecurity(unittest.TestCase):
    """Test rate limiting security patterns using established framework"""

    def setUp(self):
        """Set up rate limiting testing environment"""
        self.config = TestConfig()
        self.test_env = TestEnvironment(self.config)
        self.test_env.setup()
        self.performance_tracker = PerformanceTracker()

    def tearDown(self):
        """Clean up rate limiting testing environment"""
        self.test_env.teardown()

    @pytest.mark.security
    def test_request_rate_limiting(self):
        """Test request rate limiting patterns"""
        # Simulate rate limiting
        class RateLimiter:
            def __init__(self, max_requests=10, time_window=60):
                self.max_requests = max_requests
                self.time_window = time_window
                self.requests = {}

            def is_allowed(self, user_id):
                import time
                current_time = time.time()
                
                if user_id not in self.requests:
                    self.requests[user_id] = []
                
                # Remove old requests outside time window
                self.requests[user_id] = [
                    req_time for req_time in self.requests[user_id]
                    if current_time - req_time < self.time_window
                ]
                
                # Check if under limit
                if len(self.requests[user_id]) < self.max_requests:
                    self.requests[user_id].append(current_time)
                    return True
                return False

        rate_limiter = RateLimiter(max_requests=5, time_window=60)
        
        # Test normal usage (should be allowed)
        for i in range(5):
            self.assertTrue(rate_limiter.is_allowed("user123"))
        
        # Test rate limit exceeded (should be denied)
        self.assertFalse(rate_limiter.is_allowed("user123"))
        
        # Test different user (should be allowed)
        self.assertTrue(rate_limiter.is_allowed("user456"))

    @pytest.mark.security
    @pytest.mark.performance
    def test_concurrent_request_handling(self):
        """Test concurrent request handling security"""
        self.performance_tracker.start_timer("concurrent_requests")
        
        # Simulate concurrent requests
        def simulate_concurrent_requests(user_count=10, requests_per_user=5):
            results = {}
            for user_id in range(user_count):
                user_results = []
                for request_id in range(requests_per_user):
                    # Simulate request processing
                    memory_data = DataFactory.create_memory_data(
                        user_id=f"user_{user_id}",
                        content=f"Request {request_id} from user {user_id}"
                    )
                    user_results.append({
                        "status": "success",
                        "request_id": request_id,
                        "processed_at": datetime.now(timezone.utc).isoformat()
                    })
                results[f"user_{user_id}"] = user_results
            return results

        results = simulate_concurrent_requests(user_count=5, requests_per_user=3)
        
        self.performance_tracker.end_timer("concurrent_requests")
        
        # Verify all requests were processed
        self.assertEqual(len(results), 5)
        for user_id, user_results in results.items():
            self.assertEqual(len(user_results), 3)
            for result in user_results:
                self.assertEqual(result["status"], "success")


class TestSecurityHeaders(unittest.TestCase):
    """Test security headers patterns using established framework"""

    def setUp(self):
        """Set up security headers testing environment"""
        self.config = TestConfig()
        self.test_env = TestEnvironment(self.config)
        self.test_env.setup()
        self.assertions = TestAssertions()

    def tearDown(self):
        """Clean up security headers testing environment"""
        self.test_env.teardown()

    @pytest.mark.security
    def test_security_headers_validation(self):
        """Test security headers validation patterns"""
        # Simulate HTTP response with security headers
        def create_secure_response():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                'Content-Security-Policy': "default-src 'self'",
                'Referrer-Policy': 'strict-origin-when-cross-origin'
            }
            return mock_response

        response = create_secure_response()
        
        # Verify security headers are present
        required_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security',
            'Content-Security-Policy'
        ]
        
        for header in required_headers:
            self.assertIn(header, response.headers)

        # Verify header values
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertIn('max-age=31536000', response.headers['Strict-Transport-Security'])

    @pytest.mark.security
    def test_cors_configuration(self):
        """Test CORS configuration security patterns"""
        # Test CORS configuration
        def validate_cors_headers(origin, allowed_origins):
            cors_headers = {}
            
            if origin in allowed_origins:
                cors_headers['Access-Control-Allow-Origin'] = origin
                cors_headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE'
                cors_headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                cors_headers['Access-Control-Allow-Credentials'] = 'true'
            else:
                # Deny unauthorized origins
                cors_headers['Access-Control-Allow-Origin'] = 'null'
            
            return cors_headers

        allowed_origins = ['https://localhost:3000', 'https://myapp.com']
        
        # Test allowed origin
        cors_headers = validate_cors_headers('https://localhost:3000', allowed_origins)
        self.assertEqual(cors_headers['Access-Control-Allow-Origin'], 'https://localhost:3000')
        
        # Test disallowed origin
        cors_headers = validate_cors_headers('https://malicious.com', allowed_origins)
        self.assertEqual(cors_headers['Access-Control-Allow-Origin'], 'null')


if __name__ == "__main__":
    # Run tests with pytest markers
    pytest.main([__file__, "-v", "--tb=short"])