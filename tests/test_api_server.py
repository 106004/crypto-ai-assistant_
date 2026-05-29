import unittest
from unittest.mock import patch

from api_server import ResolveCoinRequest, resolve_coin_api


class ApiServerEndpointTest(unittest.TestCase):
    def test_endpoint_uses_resolve_coin_flow(self):
        with patch("api_server.resolve_coin_flow") as helper_mock:
            helper_mock.return_value = {
                "coin": "BTC",
                "status": "supported",
                "method": "exact_match",
                "candidates": [],
                "confidence": 1.0,
                "llm_used": False,
                "debug_trace": [],
                "gemini_key_loaded": False,
                "gemini_client_available": False,
            }

            response = resolve_coin_api(ResolveCoinRequest(text="我想查比特幣"))

        helper_mock.assert_called_once_with("我想查比特幣", debug=False)
        self.assertEqual(response["coin"], "BTC")
        self.assertIn("llm_used", response)
        self.assertIn("debug_trace", response)
        self.assertIn("gemini_key_loaded", response)
        self.assertIn("gemini_client_available", response)

    def test_exception_response(self):
        with patch("api_server.resolve_coin_flow", side_effect=RuntimeError("boom")):
            response = resolve_coin_api(ResolveCoinRequest(text="我想查比特幣"))

        self.assertEqual(
            response,
            {
                "coin": None,
                "status": "error",
                "method": "exception",
                "candidates": [],
                "confidence": 0.0,
                "llm_used": False,
                "debug_trace": [],
                "gemini_key_loaded": False,
                "gemini_client_available": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
