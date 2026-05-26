import unittest
from unittest.mock import patch

from services.agent.agent_metrics import (
    AGENT_METRICS,
    get_agent_metrics,
    record_latency,
    reset_agent_metrics,
)
from services.agent.state_manager import reset_user_state
from services.agent.workflow_engine import run_agent_workflow


class AgentMetricsTest(unittest.TestCase):
    def setUp(self):
        reset_agent_metrics()
        reset_user_state("user-1")

    def test_empty_metrics_structure(self):
        metrics = get_agent_metrics()

        self.assertEqual(
            metrics,
            {
                "summary": {
                    "total_workflows": 0,
                    "workflow_success": 0,
                    "workflow_failure": 0,
                    "success_rate": 0,
                    "failure_rate": 0,
                    "fallback_count": 0,
                    "fallback_rate": 0,
                },
                "intents": {
                    "intent_counts": {},
                    "top_intents": [],
                },
                "latency": {
                    "avg_latency_ms": 0,
                    "min_latency_ms": 0,
                    "max_latency_ms": 0,
                    "last_latency_ms": 0,
                    "samples": [],
                },
                "last_workflow": None,
            },
        )

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
        self.assertEqual(metrics["summary"]["total_workflows"], 1)
        self.assertEqual(metrics["summary"]["workflow_success"], 1)
        self.assertEqual(metrics["summary"]["workflow_failure"], 0)
        self.assertAlmostEqual(metrics["summary"]["success_rate"], 1.0, places=3)
        self.assertAlmostEqual(metrics["summary"]["failure_rate"], 0.0, places=3)
        self.assertEqual(metrics["summary"]["fallback_count"], 0)
        self.assertAlmostEqual(metrics["summary"]["fallback_rate"], 0.0, places=3)
        self.assertEqual(metrics["intents"]["intent_counts"], {"price_query": 1})
        self.assertEqual(
            metrics["intents"]["top_intents"],
            [{"intent": "price_query", "count": 1}],
        )
        self.assertEqual(len(metrics["latency"]["samples"]), 1)
        self.assertAlmostEqual(metrics["latency"]["avg_latency_ms"], 250.0, places=3)
        self.assertAlmostEqual(metrics["latency"]["min_latency_ms"], 250.0, places=3)
        self.assertAlmostEqual(metrics["latency"]["max_latency_ms"], 250.0, places=3)
        self.assertAlmostEqual(metrics["latency"]["last_latency_ms"], 250.0, places=3)
        self.assertEqual(metrics["last_workflow"]["intent"], "price_query")
        self.assertTrue(metrics["last_workflow"]["success"])
        self.assertAlmostEqual(metrics["last_workflow"]["latency_ms"], 250.0, places=3)
        self.assertIn("T", metrics["last_workflow"]["timestamp"])

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
        self.assertEqual(metrics["summary"]["total_workflows"], 1)
        self.assertEqual(metrics["summary"]["workflow_success"], 0)
        self.assertEqual(metrics["summary"]["workflow_failure"], 1)
        self.assertAlmostEqual(metrics["summary"]["success_rate"], 0.0, places=3)
        self.assertAlmostEqual(metrics["summary"]["failure_rate"], 1.0, places=3)
        self.assertEqual(metrics["summary"]["fallback_count"], 1)
        self.assertAlmostEqual(metrics["summary"]["fallback_rate"], 1.0, places=3)
        self.assertEqual(metrics["intents"]["intent_counts"], {"price_query": 1})
        self.assertEqual(
            metrics["intents"]["top_intents"],
            [{"intent": "price_query", "count": 1}],
        )
        self.assertEqual(len(metrics["latency"]["samples"]), 1)
        self.assertAlmostEqual(metrics["latency"]["avg_latency_ms"], 500.0, places=3)
        self.assertAlmostEqual(metrics["latency"]["min_latency_ms"], 500.0, places=3)
        self.assertAlmostEqual(metrics["latency"]["max_latency_ms"], 500.0, places=3)
        self.assertAlmostEqual(metrics["latency"]["last_latency_ms"], 500.0, places=3)
        self.assertEqual(metrics["last_workflow"]["intent"], "price_query")
        self.assertFalse(metrics["last_workflow"]["success"])
        self.assertAlmostEqual(metrics["last_workflow"]["latency_ms"], 500.0, places=3)

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
        self.assertEqual(metrics["summary"]["total_workflows"], 1)
        self.assertEqual(metrics["summary"]["workflow_success"], 1)
        self.assertEqual(metrics["summary"]["workflow_failure"], 0)
        self.assertAlmostEqual(metrics["summary"]["success_rate"], 1.0, places=3)
        self.assertAlmostEqual(metrics["summary"]["failure_rate"], 0.0, places=3)
        self.assertEqual(metrics["summary"]["fallback_count"], 1)
        self.assertAlmostEqual(metrics["summary"]["fallback_rate"], 1.0, places=3)
        self.assertEqual(metrics["intents"]["intent_counts"], {"unknown": 1})
        self.assertEqual(
            metrics["intents"]["top_intents"],
            [{"intent": "unknown", "count": 1}],
        )
        self.assertEqual(len(metrics["latency"]["samples"]), 1)
        self.assertAlmostEqual(metrics["latency"]["avg_latency_ms"], 125.0, places=3)
        self.assertAlmostEqual(metrics["latency"]["min_latency_ms"], 125.0, places=3)
        self.assertAlmostEqual(metrics["latency"]["max_latency_ms"], 125.0, places=3)
        self.assertAlmostEqual(metrics["latency"]["last_latency_ms"], 125.0, places=3)
        self.assertEqual(metrics["last_workflow"]["intent"], "unknown")
        self.assertTrue(metrics["last_workflow"]["success"])
        self.assertAlmostEqual(metrics["last_workflow"]["latency_ms"], 125.0, places=3)

    def test_latency_recording_function(self):
        record_latency(42.5)

        metrics = get_agent_metrics()
        self.assertEqual(metrics["latency"]["samples"], [42.5])

    def test_reset_agent_metrics(self):
        with patch(
            "services.agent.workflow_engine.decision_engine.decide_user_intent",
            return_value={"intent": "price_query", "coin": "BTC", "confidence": 0.9},
        ), patch(
            "services.agent.workflow_engine.tool_registry.get_tool_for_intent",
            return_value=lambda coin: {"kind": "price_query", "coin": coin},
        ), patch(
            "services.agent.workflow_engine.perf_counter",
            side_effect=[400.0, 400.1],
        ):
            run_agent_workflow("user-1", "btc")

        reset_agent_metrics()
        metrics = get_agent_metrics()
        self.assertEqual(metrics["summary"]["total_workflows"], 0)
        self.assertEqual(metrics["summary"]["workflow_success"], 0)
        self.assertEqual(metrics["summary"]["workflow_failure"], 0)
        self.assertEqual(metrics["summary"]["fallback_count"], 0)
        self.assertEqual(metrics["intents"]["intent_counts"], {})
        self.assertEqual(metrics["latency"]["samples"], [])
        self.assertIsNone(metrics["last_workflow"])


if __name__ == "__main__":
    unittest.main()
