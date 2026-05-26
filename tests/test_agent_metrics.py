import unittest
from unittest.mock import patch

from services.agent.agent_metrics import AGENT_METRICS, get_agent_metrics, record_latency
from services.agent.state_manager import reset_user_state
from services.agent.workflow_engine import run_agent_workflow


class AgentMetricsTest(unittest.TestCase):
    def setUp(self):
        AGENT_METRICS["workflow_success"] = 0
        AGENT_METRICS["workflow_failure"] = 0
        AGENT_METRICS["fallback_count"] = 0
        AGENT_METRICS["intent_counts"] = {}
        AGENT_METRICS["workflow_latency_ms"] = []
        reset_user_state("user-1")

    def test_success_metrics_from_workflow(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda coin: {"kind": "price_query", "coin": coin},
        ), patch(
            "services.agent.workflow_engine.perf_counter",
            side_effect=[100.0, 100.25],
        ):
            result = run_agent_workflow("user-1", "btc")

        self.assertEqual(result["intent"], "price_query")
        metrics = get_agent_metrics()
        self.assertEqual(metrics["workflow_success"], 1)
        self.assertEqual(metrics["workflow_failure"], 0)
        self.assertEqual(metrics["fallback_count"], 0)
        self.assertEqual(metrics["intent_counts"], {"price_query": 1})
        self.assertEqual(len(metrics["workflow_latency_ms"]), 1)
        self.assertAlmostEqual(metrics["workflow_latency_ms"][0], 250.0, places=3)

    def test_failure_metrics_from_workflow(self):
        def boom(_coin):
            raise RuntimeError("boom")

        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=boom,
        ), patch(
            "services.agent.workflow_engine.perf_counter",
            side_effect=[200.0, 200.5],
        ):
            with self.assertRaises(RuntimeError):
                run_agent_workflow("user-1", "btc")

        metrics = get_agent_metrics()
        self.assertEqual(metrics["workflow_success"], 0)
        self.assertEqual(metrics["workflow_failure"], 1)
        self.assertEqual(metrics["fallback_count"], 1)
        self.assertEqual(metrics["intent_counts"], {"price_query": 1})
        self.assertEqual(len(metrics["workflow_latency_ms"]), 1)
        self.assertAlmostEqual(metrics["workflow_latency_ms"][0], 500.0, places=3)

    def test_fallback_metrics_from_workflow(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "unknown", "coin": "", "confidence": 0.1},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=None,
        ), patch(
            "services.agent.workflow_engine.perf_counter",
            side_effect=[300.0, 300.125],
        ):
            result = run_agent_workflow("user-1", "???")

        self.assertEqual(result["result"], "unknown_intent")
        metrics = get_agent_metrics()
        self.assertEqual(metrics["workflow_success"], 1)
        self.assertEqual(metrics["workflow_failure"], 0)
        self.assertEqual(metrics["fallback_count"], 1)
        self.assertEqual(metrics["intent_counts"], {"unknown": 1})
        self.assertEqual(len(metrics["workflow_latency_ms"]), 1)
        self.assertAlmostEqual(metrics["workflow_latency_ms"][0], 125.0, places=3)

    def test_latency_recording_function(self):
        record_latency(42.5)

        metrics = get_agent_metrics()
        self.assertEqual(metrics["workflow_latency_ms"], [42.5])


if __name__ == "__main__":
    unittest.main()
