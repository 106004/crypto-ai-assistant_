import unittest
from unittest.mock import patch

import database_manager


class FakeResponse:
    def __init__(self, data=None):
        self.data = data


class FakeQuery:
    def __init__(self, table):
        self.table = table
        self.operation = None
        self.payload = None
        self.filters = []
        self.limit_value = None

    def select(self, columns):
        self.operation = "select"
        self.payload = columns
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        return self.table.execute(self)


class FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def select(self, columns):
        return FakeQuery(self).select(columns)

    def insert(self, payload):
        return FakeQuery(self).insert(payload)

    def update(self, payload):
        return FakeQuery(self).update(payload)

    def execute(self, query):
        self.executed.append(query)
        if query.operation == "select":
            rows = self.rows
            for column, value in query.filters:
                rows = [row for row in rows if row.get(column) == value]
            if query.limit_value is not None:
                rows = rows[: query.limit_value]
            return FakeResponse(list(rows))

        if query.operation == "insert":
            self.rows.append(dict(query.payload))
            return FakeResponse([query.payload])

        if query.operation == "update":
            for row in self.rows:
                if all(row.get(column) == value for column, value in query.filters):
                    row.update(query.payload)
            return FakeResponse([query.payload])

        return FakeResponse([])


class FakeSupabaseClient:
    def __init__(self):
        self.tables = {
            "users": FakeTable([]),
            "market_data": FakeTable([]),
        }

    def table(self, name):
        return self.tables[name]


class DatabaseManagerTest(unittest.TestCase):
    def setUp(self):
        self.client = FakeSupabaseClient()
        self.client.tables["users"].rows.append(
            {"line_user_id": "U1", "display_name": "old", "favorite_coin": "btc"}
        )
        self.client.tables["market_data"].rows.append(
            {"symbol": "BTC", "name": "Bitcoin", "price_usd": 1, "change_24h": 0, "updated_at": "old"}
        )

    def test_get_user_by_line_id_returns_first_matching_user(self):
        with patch.object(database_manager, "get_supabase_client", return_value=self.client):
            user = database_manager.get_user_by_line_id("U1")

        self.assertEqual(user["line_user_id"], "U1")

    def test_upsert_user_updates_existing_user(self):
        with patch.object(database_manager, "get_supabase_client", return_value=self.client):
            ok = database_manager.upsert_user(
                {"line_user_id": "U1", "display_name": "new", "favorite_coin": "eth"}
            )

        self.assertTrue(ok)
        self.assertEqual(self.client.tables["users"].rows[0]["display_name"], "new")
        operations = [query.operation for query in self.client.tables["users"].executed]
        self.assertIn("update", operations)

    def test_upsert_user_inserts_new_user(self):
        with patch.object(database_manager, "get_supabase_client", return_value=self.client):
            ok = database_manager.upsert_user({"line_user_id": "U2", "display_name": "new"})

        self.assertTrue(ok)
        self.assertEqual(self.client.tables["users"].rows[-1]["line_user_id"], "U2")

    def test_upsert_market_data_updates_existing_symbol(self):
        with patch.object(database_manager, "get_supabase_client", return_value=self.client), patch(
            "builtins.print"
        ) as print_log:
            ok = database_manager.upsert_market_data(
                {
                    "symbol": "btc",
                    "name": "Bitcoin",
                    "price_usd": 100,
                    "change_24h": 2.5,
                    "updated_at": "now",
                }
            )

        self.assertTrue(ok)
        self.assertEqual(self.client.tables["market_data"].rows[0]["symbol"], "BTC")
        self.assertEqual(self.client.tables["market_data"].rows[0]["price_usd"], 100)
        print_log.assert_any_call("[Supabase] BTC 寫入成功")

    def test_upsert_market_data_logs_symbol_when_write_fails(self):
        with patch.object(database_manager, "get_supabase_client", return_value=self.client), patch.object(
            self.client.tables["market_data"], "execute", side_effect=RuntimeError("db down")
        ), patch("builtins.print") as print_log:
            ok = database_manager.upsert_market_data(
                {
                    "symbol": "btc",
                    "name": "Bitcoin",
                    "price_usd": 100,
                    "change_24h": 2.5,
                    "updated_at": "now",
                }
            )

        self.assertFalse(ok)
        print_log.assert_any_call("[Supabase] BTC 寫入失敗：db down")

    def test_get_market_data_by_symbol_returns_matching_symbol(self):
        with patch.object(database_manager, "get_supabase_client", return_value=self.client):
            coin = database_manager.get_market_data_by_symbol("btc")

        self.assertEqual(coin["symbol"], "BTC")


if __name__ == "__main__":
    unittest.main()
