# Supabase 說明

Supabase 是這個專案的主要資料庫。

## users table

`users` table 主要存使用者相關資料，例如：

- LINE user id
- 使用者設定
- `set coin`
- `mycoin`
- onboarding 狀態

## market_data table

`market_data` table 主要存市場資料，例如：

- 幣種 symbol
- 幣名
- 價格
- 24H 漲跌
- `updated_at`

這張表是 LINE 查幣價的唯一來源。

## service role key

`SUPABASE_SERVICE_ROLE_KEY` 是高權限金鑰。

### 注意事項

- 只能放在環境變數
- 不可以寫進程式碼
- 不可以提交到 Git

## freshness check

查詢價格時，系統會先檢查 `updated_at`。

判斷原則：

- 5 分鐘內：視為新鮮
- 超過 5 分鐘：視為過期

這樣可以避免回覆舊價格誤導使用者。

## UTC 時間

時間判斷一律使用 UTC timezone-aware datetime。

原因：

- Supabase 回來的時間多半是 UTC
- 不同地區時間容易混淆
- 台灣時間只能用在顯示，不可以拿來判斷過期

## 為什麼不用 JSON

現在不再用 `data/market_data.json` 當查價 fallback。

原因：

- JSON 不是即時資料庫
- 容易和 Supabase 不一致
- 不利於 freshness check
- 容易造成舊資料誤判

## 為什麼不直接查 API

LINE 使用者查幣價時，不直接打 CoinGecko 或其他 API。

原因：

- 即時 API 可能 429
- 可能 quota exceeded
- 延遲較高
- 容易讓使用者查詢時失敗

所以目前流程是：

1. 背景用 `market_collector.py` 更新 Supabase
2. LINE 查詢只讀 Supabase
3. 過期或缺資料就改走 CoinGlass links

