import unittest

from fastapi.testclient import TestClient

from caretrace.service import RateLimiter, create_app


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_extract_and_response_headers(self):
        response = self.client.post("/api/v1/extract", json={"transcript": "Patient: I stopped taking tablets.\nDoctor: We'll arrange a blood test."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["orders"][0]["provenance"], [2])
        self.assertTrue(response.json()["research_only"])
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_invalid_and_oversized_requests(self):
        self.assertEqual(self.client.post("/api/v1/extract", json={"transcript": "unlabelled text"}).status_code, 422)
        self.assertEqual(self.client.post("/api/v1/extract", content=b"x", headers={"content-type": "text/plain"}).status_code, 415)
        self.assertEqual(self.client.post("/api/v1/extract", content=b"x" * 70000, headers={"content-type": "application/json"}).status_code, 413)

    def test_openapi_ui_policy_allows_its_script_without_weakening_home(self):
        docs = self.client.get("/docs")
        home = self.client.get("/")
        self.assertIn("https://cdn.jsdelivr.net", docs.headers["content-security-policy"])
        self.assertNotIn("'unsafe-inline'", home.headers["content-security-policy"])

    def test_rate_limit_expires_and_bounds_clients(self):
        limiter = RateLimiter(limit=2, window=10, capacity=2)
        self.assertTrue(limiter.allow("a", 0))
        self.assertTrue(limiter.allow("a", 1))
        self.assertFalse(limiter.allow("a", 2))
        self.assertTrue(limiter.allow("a", 10))
        limiter.allow("b", 11)
        limiter.allow("c", 12)
        self.assertEqual(len(limiter.hits), 2)


if __name__ == "__main__":
    unittest.main()
