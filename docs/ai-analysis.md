# AI 分析說明

這個專案有一個 `analyze btc` 指令，可以讓使用者看簡單的市場分析。

## Gemini API

目前 AI 分析主要使用 Gemini API。

輸入資料通常包含：

- `symbol`
- `name`
- `price_usd`
- `change_24h`
- `updated_at`

系統會先把 Supabase 讀到的資料整理成 prompt，再送給 Gemini。

## analyze btc

當使用者輸入：

```text
analyze btc
```

流程是：

1. `line_bot.py` 接到指令
2. 查 Supabase `market_data`
3. 做 freshness check
4. 資料夠新才送去 Gemini
5. 回傳 AI 分析文字給 LINE

## rule-based fallback

Gemini 有時會失敗，常見原因包括：

- quota exceeded
- 429 RESOURCE_EXHAUSTED
- timeout
- key missing
- 其他例外

這時候系統不能直接壞掉，所以會改用 `rule_based_analysis`。

### 為什麼要有 fallback

- 讓功能穩定
- 避免 AI 額度不足時整個分析不能用
- 讓使用者至少還能看到基本市場判讀

## AI quota 問題

AI API 不是永遠可用。

如果遇到 quota 問題：

- 不要回覆過期資料
- 不要硬送失敗訊息給使用者
- 要有穩定 fallback

## 為什麼需要 fallback

這個專案的原則是：

- 不要誤導使用者
- 不要因為 AI 不穩就完全失效
- 資料正確性比回覆速度更重要

所以設計成：

1. 先看 Gemini
2. Gemini 成功就回 AI 分析
3. Gemini 失敗就回規則分析

## CoinGlass links fallback

如果市場資料過期或不存在，價格查詢不應該回舊價格。

這時候會回：

- CoinGlass 幣種頁面連結

這比硬回一個可能不準的價格更安全。

