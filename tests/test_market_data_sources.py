import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

import crypto_api
import line_bot
import market_collector


class MarketDataSourceTest(unittest.TestCase):
    def test_get_coin_from_supabase_returns_market_data_with_source(self):
        db_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": "now",
        }

        with patch("database_manager.get_market_data_by_symbol", return_value=db_coin):
            result = crypto_api.get_coin_from_supabase("btc")

        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(result["source"], "Supabase")

    def test_get_coin_from_supabase_returns_none_when_db_fails(self):
        with patch("database_manager.get_market_data_by_symbol", side_effect=RuntimeError("db down")):
            result = crypto_api.get_coin_from_supabase("btc")

        self.assertIsNone(result)

    def test_local_data_does_not_read_supabase(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_file = Path(temp_dir) / "market_data.json"

            with patch.object(crypto_api, "LOCAL_MARKET_DATA_FILE", missing_file), patch(
                "database_manager.get_market_data_by_symbol",
                return_value={
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "price_usd": 100,
                    "change_24h": 1.5,
                    "updated_at": "now",
                },
            ):
                result = crypto_api.get_coin_from_local_data("btc")

        self.assertIsNone(result)

    def test_line_bot_uses_supabase_before_local_and_api(self):
        supabase_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": "now",
            "source": "Supabase",
        }

        with patch.object(line_bot, "get_coin_from_supabase", return_value=supabase_coin) as get_supabase, patch.object(
            line_bot, "get_coin_from_local_data", return_value=None
        ) as get_local, patch.object(line_bot, "get_coin_price", return_value=None) as get_api, patch.object(
            line_bot, "reply_message"
        ) as reply_message:
            line_bot._handle_coin_price("reply-token", "btc")

        get_supabase.assert_called_once_with("btc")
        get_local.assert_not_called()
        get_api.assert_not_called()
        reply_message.assert_called_once()
        self.assertIn("資料來源：Supabase", reply_message.call_args.args[1])

    def test_line_bot_falls_back_to_local_before_api(self):
        local_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 90,
            "change_24h": 0.5,
            "updated_at": "now",
            "source": "本地 market_data.json",
        }

        with patch.object(line_bot, "get_coin_from_supabase", return_value=None), patch.object(
            line_bot, "get_coin_from_local_data", return_value=local_coin
        ) as get_local, patch.object(line_bot, "get_coin_price", return_value=None) as get_api, patch.object(
            line_bot, "reply_message"
        ) as reply_message:
            line_bot._handle_coin_price("reply-token", "btc")

        get_local.assert_called_once_with("btc")
        get_api.assert_not_called()
        self.assertIn("資料來源：本地 market_data.json", reply_message.call_args.args[1])

    def test_line_bot_falls_back_to_realtime_api_last(self):
        api_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 80,
            "change_24h": -0.5,
            "updated_at": "now",
            "source": "CoinGecko",
        }

        with patch.object(line_bot, "get_coin_from_supabase", return_value=None), patch.object(
            line_bot, "get_coin_from_local_data", return_value=None
        ), patch.object(line_bot, "get_coin_price", return_value=api_coin) as get_api, patch.object(
            line_bot, "reply_message"
        ) as reply_message:
            line_bot._handle_coin_price("reply-token", "btc")

        get_api.assert_called_once_with("btc")
        self.assertIn("資料來源：即時 API", reply_message.call_args.args[1])

    def test_market_collector_writes_supabase_first_without_json_when_successful(self):
        data = {
            "btc": {
                "name": "Bitcoin",
                "symbol": "BTC",
                "price_usd": 100,
                "change_24h": 1.5,
                "updated_at": "now",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            market_file = Path(temp_dir) / "market_data.json"
            with patch.object(market_collector, "MARKET_DATA_FILE", market_file), patch(
                "database_manager.upsert_market_data", return_value=True
            ) as upsert_market_data, patch("builtins.print") as print_log:
                market_collector.save_market_data(data)

            self.assertFalse(market_file.exists())

        upsert_market_data.assert_called_once_with(data["btc"])
        print_log.assert_any_call("[MarketCollector] 準備寫入 Supabase：BTC")

    def test_market_collector_logs_fallback_when_supabase_write_fails(self):
        data = {
            "btc": {
                "name": "Bitcoin",
                "symbol": "BTC",
                "price_usd": 100,
                "change_24h": 1.5,
                "updated_at": "now",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            market_file = Path(temp_dir) / "market_data.json"
            with patch.object(market_collector, "MARKET_DATA_FILE", market_file), patch(
                "database_manager.upsert_market_data", return_value=False
            ), patch("builtins.print") as print_log:
                market_collector.save_market_data(data)

            self.assertTrue(market_file.exists())

        print_log.assert_any_call("[MarketCollector] 使用 fallback local JSON")

    def test_collect_market_data_logs_coin_update_and_completion(self):
        response_data = {
            "bitcoin": {
                "usd": 100,
                "usd_24h_change": 1.5,
            }
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return response_data

        with patch.object(
            market_collector,
            "TRACKED_COINS",
            {"btc": {"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC"}},
        ), patch.object(market_collector.requests, "get", return_value=FakeResponse()), patch.object(
            market_collector, "save_market_data"
        ), patch("builtins.print") as print_log:
            market_collector.collect_market_data()

        print_log.assert_any_call("[MarketCollector] 準備更新：BTC")
        print_log.assert_any_call("[MarketCollector] 本次市場更新完成")

    def test_collect_market_data_logs_rate_limit_when_coingecko_returns_429(self):
        response = requests.Response()
        response.status_code = 429
        error = requests.HTTPError("429 Client Error", response=response)

        class FakeResponse:
            def raise_for_status(self):
                raise error

        with patch.object(market_collector.requests, "get", return_value=FakeResponse()), patch.object(
            market_collector, "load_market_data", return_value={}
        ), patch("builtins.print") as print_log:
            market_collector.collect_market_data()

        print_log.assert_any_call("[MarketCollector] CoinGecko 被限流")
        print_log.assert_any_call("[MarketCollector] 本次市場更新完成")


if __name__ == "__main__":
    unittest.main()
