#!/usr/bin/env python3
"""
Post-Deployment Smoke Tests
Tests critical endpoints after deployment to verify the application is working.
"""

import os
import sys
import asyncio
import time
from typing import Dict, Optional

try:
    import httpx
except ImportError:
    print("❌ httpx not installed. Install with: pip install httpx")
    sys.exit(1)

# Color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


class SmokeTest:
    def __init__(self, base_url: Optional[str] = None):
        """Initialize smoke test"""
        self.base_url = base_url or os.getenv("RAILWAY_URL", "http://localhost:8000")
        if not self.base_url.startswith("http"):
            self.base_url = f"https://{self.base_url}"

        self.base_url = self.base_url.rstrip("/")
        self.tests_passed = 0
        self.tests_failed = 0
        self.tests_total = 0

    def log_test(self, name: str, passed: bool, message: str = ""):
        """Log test result"""
        self.tests_total += 1
        if passed:
            self.tests_passed += 1
            status = f"{GREEN}✅ PASS{RESET}"
        else:
            self.tests_failed += 1
            status = f"{RED}❌ FAIL{RESET}"

        print(f"{status} | {name}")
        if message:
            print(f"     {message}")

    async def test_health_endpoint(self, client: httpx.AsyncClient) -> bool:
        """Test /health endpoint"""
        test_name = "Health Check Endpoint"

        try:
            response = await client.get(f"{self.base_url}/health", timeout=10.0)

            if response.status_code != 200:
                self.log_test(
                    test_name, False, f"Expected 200, got {response.status_code}"
                )
                return False

            data = response.json()

            # Check response structure
            if "status" not in data:
                self.log_test(test_name, False, "Missing 'status' field")
                return False

            if data["status"] not in ["healthy", "degraded"]:
                self.log_test(
                    test_name, False, f"Unexpected status: {data['status']}"
                )
                return False

            # Check components
            checks = data.get("checks", {})
            if "database" in checks:
                db_status = checks["database"].get("status")
                if db_status != "healthy":
                    self.log_test(
                        test_name, False, f"Database not healthy: {db_status}"
                    )
                    return False

            self.log_test(test_name, True, f"Status: {data['status']}")
            return True

        except httpx.TimeoutException:
            self.log_test(test_name, False, "Request timeout")
            return False
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False

    async def test_root_endpoint(self, client: httpx.AsyncClient) -> bool:
        """Test root endpoint"""
        test_name = "Root Endpoint"

        try:
            response = await client.get(f"{self.base_url}/", timeout=5.0)

            if response.status_code not in [200, 307]:  # 307 is redirect
                self.log_test(
                    test_name, False, f"Expected 200/307, got {response.status_code}"
                )
                return False

            self.log_test(test_name, True, f"Status: {response.status_code}")
            return True

        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False

    async def test_docs_endpoint(self, client: httpx.AsyncClient) -> bool:
        """Test /docs endpoint (OpenAPI docs)"""
        test_name = "API Documentation"

        try:
            response = await client.get(f"{self.base_url}/docs", timeout=5.0)

            if response.status_code != 200:
                self.log_test(
                    test_name, False, f"Expected 200, got {response.status_code}"
                )
                return False

            # Check if it's HTML
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type:
                self.log_test(test_name, False, f"Unexpected content-type: {content_type}")
                return False

            self.log_test(test_name, True)
            return True

        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False

    async def test_cors_headers(self, client: httpx.AsyncClient) -> bool:
        """Test CORS headers are present"""
        test_name = "CORS Configuration"

        try:
            response = await client.options(
                f"{self.base_url}/health",
                headers={"Origin": "http://localhost:3000"},
                timeout=5.0,
            )

            # Check for CORS headers
            has_cors = (
                "access-control-allow-origin" in response.headers
                or "access-control-allow-credentials" in response.headers
            )

            if not has_cors:
                self.log_test(test_name, False, "CORS headers not found")
                return False

            self.log_test(test_name, True)
            return True

        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False

    async def test_response_time(self, client: httpx.AsyncClient) -> bool:
        """Test response time is acceptable"""
        test_name = "Response Time"

        try:
            start = time.time()
            response = await client.get(f"{self.base_url}/health", timeout=5.0)
            elapsed = time.time() - start

            # Health check should respond in under 3 seconds
            if elapsed > 3.0:
                self.log_test(
                    test_name, False, f"Too slow: {elapsed:.2f}s (expected <3s)"
                )
                return False

            if response.status_code != 200:
                self.log_test(
                    test_name, False, f"Expected 200, got {response.status_code}"
                )
                return False

            self.log_test(test_name, True, f"{elapsed:.2f}s")
            return True

        except httpx.TimeoutException:
            self.log_test(test_name, False, "Request timeout (>5s)")
            return False
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False

    async def test_submission_endpoint_exists(self, client: httpx.AsyncClient) -> bool:
        """Test submission endpoint exists (don't actually submit)"""
        test_name = "Submission Endpoint Exists"

        try:
            # POST without data should return 422 (validation error) not 404
            response = await client.post(
                f"{self.base_url}/api/submit", json={}, timeout=5.0
            )

            if response.status_code == 404:
                self.log_test(test_name, False, "Endpoint not found (404)")
                return False

            # 422 (validation error) or 400 (bad request) means endpoint exists
            if response.status_code in [422, 400]:
                self.log_test(test_name, True, f"Endpoint exists (returns {response.status_code})")
                return True

            # If we get 405 (method not allowed), endpoint exists but wrong method
            if response.status_code == 405:
                self.log_test(test_name, False, "Method not allowed (wrong HTTP method)")
                return False

            self.log_test(
                test_name, True, f"Endpoint exists (returns {response.status_code})"
            )
            return True

        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False

    async def test_admin_endpoints_protected(self, client: httpx.AsyncClient) -> bool:
        """Test admin endpoints are protected (require auth)"""
        test_name = "Admin Endpoint Protection"

        try:
            # Try accessing admin endpoint without auth
            response = await client.get(
                f"{self.base_url}/api/admin/submissions", timeout=5.0
            )

            # Should return 401 (unauthorized) or 403 (forbidden), not 200
            if response.status_code == 200:
                self.log_test(
                    test_name, False, "Admin endpoint not protected (returns 200)"
                )
                return False

            if response.status_code in [401, 403]:
                self.log_test(test_name, True, f"Protected (returns {response.status_code})")
                return True

            # 404 is also acceptable (route may not exist)
            if response.status_code == 404:
                self.log_test(test_name, True, "Endpoint not found (404)")
                return True

            self.log_test(
                test_name, False, f"Unexpected status: {response.status_code}"
            )
            return False

        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False

    async def run_all_tests(self):
        """Run all smoke tests"""
        print(f"\n{BLUE}{'='*70}")
        print("🧪 POST-DEPLOYMENT SMOKE TESTS")
        print(f"{'='*70}{RESET}")
        print(f"Target: {self.base_url}\n")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Run tests in order
            tests = [
                self.test_health_endpoint,
                self.test_root_endpoint,
                self.test_docs_endpoint,
                self.test_cors_headers,
                self.test_response_time,
                self.test_submission_endpoint_exists,
                self.test_admin_endpoints_protected,
            ]

            for test in tests:
                await test(client)
                await asyncio.sleep(0.1)  # Small delay between tests

        # Print summary
        print(f"\n{BLUE}{'='*70}")
        print("📊 SMOKE TEST SUMMARY")
        print(f"{'='*70}{RESET}\n")

        print(f"Total tests: {self.tests_total}")
        print(f"{GREEN}✅ Passed: {self.tests_passed}{RESET}")
        print(f"{RED}❌ Failed: {self.tests_failed}{RESET}\n")

        if self.tests_failed > 0:
            print(f"{RED}{'='*70}")
            print("❌ SMOKE TESTS FAILED")
            print(f"{'='*70}{RESET}\n")
            print("Deployment may have issues. Check the logs above.\n")
            return False

        print(f"{GREEN}{'='*70}")
        print("✅ ALL SMOKE TESTS PASSED")
        print(f"{'='*70}{RESET}\n")
        print("Deployment is healthy and ready for traffic!\n")
        return True


async def main():
    """Main entry point"""
    # Get Railway URL from environment
    railway_url = os.getenv("RAILWAY_URL")

    if not railway_url:
        print(f"{YELLOW}⚠️  RAILWAY_URL not set, using localhost{RESET}")
        print(f"{YELLOW}   Set RAILWAY_URL=your-app.railway.app for production tests{RESET}\n")
        railway_url = "http://localhost:8000"

    tester = SmokeTest(base_url=railway_url)

    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests cancelled by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Fatal error during smoke tests: {e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
