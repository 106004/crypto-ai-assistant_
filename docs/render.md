# Render 說明

Render 是這個專案的主要部署平台。

## Render 的用途

Render 負責：

- 部署 Flask Web App
- 接收 LINE webhook
- 提供 `/callback`
- 提供 `/update-market-data`
- 執行排程相關服務

## Environment Variables

Render 上需要設定的環境變數，通常包括：

- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_CHANNEL_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GEMINI_API_KEY`

### 為什麼重要

這些值不能寫死在程式裡，因為：

- 會有安全風險
- 不方便換環境
- 一旦外洩會很麻煩

## 自動 deploy

Render 可以連 GitHub，自動部署最新程式碼。

常見流程：

1. 在本機修改程式
2. `git add`
3. `git commit`
4. `git push`
5. Render 偵測到 GitHub 更新
6. 自動重新部署

## free tier 睡眠問題

Render free tier 有可能睡眠。

這代表：

- 服務一段時間沒流量就可能休眠
- 第一次請求會比較慢
- LINE webhook 或定時更新可能受影響

## cron-job.org 為什麼需要

因為 free tier 服務不一定一直醒著，所以要靠外部排程固定喚醒 `/update-market-data`。

這樣可以確保：

- `market_data` 持續更新
- LINE 查詢時比較容易拿到新鮮資料

## logs 怎麼看

Render Logs 是除錯的重要來源。

你可以觀察這些前綴：

- `[PriceFlow]`
- `[Freshness]`
- `[Supabase]`
- `[MarketCollector]`
- `[ExternalCron]`
- `[Gemini]`
- `[Analyze]`

### 常見用途

- 看 LINE 查幣價是否只讀 Supabase
- 看 freshness check 有沒有把過期資料擋掉
- 看 market_collector 有沒有成功寫入
- 看 Gemini 有沒有 quota 問題

