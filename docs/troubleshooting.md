# Troubleshooting

這份文件整理這個專案常見問題，方便快速排查。

---

## 1. CoinGecko 429

### 症狀

- `market_collector.py` 抓資料失敗
- logs 出現 rate limit 類錯誤
- Supabase `market_data` 更新變慢或中斷

### 原因

- CoinGecko API 觸發頻率限制
- cron 太頻繁
- 當下 API 服務忙碌

### 解法

- 確認 `market_collector.py` 保留 API 抓取，但只用於背景更新
- 檢查 cron 頻率是否合理
- 看 logs 是否有 `CoinGecko API 查詢成功` 或錯誤訊息
- 必要時降低更新頻率或調整資料抓取策略

---

## 2. Gemini quota exceeded

### 症狀

- `analyze btc` 回覆失敗
- logs 出現 429 / quota exceeded / RESOURCE_EXHAUSTED

### 原因

- Gemini 額度不足
- API key 配額用完
- 服務暫時不可用

### 解法

- 確認 `market_analyzer.py` 已經有 fallback 到 `rule_based_analysis`
- 確認 logs 有 `[Gemini] API 呼叫失敗，改用規則分析`
- 不要讓分析功能直接失效

---

## 3. Render 睡眠

### 症狀

- LINE webhook 延遲變高
- `/update-market-data` 有時候沒準時跑
- 首次請求很慢

### 原因

- Render free tier 可能會睡眠

### 解法

- 使用 `cron-job.org` 定時打 `/update-market-data`
- 讓服務保持比較容易被喚醒
- 檢查 Render logs 是否有正常收到請求

---

## 4. timezone mismatch

### 症狀

- fresh 資料被誤判成過期
- 過期資料被誤判成新鮮

### 原因

- `updated_at` 和系統時間時區不一致
- naive datetime 被當成本機時間

### 解法

- 一律使用 UTC timezone-aware datetime
- 解析 `updated_at` 時，若是 naive datetime 就視為 UTC
- freshness check 不可使用台灣時間

---

## 5. stale data

### 症狀

- 查到的價格看起來不對
- 使用者看到過期行情

### 原因

- `market_data.updated_at` 超過 5 分鐘
- 背景更新暫時失敗

### 解法

- freshness check 超過 5 分鐘就不要回價格
- 改回 CoinGlass links
- 看 `market_collector.py` 和 cron-job.org 是否正常

---

## 6. Supabase permission denied

### 症狀

- 讀取或寫入 Supabase 失敗
- logs 顯示 permission denied / unauthorized

### 原因

- service role key 沒設好
- `.env` 與 Render Environment Variables 不一致

### 解法

- 檢查 `SUPABASE_URL`
- 檢查 `SUPABASE_SERVICE_ROLE_KEY`
- 確認沒有把 key 寫死在程式碼中

---

## 7. scheduler 沒運作

### 症狀

- 排程不會啟動
- market data 沒有定時更新

### 原因

- Flask reloader
- Render 休眠
- scheduler 啟動條件不對

### 解法

- 檢查 logs 是否有 scheduler 啟動訊息
- 確認 app 啟動流程沒有重複啟動 scheduler
- 搭配 `cron-job.org` 觸發 `/update-market-data`

---

## 8. cron-job.org 設定

### 症狀

- `/update-market-data` 沒有被打到
- Supabase `market_data` 沒有更新

### 原因

- cron URL 設錯
- method 設錯
- 排程時間間隔不正確

### 解法

- 確認 cron 指向正確的 Render URL
- 方法要符合後端預期
- 頻率保持每 5 分鐘
- 檢查 Render logs 是否有收到請求

---

## 快速檢查順序

1. 先看 logs 前綴
2. 再看 Supabase `market_data.updated_at`
3. 再看 freshness check 結果
4. 再看 Gemini 或 fallback 是否正常
5. 最後再查 Render 與 cron-job.org

