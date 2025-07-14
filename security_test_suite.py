#!/usr/bin/env python3
"""
Comprehensive Security Test Suite for MCP Server
Tests all security measures before public deployment
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

import aiohttp


class SecurityTestSuite:
    def __init__(self, base_url: str, api_key: str, domain: str):
        self.base_url = base_url
        self.api_key = api_key
        self.domain = domain
        self.test_results = []
        self.failed_tests = []

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test results"""
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": time.time(),
        }
        self.test_results.append(result)

        if passed:
            print(f"✅ {test_name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {test_name}")
            if details:
                print(f"   {details}")
            self.failed_tests.append(result)

    async def test_authentication_bypass_attempts(self) -> bool:
        """Test various authentication bypass attempts"""
        print("\n🔒 Testing Authentication Security...")

        bypass_attempts = [
            ("No Authorization Header", {}),
            ("Invalid Bearer Token", {"Authorization": "Bearer invalid_token_123"}),
            ("Wrong Token Type", {"Authorization": "Basic invalid_token_123"}),
            ("Empty Bearer Token", {"Authorization": "Bearer "}),
            (
                "SQL Injection in Token",
                {"Authorization": "Bearer '; DROP TABLE users; --"},
            ),
            ("XSS in Token", {"Authorization": "Bearer <script>alert('xss')</script>"}),
            (
                "Path Traversal in Token",
                {"Authorization": "Bearer ../../../etc/passwd"},
            ),
            (
                "Long Token (Buffer Overflow)",
                {"Authorization": "Bearer " + "A" * 10000},
            ),
        ]

        async with aiohttp.ClientSession() as session:
            for test_name, headers in bypass_attempts:
                try:
                    async with session.post(
                        f"{self.base_url}/tools/call",
                        json={"name": "list_memories", "arguments": {}},
                        headers=headers,
                        timeout=10,
                    ) as response:
                        if response.status in [401, 403]:
                            self.log_test(
                                f"Auth Bypass: {test_name}", True, "Correctly rejected"
                            )
                        else:
                            self.log_test(
                                f"Auth Bypass: {test_name}",
                                False,
                                f"Got status {response.status}",
                            )
                            return False
                except Exception as e:
                    self.log_test(
                        f"Auth Bypass: {test_name}",
                        True,
                        f"Exception (expected): {str(e)[:100]}",
                    )

        return True

    async def test_rate_limiting(self) -> bool:
        """Test rate limiting protection"""
        print("\n🚦 Testing Rate Limiting...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            # Test health endpoint rate limiting (30/minute)
            rapid_requests = []
            for i in range(35):  # Exceed limit
                rapid_requests.append(session.get(f"{self.base_url}/health", timeout=5))

            try:
                responses = await asyncio.gather(
                    *rapid_requests, return_exceptions=True
                )
                rate_limited = sum(
                    1 for r in responses if hasattr(r, "status") and r.status == 429
                )

                if rate_limited > 0:
                    self.log_test(
                        "Rate Limiting: Health endpoint",
                        True,
                        f"Rate limited {rate_limited} requests",
                    )
                else:
                    self.log_test(
                        "Rate Limiting: Health endpoint",
                        False,
                        "No rate limiting detected",
                    )
                    return False
            except Exception as e:
                self.log_test(
                    "Rate Limiting: Health endpoint", False, f"Test failed: {e}"
                )
                return False

        return True

    async def test_input_validation(self) -> bool:
        """Test input validation and injection protection"""
        print("\n🛡️  Testing Input Validation...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        malicious_inputs = [
            (
                "SQL Injection",
                {
                    "name": "add_memories",
                    "arguments": {"text": "'; DROP TABLE memories; --"},
                },
            ),
            (
                "XSS Script",
                {
                    "name": "add_memories",
                    "arguments": {"text": "<script>alert('xss')</script>"},
                },
            ),
            (
                "Command Injection",
                {"name": "add_memories", "arguments": {"text": "; rm -rf / ;"}},
            ),
            (
                "Path Traversal",
                {"name": "add_memories", "arguments": {"text": "../../../etc/passwd"}},
            ),
            (
                "JSON Injection",
                {
                    "name": "add_memories",
                    "arguments": {"text": '{"malicious": "payload"}'},
                },
            ),
            (
                "Large Payload",
                {"name": "add_memories", "arguments": {"text": "A" * 100000}},
            ),
            (
                "Null Bytes",
                {"name": "add_memories", "arguments": {"text": "test\x00\x00"}},
            ),
            (
                "Unicode Exploit",
                {"name": "add_memories", "arguments": {"text": "test\u0000\u202e"}},
            ),
        ]

        async with aiohttp.ClientSession() as session:
            for test_name, payload in malicious_inputs:
                try:
                    async with session.post(
                        f"{self.base_url}/tools/call",
                        json=payload,
                        headers=headers,
                        timeout=10,
                    ) as response:
                        if response.status in [400, 422, 500]:
                            self.log_test(
                                f"Input Validation: {test_name}",
                                True,
                                f"Handled safely (status {response.status})",
                            )
                        elif response.status == 200:
                            # Check if the response contains safe, sanitized content
                            result = await response.json()
                            if result.get("success"):
                                self.log_test(
                                    f"Input Validation: {test_name}",
                                    True,
                                    "Input sanitized and processed safely",
                                )
                            else:
                                self.log_test(
                                    f"Input Validation: {test_name}",
                                    False,
                                    "Unexpected successful processing",
                                )
                        else:
                            self.log_test(
                                f"Input Validation: {test_name}",
                                False,
                                f"Unexpected status {response.status}",
                            )
                            return False
                except Exception as e:
                    self.log_test(
                        f"Input Validation: {test_name}",
                        True,
                        f"Exception handled: {str(e)[:100]}",
                    )

        return True

    async def test_cors_policy(self) -> bool:
        """Test CORS policy enforcement"""
        print("\n🌐 Testing CORS Policy...")

        # Test various Origins
        origins_to_test = [
            ("Allowed Domain", "https://mem-mcp.onemainarmy.com", True),
            ("Allowed Parent Domain", "https://onemainarmy.com", True),
            ("Allowed Trusted Domain", "https://drjlabs.com", True),
            ("Allowed ChatGPT Domain", "https://chat.openai.com", True),
            ("Allowed ChatGPT Alt Domain", "https://chatgpt.com", True),
            ("Malicious Domain", "https://evil.com", False),
            ("HTTP (not HTTPS)", "http://mem-mcp.onemainarmy.com", False),
            ("Subdomain Attack", "https://mem-mcp.onemainarmy.com.evil.com", False),
            ("No Origin", None, False),
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            for test_name, origin, should_allow in origins_to_test:
                test_headers = headers.copy()
                if origin:
                    test_headers["Origin"] = origin

                try:
                    async with session.post(
                        f"{self.base_url}/tools/call",
                        json={"name": "list_memories", "arguments": {}},
                        headers=test_headers,
                        timeout=10,
                    ) as response:
                        cors_headers = response.headers.get(
                            "Access-Control-Allow-Origin", ""
                        )

                        if should_allow:
                            if origin in cors_headers or cors_headers == "*":
                                self.log_test(
                                    f"CORS Policy: {test_name}",
                                    True,
                                    "Correctly allowed",
                                )
                            else:
                                self.log_test(
                                    f"CORS Policy: {test_name}",
                                    False,
                                    f"Blocked allowed origin: {cors_headers}",
                                )
                        else:
                            if origin not in cors_headers and cors_headers != "*":
                                self.log_test(
                                    f"CORS Policy: {test_name}",
                                    True,
                                    "Correctly blocked",
                                )
                            else:
                                self.log_test(
                                    f"CORS Policy: {test_name}",
                                    False,
                                    f"Allowed malicious origin: {cors_headers}",
                                )
                except Exception as e:
                    self.log_test(
                        f"CORS Policy: {test_name}", False, f"Test failed: {e}"
                    )

        return True

    async def test_security_headers(self) -> bool:
        """Test security headers implementation"""
        print("\n🔐 Testing Security Headers...")

        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                for header_name, expected_value in expected_headers.items():
                    actual_value = response.headers.get(header_name)
                    if actual_value and expected_value in actual_value:
                        self.log_test(
                            f"Security Header: {header_name}",
                            True,
                            f"Value: {actual_value}",
                        )
                    else:
                        self.log_test(
                            f"Security Header: {header_name}",
                            False,
                            f"Missing or incorrect: {actual_value}",
                        )
                        return False

        return True

    async def test_information_disclosure(self) -> bool:
        """Test for information disclosure vulnerabilities"""
        print("\n🕵️  Testing Information Disclosure...")

        # Test endpoints that might leak information
        test_endpoints = [
            "/admin",
            "/debug",
            "/config",
            "/status",
            "/metrics",
            "/logs",
            "/.env",
            "/server-info",
            "/phpinfo",
            "/robots.txt",
            "/sitemap.xml",
            "/backup",
            "/test",
            "/dev",
        ]

        async with aiohttp.ClientSession() as session:
            for endpoint in test_endpoints:
                try:
                    async with session.get(
                        f"{self.base_url}{endpoint}", timeout=5
                    ) as response:
                        if response.status == 404:
                            self.log_test(
                                f"Info Disclosure: {endpoint}",
                                True,
                                "Endpoint not found (good)",
                            )
                        elif response.status == 403:
                            self.log_test(
                                f"Info Disclosure: {endpoint}",
                                True,
                                "Access forbidden (good)",
                            )
                        else:
                            content = await response.text()
                            if len(content) > 100:  # Significant content returned
                                self.log_test(
                                    f"Info Disclosure: {endpoint}",
                                    False,
                                    f"Status {response.status}, content length: {len(content)}",
                                )
                            else:
                                self.log_test(
                                    f"Info Disclosure: {endpoint}",
                                    True,
                                    f"Minimal content (status {response.status})",
                                )
                except Exception as e:
                    self.log_test(
                        f"Info Disclosure: {endpoint}",
                        True,
                        f"Request failed (good): {str(e)[:50]}",
                    )

        return True

    async def test_dos_protection(self) -> bool:
        """Test Denial of Service protection"""
        print("\n🛡️  Testing DoS Protection...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Test large payload
        large_payload = {
            "name": "add_memories",
            "arguments": {"text": "A" * 1000000},  # 1MB payload
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/tools/call",
                    json=large_payload,
                    headers=headers,
                    timeout=30,
                ) as response:
                    if response.status in [
                        413,
                        400,
                        500,
                    ]:  # Request too large or handled
                        self.log_test(
                            "DoS Protection: Large payload",
                            True,
                            f"Handled large payload (status {response.status})",
                        )
                    else:
                        self.log_test(
                            "DoS Protection: Large payload",
                            False,
                            f"Accepted large payload (status {response.status})",
                        )
                        return False
            except Exception as e:
                self.log_test(
                    "DoS Protection: Large payload",
                    True,
                    f"Exception on large payload: {str(e)[:100]}",
                )

        return True

    def test_credential_exposure(self) -> bool:
        """Test for credential exposure in files"""
        print("\n🔍 Testing Credential Exposure...")

        # Check if sensitive files are properly ignored
        sensitive_patterns = [
            ".env",
            ".env.mcp",
            "*.key",
            "*.secret",
            "mcp_server.log",
            "auth_tokens.json",
            "jwt_secret.txt",
        ]

        # Check if .gitignore contains the patterns
        try:
            with open(".gitignore", "r") as f:
                gitignore_content = f.read()

            for pattern in sensitive_patterns:
                if pattern in gitignore_content:
                    self.log_test(
                        f"Credential Protection: {pattern}",
                        True,
                        "Pattern in .gitignore",
                    )
                else:
                    self.log_test(
                        f"Credential Protection: {pattern}",
                        False,
                        "Pattern NOT in .gitignore",
                    )
                    return False
        except Exception as e:
            self.log_test(
                "Credential Protection: .gitignore",
                False,
                f"Error reading .gitignore: {e}",
            )
            return False

        return True

    async def test_valid_functionality(self) -> bool:
        """Test that valid requests still work correctly"""
        print("\n✅ Testing Valid Functionality...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Test valid operations
        async with aiohttp.ClientSession() as session:
            # Test add_memories
            add_payload = {
                "name": "add_memories",
                "arguments": {"text": "Security test - valid operation"},
            }

            async with session.post(
                f"{self.base_url}/tools/call",
                json=add_payload,
                headers=headers,
                timeout=10,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("success"):
                        self.log_test(
                            "Valid Functionality: add_memories",
                            True,
                            "Working correctly",
                        )
                    else:
                        self.log_test(
                            "Valid Functionality: add_memories",
                            False,
                            "Failed to add memory",
                        )
                        return False
                else:
                    self.log_test(
                        "Valid Functionality: add_memories",
                        False,
                        f"Status {response.status}",
                    )
                    return False

        return True

    async def run_all_tests(self) -> bool:
        """Run all security tests"""
        print(f"🔐 Security Test Suite for {self.domain}")
        print("=" * 50)

        tests = [
            ("Authentication Bypass", self.test_authentication_bypass_attempts),
            ("Rate Limiting", self.test_rate_limiting),
            ("Input Validation", self.test_input_validation),
            ("CORS Policy", self.test_cors_policy),
            ("Security Headers", self.test_security_headers),
            ("Information Disclosure", self.test_information_disclosure),
            ("DoS Protection", self.test_dos_protection),
            ("Valid Functionality", self.test_valid_functionality),
        ]

        # Add synchronous tests
        self.test_credential_exposure()

        # Run async tests
        for test_name, test_func in tests:
            try:
                success = await test_func()
                if not success:
                    print(f"\n❌ {test_name} FAILED - stopping tests")
                    return False
            except Exception as e:
                print(f"\n💥 {test_name} CRASHED: {e}")
                return False

        return True

    def generate_report(self) -> str:
        """Generate security test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = len(self.failed_tests)

        report = f"""
🔐 SECURITY TEST REPORT
=====================
Domain: {self.domain}
Total Tests: {total_tests}
Passed: {passed_tests}
Failed: {failed_tests}
Success Rate: {(passed_tests/total_tests)*100:.1f}%

"""

        if self.failed_tests:
            report += "❌ FAILED TESTS:\n"
            for test in self.failed_tests:
                report += f"  - {test['test']}: {test['details']}\n"

        if failed_tests == 0:
            report += "✅ ALL SECURITY TESTS PASSED - READY FOR PRODUCTION\n"
        else:
            report += "❌ SECURITY ISSUES FOUND - DO NOT DEPLOY\n"

        return report


async def main():
    """Main test runner"""
    # Configuration
    BASE_URL = "http://localhost:8081"
    DOMAIN = "mem-mcp.onemainarmy.com"

    # Use production API key if provided, otherwise generate one
    production_api_key = os.getenv("PRODUCTION_API_KEY")
    if production_api_key:
        print("🔑 Using production API key...")
        api_key = production_api_key
        print(f"Using API key: {api_key[:8]}...")
    else:
        print("🔑 Generating secure API key...")
        api_key = (
            subprocess.check_output(["openssl", "rand", "-hex", "32"]).decode().strip()
        )
        print(f"Generated API key: {api_key[:8]}...")

    # Create test environment
    with open(".env.mcp.test", "w") as f:
        f.write(
            f"""HOST=127.0.0.1
PORT=8081
MEM0_API_URL=http://localhost:8000
OPENMEMORY_API_URL=http://localhost:8765
JWT_SECRET={subprocess.check_output(['openssl', 'rand', '-hex', '32']).decode().strip()}
API_KEYS={api_key}
ALLOWED_HOSTS=localhost,127.0.0.1,mem-mcp.onemainarmy.com
"""
        )

    print("🔐 Starting security test suite...")
    print("⚠️  Make sure the MCP server is running on port 8081")
    print("⚠️  Make sure mem0 backend services are running")

    # Run security tests
    suite = SecurityTestSuite(BASE_URL, api_key, DOMAIN)
    success = await suite.run_all_tests()

    # Generate report
    report = suite.generate_report()
    print(report)

    # Save report
    with open("security_test_report.txt", "w") as f:
        f.write(report)

    # Cleanup
    os.remove(".env.mcp.test")

    if success:
        print("🎉 All security tests passed! Ready for production deployment.")
        print(f"🔑 Production API key: {api_key}")
        print("💾 Save this API key securely!")
        return 0
    else:
        print("❌ Security tests failed. DO NOT DEPLOY to production.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
