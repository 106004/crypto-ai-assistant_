import unittest

from services.agent.coin_resolver import resolve_coin


class CoinResolverDebugTest(unittest.TestCase):
    def _trace(self, text: str):
        return resolve_coin(text, debug=True)["debug_trace"]

    def test_bitcoin_exact_match_trace(self):
        trace = self._trace("\u6211\u60f3\u67e5\u6bd4\u7279\u5e63")
        self.assertEqual(trace[0], {"step": "exact_match", "executed": True, "matched": True, "source": "semantic", "coin": "BTC"})
        self.assertEqual(trace[1], {"step": "fuzzy_candidates", "executed": False, "matched": False, "candidates": []})
        self.assertEqual(trace[2], {"step": "ticker_extraction", "executed": False, "matched": False})
        self.assertEqual(trace[3], {"step": "gemini_fallback", "executed": False, "matched": False, "error": None})

    def test_pepe_supported_alias_trace(self):
        trace = self._trace("\u6211\u60f3\u67e5 PEPE")
        self.assertEqual(trace[0], {"step": "exact_match", "executed": True, "matched": True, "source": "unsupported_alias", "coin": "PEPE"})
        self.assertEqual(trace[1], {"step": "fuzzy_candidates", "executed": False, "matched": False, "candidates": []})
        self.assertEqual(trace[2], {"step": "ticker_extraction", "executed": False, "matched": False})
        self.assertEqual(trace[3], {"step": "gemini_fallback", "executed": False, "matched": False, "error": None})

    def test_btcc_fuzzy_trace(self):
        trace = self._trace("\u6211\u60f3\u67e5 BTCc")
        self.assertEqual(trace[0], {"step": "exact_match", "executed": True, "matched": False, "source": "semantic"})
        self.assertEqual(trace[1]["step"], "fuzzy_candidates")
        self.assertTrue(trace[1]["executed"])
        self.assertTrue(trace[1]["matched"])
        self.assertEqual(trace[1]["candidates"], [{"coin": "BTC", "score": 0.943}])
        self.assertEqual(trace[2], {"step": "ticker_extraction", "executed": False, "matched": False})
        self.assertEqual(trace[3], {"step": "gemini_fallback", "executed": False, "matched": False, "error": None})

    def test_typo_does_not_match_trace(self):
        trace = self._trace("\u6211\u60f3\u67e5 \u6bd4\u6301\u5e63")
        self.assertEqual(trace[0], {"step": "exact_match", "executed": True, "matched": False, "source": "semantic"})
        self.assertEqual(trace[1], {"step": "fuzzy_candidates", "executed": True, "matched": False, "candidates": []})
        self.assertEqual(trace[2], {"step": "ticker_extraction", "executed": True, "matched": False})
        self.assertEqual(trace[3], {"step": "gemini_fallback", "executed": False, "matched": False, "error": None})

    def test_weather_sentence_trace(self):
        trace = self._trace("\u4eca\u5929\u5929\u6c23\u5f88\u597d")
        self.assertEqual(trace[0], {"step": "exact_match", "executed": True, "matched": False, "source": "semantic"})
        self.assertEqual(trace[1], {"step": "fuzzy_candidates", "executed": True, "matched": False, "candidates": []})
        self.assertEqual(trace[2], {"step": "ticker_extraction", "executed": True, "matched": False})
        self.assertEqual(trace[3], {"step": "gemini_fallback", "executed": False, "matched": False, "error": None})


if __name__ == "__main__":
    unittest.main()
