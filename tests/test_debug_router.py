import unittest

from api.routers.debug import list_registered_routes
from api_server import app


class DebugRouterTest(unittest.TestCase):
    def test_list_registered_routes_includes_project_routes(self):
        routes = list_registered_routes(app)
        paths = {route["path"] for route in routes}

        self.assertIn("/health", paths)
        self.assertIn("/resolve-coin", paths)
        self.assertIn("/debug/routes", paths)
        self.assertNotIn("/docs", paths)
        self.assertNotIn("/openapi.json", paths)

        debug_route = next(route for route in routes if route["path"] == "/debug/routes")
        self.assertEqual(debug_route["methods"], ["GET"])
        self.assertEqual(debug_route["name"], "debug_routes")

        resolve_route = next(route for route in routes if route["path"] == "/resolve-coin")
        self.assertEqual(resolve_route["name"], "resolve_coin")

        health_route = next(route for route in routes if route["path"] == "/health")
        self.assertEqual(health_route["name"], "health")


if __name__ == "__main__":
    unittest.main()
