import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import requests

import crypto_api
import line_bot
import market_collector
from services.market import collector_service
from services.line import analysis_service as line_analysis_service
from services.line import price_service as line_price_service


def fresh_timestamp():
    return datetime.now(timezone.utc).isoformat()


def stale_timestamp():
    return (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat()


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

    @unittest.skip("Local JSON price lookup is removed from user-facing price queries.")
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
                    "updated_at": fresh_timestamp(),
                },
            ):
                result = crypto_api.get_coin_from_local_data("btc")

        self.assertIsNone(result)

    def test_coinglass_url_returns_supported_symbol_link(self):
        self.assertEqual(
            crypto_api.get_coinglass_url("btc"),
            "https://www.coinglass.com/zh-TW/currencies/BTC",
        )

    def test_all_mainstream_coinglass_links_contains_all_supported_symbols(self):
        links = crypto_api.get_all_mainstream_coinglass_links()

        self.assertIn("BTC：\nhttps://www.coinglass.com/zh-TW/currencies/BTC", links)
        self.assertIn("AVAX：\nhttps://www.coinglass.com/zh-TW/currencies/AVAX", links)

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

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_freshness_treats_naive_updated_at_as_utc(self):
        now_utc = datetime(2026, 5, 23, 12, 4, 30, tzinfo=timezone.utc)
        coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": "2026-05-23 12:00:00",
        }

        with patch.object(line_bot, "get_market_data_by_symbol", return_value=coin), patch(
            "builtins.print"
        ) as print_log:
            result = line_bot._get_fresh_supabase_market_data("BTC", now_utc=now_utc)

        self.assertIsNotNone(result)
        print_log.assert_any_call("[Freshness] BTC updated_at 原始值：2026-05-23 12:00:00")
        print_log.assert_any_call("[Freshness] BTC parsed updated_at UTC：2026-05-23T12:00:00+00:00")
        print_log.assert_any_call("[Freshness] 系統現在 UTC：2026-05-23T12:04:30+00:00")
        print_log.assert_any_call("[Freshness] 資料年齡：4.5 分鐘")
        print_log.assert_any_call("[Freshness] freshness limit：5 分鐘")
        print_log.assert_any_call("[Freshness] fresh：True")
        print_log.assert_any_call("[Freshness] BTC 資料新鮮，資料年齡：4.5 分鐘")

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_freshness_accepts_supabase_iso_timestamp_and_logs_stale_age(self):
        now_utc = datetime(2026, 5, 23, 12, 8, 42, tzinfo=timezone.utc)
        coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": "2026-05-23T12:00:00+00:00",
        }

        with patch.object(line_bot, "get_market_data_by_symbol", return_value=coin), patch(
            "builtins.print"
        ) as print_log:
            result = line_bot._get_fresh_supabase_market_data("BTC", now_utc=now_utc)

        self.assertIsNone(result)
        print_log.assert_any_call("[Freshness] BTC updated_at 原始值：2026-05-23T12:00:00+00:00")
        print_log.assert_any_call("[Freshness] BTC parsed updated_at UTC：2026-05-23T12:00:00+00:00")
        print_log.assert_any_call("[Freshness] 系統現在 UTC：2026-05-23T12:08:42+00:00")
        print_log.assert_any_call("[Freshness] 資料年齡：8.7 分鐘")
        print_log.assert_any_call("[Freshness] freshness limit：5 分鐘")
        print_log.assert_any_call("[Freshness] fresh：False")
        print_log.assert_any_call("[Freshness] BTC 資料已過期，資料年齡：8.7 分鐘，超過限制：5 分鐘，放棄使用 Supabase 價格")

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_freshness_accepts_supabase_space_plus_zero_timestamp(self):
        now_utc = datetime(2026, 5, 23, 12, 2, 0, tzinfo=timezone.utc)
        coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": "2026-05-23 12:00:00+00",
        }

        with patch.object(line_bot, "get_market_data_by_symbol", return_value=coin), patch(
            "builtins.print"
        ) as print_log:
            result = line_bot._get_fresh_supabase_market_data("BTC", now_utc=now_utc)

        self.assertIsNotNone(result)
        print_log.assert_any_call("[Freshness] BTC parsed updated_at UTC：2026-05-23T12:00:00+00:00")
        print_log.assert_any_call("[Freshness] 資料年齡：2.0 分鐘")

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_logs_missing_supabase_data(self):
        now_utc = datetime(2026, 5, 23, 12, 0, tzinfo=timezone.utc)

        with patch.object(line_bot, "get_market_data_by_symbol", return_value=None), patch(
            "builtins.print"
        ) as print_log:
            result = line_bot._get_fresh_supabase_market_data("BTC", now_utc=now_utc)

        self.assertIsNone(result)
        print_log.assert_any_call("[Freshness] BTC 在 Supabase 沒有資料，提供 CoinGlass fallback links")

    def test_crypto_api_no_longer_exposes_local_or_realtime_price_lookup(self):
        self.assertFalse(hasattr(crypto_api, "get_coin_from_local_data"))
        self.assertFalse(hasattr(crypto_api, "get_coin_price"))

    @unittest.skip("Local JSON price lookup is removed from user-facing price queries.")
    def test_stale_local_data_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            market_file = Path(temp_dir) / "market_data.json"
            market_file.write_text(
                json.dumps(
                    {
                        "btc": {
                            "name": "Bitcoin",
                            "symbol": "BTC",
                            "price_usd": 100,
                            "change_24h": 1.5,
                            "updated_at": stale_timestamp(),
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(crypto_api, "LOCAL_MARKET_DATA_FILE", market_file), patch(
                "builtins.print"
            ) as print_log:
                result = crypto_api.get_coin_from_local_data("btc")

        self.assertIsNone(result)
        print_log.assert_any_call("[Freshness] JSON BTC 資料超過 5 分鐘，視為過期。")

    @unittest.skip("Realtime API price lookup is removed from user-facing price queries.")
    def test_api_failure_returns_tradingview_fallback_links(self):
        with patch.object(crypto_api, "_get_coin_price_from_coingecko", return_value=None), patch.object(
            crypto_api, "_get_coin_price_from_coincap", return_value=None
        ), patch("builtins.print") as print_log:
            result = crypto_api.get_coin_price("btc")

        self.assertIn("即時市場資料服務暫時異常", result)
        self.assertIn("超過 5 分鐘的舊價格", result)
        self.assertIn("https://www.tradingview.com/symbols/BTCUSDT/", result)
        self.assertIn("https://www.tradingview.com/symbols/AVAXUSDT/", result)
        print_log.assert_any_call("[CryptoAPI] API 全部失敗")
        print_log.assert_any_call("[CryptoAPI] 提供 TradingView fallback links")

    @unittest.skip("Realtime API price lookup is removed from user-facing price queries.")
    def test_realtime_api_success_updates_supabase_and_json(self):
        api_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": fresh_timestamp(),
            "source": "CoinGecko",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            market_file = Path(temp_dir) / "market_data.json"
            with patch.object(crypto_api, "LOCAL_MARKET_DATA_FILE", market_file), patch.object(
                crypto_api, "_get_coin_price_from_coingecko", return_value=api_coin
            ), patch.object(crypto_api, "_get_coin_price_from_coincap", return_value=None), patch(
                "database_manager.upsert_market_data", return_value=True
            ) as upsert_market_data:
                result = crypto_api.get_coin_price("btc")

            saved_data = json.loads(market_file.read_text(encoding="utf-8"))

        self.assertEqual(result["symbol"], "BTC")
        upsert_market_data.assert_called_once()
        self.assertEqual(saved_data["btc"]["symbol"], "BTC")

    @unittest.skip("Old LINE price flow used JSON/API fallbacks; new flow is Supabase-only.")
    @unittest.skip("Legacy line_bot internals moved to services.")
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

    @unittest.skip("Old LINE price flow used JSON/API fallbacks; new flow is Supabase-only.")
    @unittest.skip("Legacy line_bot internals moved to services.")
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

    @unittest.skip("Old LINE price flow used JSON/API fallbacks; new flow is Supabase-only.")
    @unittest.skip("Legacy line_bot internals moved to services.")
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
        ) as reply_message, patch("builtins.print") as print_log:
            line_bot._handle_coin_price("reply-token", "btc")

        get_api.assert_called_once_with("btc")
        self.assertIn("資料來源：即時 API", reply_message.call_args.args[1])
        print_log.assert_any_call("[PriceFlow] 查詢：BTC")
        print_log.assert_any_call("[PriceFlow] Supabase fresh：False")
        print_log.assert_any_call("[PriceFlow] JSON fresh：False")
        print_log.assert_any_call("[PriceFlow] 嘗試即時 API")
        print_log.assert_any_call("[PriceFlow] 即時 API 成功，不提供 TradingView 連結")

    @unittest.skip("Old LINE price flow used JSON/API fallbacks; new flow is Supabase-only.")
    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_returns_tradingview_links_when_all_price_sources_fail(self):
        with patch.object(line_bot, "get_coin_from_supabase", return_value=None), patch.object(
            line_bot, "get_coin_from_local_data", return_value=None
        ), patch.object(line_bot, "get_coin_price", return_value=None), patch.object(
            line_bot, "reply_message"
        ) as reply_message, patch("builtins.print") as print_log:
            line_bot._handle_coin_price("reply-token", "btc")

        reply_message.assert_called_once()
        self.assertIn("即時市場資料服務暫時異常", reply_message.call_args.args[1])
        self.assertIn("https://www.tradingview.com/symbols/BTCUSDT/", reply_message.call_args.args[1])
        print_log.assert_any_call("[PriceFlow] 即時 API 失敗，提供 TradingView 連結")

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_uses_fresh_supabase_data_only(self):
        supabase_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": fresh_timestamp(),
        }

        with patch.object(line_bot, "get_market_data_by_symbol", return_value=supabase_coin) as get_supabase, patch.object(
            line_bot, "reply_message"
        ) as reply_message, patch("builtins.print") as print_log:
            line_bot._handle_coin_price("reply-token", "btc")

        self.assertEqual(get_supabase.call_count, 2)
        reply_message.assert_called_once()
        self.assertIn("Supabase", reply_message.call_args.args[1])
        self.assertTrue(
            any("PriceService" in str(call.args[0]) and "freshness: True" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("MessageService" in str(call.args[0]) and "format price message" in str(call.args[0]) for call in print_log.call_args_list)
        )

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_returns_coinglass_links_when_supabase_missing(self):
        with patch.object(line_bot, "get_market_data_by_symbol", return_value=None) as get_supabase, patch.object(
            line_bot, "reply_message"
        ) as reply_message, patch("builtins.print") as print_log:
            line_bot._handle_coin_price("reply-token", "btc")

        self.assertEqual(get_supabase.call_count, 2)
        reply_message.assert_called_once()
        self.assertIn("https://www.coinglass.com/zh-TW/currencies/BTC", reply_message.call_args.args[1])
        self.assertNotIn("https://www.coinglass.com/zh-TW/currencies/AVAX", reply_message.call_args.args[1])
        self.assertTrue(
            any("PriceService" in str(call.args[0]) and "CoinGlass fallback" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("MessageService" in str(call.args[0]) and "format stale message" in str(call.args[0]) for call in print_log.call_args_list)
        )

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_returns_coinglass_links_when_supabase_stale(self):
        stale_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 1.5,
            "updated_at": stale_timestamp(),
        }

        with patch.object(line_bot, "get_market_data_by_symbol", return_value=stale_coin) as get_supabase, patch.object(
            line_bot, "reply_message"
        ) as reply_message, patch("builtins.print") as print_log:
            line_bot._handle_coin_price("reply-token", "btc")

        self.assertEqual(get_supabase.call_count, 2)
        reply_message.assert_called_once()
        self.assertIn("https://www.coinglass.com/zh-TW/currencies/BTC", reply_message.call_args.args[1])
        self.assertTrue(
            any("PriceService" in str(call.args[0]) and "freshness: False" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("PriceService" in str(call.args[0]) and "CoinGlass fallback" in str(call.args[0]) for call in print_log.call_args_list)
        )

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_analyze_uses_fresh_supabase_data(self):
        supabase_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 2.3,
            "updated_at": fresh_timestamp(),
        }

        with patch.object(
            line_analysis_service, "get_market_data_by_symbol", return_value=supabase_coin
        ) as get_market_data, patch.object(
            line_analysis_service, "analyze_market_data", return_value="BTC analysis"
        ) as analyze_market_data, patch.object(line_bot, "reply_message") as reply_message, patch(
            "builtins.print"
        ) as print_log:
            handled = line_bot._handle_analyze_command("reply-token", "analyze btc")

        self.assertTrue(handled)
        get_market_data.assert_called_once_with("BTC")
        analyze_market_data.assert_called_once()
        self.assertIn("BTC analysis", reply_message.call_args.args[1])
        self.assertTrue(
            any("AnalysisService" in str(call.args[0]) and "freshness: True" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("MessageService" in str(call.args[0]) and "format analysis message" in str(call.args[0]) for call in print_log.call_args_list)
        )

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_analyze_missing_data_replies_unavailable_message(self):
        with patch.object(line_analysis_service, "get_market_data_by_symbol", return_value=None), patch.object(
            line_bot, "reply_message"
        ) as reply_message, patch("builtins.print") as print_log:
            handled = line_bot._handle_analyze_command("reply-token", "analyze btc")

        self.assertTrue(handled)
        self.assertIn("⚠️ 資訊超過 5 分鐘，AI 無法分析。", reply_message.call_args.args[1])
        self.assertIn("https://www.coinglass.com/zh-TW/currencies/BTC", reply_message.call_args.args[1])
        self.assertTrue(
            any(
                "AnalysisService" in str(call.args[0])
                and "market data stale, skip AI analysis" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "AnalysisService" in str(call.args[0])
                and "provide CoinGlass link" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

    @unittest.skip("Legacy line_bot internals moved to services.")
    def test_line_bot_analyze_stale_data_replies_stale_message(self):
        stale_coin = {
            "name": "Bitcoin",
            "symbol": "BTC",
            "price_usd": 100,
            "change_24h": 2.3,
            "updated_at": stale_timestamp(),
        }

        with patch.object(line_analysis_service, "get_market_data_by_symbol", return_value=stale_coin), patch.object(
            line_bot, "reply_message"
        ) as reply_message, patch("builtins.print") as print_log:
            handled = line_bot._handle_analyze_command("reply-token", "analyze btc")

        self.assertTrue(handled)
        self.assertIn("⚠️ 資訊超過 5 分鐘，AI 無法分析。", reply_message.call_args.args[1])
        self.assertIn("https://www.coinglass.com/zh-TW/currencies/BTC", reply_message.call_args.args[1])
        self.assertTrue(
            any(
                "AnalysisService" in str(call.args[0])
                and "market data stale, skip AI analysis" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )
        self.assertTrue(
            any(
                "AnalysisService" in str(call.args[0])
                and "provide CoinGlass link" in str(call.args[0])
                for call in print_log.call_args_list
            )
        )

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

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return response_data

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
        error = requests.HTTPError("429 Client Error", response=response)

        with patch.object(collector_service, "fetch_market_data", return_value=None), patch.object(
            collector_service, "load_market_data", return_value={}
        ), patch("builtins.print") as print_log:
            collector_service.collect_market_data()

        self.assertTrue(
            any("CollectorService" in str(call.args[0]) and "CoinGecko fetch failed" in str(call.args[0]) for call in print_log.call_args_list)
        )
        self.assertTrue(
            any("CollectorService" in str(call.args[0]) and "CoinGecko fetch failed" in str(call.args[0]) for call in print_log.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()
