import unittest
from unittest.mock import patch

import supabase_client


class SupabaseClientTest(unittest.TestCase):
    def tearDown(self):
        supabase_client._supabase_client = None

    def test_missing_config_returns_none_without_crashing(self):
        supabase_client._supabase_client = None

        with patch.object(supabase_client, "SUPABASE_URL", ""), patch.object(
            supabase_client, "SUPABASE_SERVICE_ROLE_KEY", ""
        ):
            client = supabase_client.get_supabase_client()

        self.assertIsNone(client)


if __name__ == "__main__":
    unittest.main()
