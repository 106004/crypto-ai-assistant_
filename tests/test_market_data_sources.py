import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import requests

import crypto_api
from services.market import collector_service


def fresh_timestamp():
    return datetime.now(timezone.utc).isoformat()


def stale_timestamp():
    return (datetime.now(timezone.utc) - timedelta(minutes=7)).isoformat()


class MarketDataSourceTest(unittest.TestCase):
    def test_get_coin_from_supabase_returns_market_data_with_source(self):
        db_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": fresh_timestamp(),
        }

        with patch("database_manager.get_market_data_by_symbol", return_value=db_coin):
            result = crypto_api.get_coin_from_supabase("btc")

        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(result["source"], "Supabase")

    def test_get_coin_from_supabase_returns_none_when_db_fails(self):
        with patch("database_manager.get_market_data_by_symbol", side_effect=RuntimeError("db down")):
            result = crypto_api.get_coin_from_supabase("btc")

        self.assertIsNone(result)

    def test_coinglass_url_returns_supported_symbol_link(self):
        self.assertEqual(
            crypto_api.get_coinglass_url("btc"),
            "https://www.coinglass.com/zh-TW/currencies/BTC",
        )

    def test_all_mainstream_coinglass_links_contains_all_supported_symbols(self):
        links = crypto_api.get_all_mainstream_coinglass_links()

        self.assertIn("BTC\nhttps://www.coinglass.com/zh-TW/currencies/BTC", links)
        self.assertIn("AVAX\nhttps://www.coinglass.com/zh-TW/currencies/AVAX", links)

    def test_stale_supabase_data_is_ignored(self):
        db_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": stale_timestamp(),
        }

        with patch("database_manager.get_market_data_by_symbol", return_value=db_coin), patch(
            "builtins.print"
        ) as print_log:
            result = crypto_api.get_coin_from_supabase("btc")

        self.assertIsNone(result)
        self.assertTrue(
            any(
                "SupabaseData" in str(call.args[0]) and "True" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    def test_crypto_api_no_longer_exposes_local_or_realtime_price_lookup(self):
        self.assertFalse(hasattr(crypto_api, "get_coin_from_local_data"))
        self.assertFalse(hasattr(crypto_api, "get_coin_price"))

    def test_collect_market_data_logs_coin_update_and_completion(self):
        response_data = {
            "bitcoin": {
                "usd": 100,
                "usd_24h_change": 1.5,
            }
        }

        with patch.object(
            collector_service,
            "_get_tracked_coins",
            return_value={"btc": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"}},
        ), patch.object(collector_service, "fetch_market_data", return_value=response_data), patch.object(
            collector_service, "save_market_data", return_value=True
        ) as save_market_data, patch("builtins.print") as print_log:
            collector_service.collect_market_data()

        saved_data = save_market_data.call_args.args[0]
        self.assertEqual(saved_data["symbol"], "BTC")
        self.assertTrue(
            any("CollectorService" in str(call.args[0]) and "CoinGecko data fetched" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("CollectorService" in str(call.args[0]) and "normalized" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("CollectorService" in str(call.args[0]) and "market collection complete" in str(call.args[0]) for call in print_log.call_args_list)
        )

    def test_collect_market_data_writes_utc_timezone_aware_updated_at(self):
        response_data = {
            "bitcoin": {
                "usd": 100,
                "usd_24h_change": 1.5,
            }
        }

        with patch.object(
            collector_service,
            "_get_tracked_coins",
            return_value={"btc": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"}},
        ), patch.object(collector_service, "fetch_market_data", return_value=response_data), patch.object(
            collector_service, "save_market_data"
        ) as save_market_data:
            collector_service.collect_market_data()

        saved_data = save_market_data.call_args.args[0]
        updated_at = saved_data["updated_at"]
        parsed = datetime.fromisoformat(updated_at)
        self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_collect_market_data_logs_rate_limit_when_coingecko_returns_429(self):
        response = requests.Response()
        response.status_code = 429

        with patch.object(collector_service, "fetch_market_data", return_value=None), patch.object(
            collector_service, "load_market_data", return_value={}
        ), patch("builtins.print") as print_log:
            collector_service.collect_market_data()

        self.assertTrue(
            any("CollectorService" in str(call.args[0]) and "CoinGecko fetch failed" in str(call.args[0]) for call in print_log.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()
