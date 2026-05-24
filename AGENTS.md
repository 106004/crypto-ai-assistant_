# 專案背景

這是一個 AI Crypto LINE Bot 專案。

目前功能包含：
- LINE Bot webhook
- Supabase users table
- Supabase market_data table
- CoinGecko market_collector
- cron-job.org 外部定時觸發
- Render 雲端部署
- Gemini AI 市場分析
- rule-based analysis fallback
- CoinGlass fallback links
- freshness check
- UTC 時間判斷
- set coin / mycoin / onboarding

# 技術架構

使用：
- Python
- Flask
- LINE Messaging API
- Supabase
- Render
- cron-job.org
- Gemini API
- CoinGecko API
- GitHub

# 核心資料流

市場資料更新：
cron-job.org
→ Render /update-market-data
→ market_collector.py
→ CoinGecko
→ Supabase market_data

LINE 查幣價：
LINE 使用者
→ /callback
→ line_bot.py
→ Supabase market_data
→ freshness check
→ fresh 則回價格
→ stale/missing 則回 CoinGlass links

AI 分析：
analyze btc
→ Supabase market_data
→ freshness check
→ Gemini
→ 如果 Gemini 失敗，改用 rule_based_analysis

# 重要規則

1. 不可以把 .env 加入 Git。
2. 不可以把 API key、token、service role key 寫死在程式碼。
3. 新增環境變數時，要提醒同步到 Render Environment Variables。
4. 修改 requirements.txt 後，要提醒 git add / commit / push，並讓 Render redeploy。
5. 不要破壞 LINE webhook /callback。
6. 不要破壞 /update-market-data。
7. 不要破壞 Supabase users 與 market_data 的資料流。
8. LINE 查幣價時，不要再讀 JSON，不要即時呼叫 API，只能讀 Supabase。
9. 如果 Supabase 資料超過 5 分鐘，不可以回覆舊價格。
10. 過期資料要回 CoinGlass links。
11. 時間判斷一律使用 UTC timezone-aware datetime。
12. 台灣時間只能用於顯示，不可用於 freshness check。
13. Gemini 失敗時要 fallback 到 rule_based_analysis。
14. 所有重要流程都要加 logs。
15. logs 格式盡量使用：
[PriceFlow]
[Freshness]
[Supabase]
[MarketCollector]
[ExternalCron]
[Gemini]
[Analyze]

# 開發習慣

每次修改前：
- 先說明會改哪些檔案
- 不要一次改太大範圍
- 不要新增無用檔案
- 不要刪除現有功能
- 修改完要列出測試方式

# 部署提醒

每次完成修改後，提醒我執行：

git add .
git commit -m "描述這次修改"
git push

# 優先級

穩定性 > 功能數量
資料正確性 > 回覆速度
不要誤導使用者 > 勉強回覆價格

# Subagents

遇到相關任務時，請先套用對應 subagent 角色思考。

- `backend-agent`：`app.py`、LINE webhook、`line_bot.py`、指令解析
- `database-agent`：Supabase、`database_manager.py`、freshness check、UTC 判斷
- `deploy-agent`：Render、環境變數、`cron-job.org`、`requirements.txt`
- `ai-agent`：Gemini、`market_analyzer.py`、fallback 分析
- `qa-agent`：只做 review、test plan、bug risk analysis，不直接新增功能
