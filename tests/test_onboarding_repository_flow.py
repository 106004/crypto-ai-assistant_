import unittest
from unittest.mock import patch

from services.line import onboarding_service
from services.line.onboarding_service import handle_mycoin, handle_set_coin


class OnboardingRepositoryFlowTest(unittest.TestCase):
    def _run_coin_cycle(self, symbol):
        state = {}

        def fake_save_user(user_data):
            line_user_id = str((user_data or {}).get("line_user_id") or "").strip()
            if not line_user_id:
                return False

            existing = dict(state.get(line_user_id, {}))
            existing.update(user_data)
            state[line_user_id] = existing
            return True

        def fake_get_user(line_user_id):
            return state.get(line_user_id)

        with patch("services.line.onboarding_service.save_user", side_effect=fake_save_user), patch(
            "services.line.onboarding_service.get_user", side_effect=fake_get_user
        ):
            set_reply = handle_set_coin("U1234567890", symbol)
            mycoin_reply = handle_mycoin("U1234567890")

        return state, set_reply, mycoin_reply

    def test_onboarding_service_uses_repository_module(self):
        self.assertEqual(onboarding_service.get_user.__module__, "data.repositories.user_repository")
        self.assertEqual(onboarding_service.save_user.__module__, "data.repositories.user_repository")

    def test_set_btc_then_mycoin_share_repository_state(self):
        state, set_reply, mycoin_reply = self._run_coin_cycle("btc")

        self.assertIn("BTC", set_reply)
        self.assertIn("BTC", mycoin_reply)
        self.assertEqual(state["U1234567890"]["favorite_coin"], "btc")
        self.assertTrue(state["U1234567890"]["onboarded"])

    def test_set_sol_then_mycoin_share_repository_state(self):
        state, set_reply, mycoin_reply = self._run_coin_cycle("sol")

        self.assertIn("SOL", set_reply)
        self.assertIn("SOL", mycoin_reply)
        self.assertEqual(state["U1234567890"]["favorite_coin"], "sol")
        self.assertTrue(state["U1234567890"]["onboarded"])


if __name__ == "__main__":
    unittest.main()
