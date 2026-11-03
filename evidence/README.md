# 期中報告示範證據索引

分支：`week07-memory`
本機 MCP 示範影片錄製版本：`cb6e4cd`（影片檔名也標有此版本）
ADC／Vertex AI 測試程式版本：`a26c5f219bf84e7dffcfbffc3e141a32d1d3a8e3`
錄製日期：2026-11-03

## 本機 MCP 示範影片

| 檔案 | 案例 | 說明 |
|---|---|---|
| `本機MCP查詢與草稿成功示範_壓縮版_2026-11-03_cb6e4cd.mp4` | 本機 MCP 正常流程 | 展示 tools/list、修繕資訊查詢與 evidence 回傳、建立本機草稿及讀回核對。這是本機 MCP 示範，不代表 Gemini Live 或 Google Cloud／ADC 驗收通過。 |
| `本機MCP空白輸入驗證失敗_2026-11-03_cb6e4cd.mp4` | 本機 MCP 輸入驗證失敗 | 空白問題描述被拒絕並回傳 `INVALID_INPUT`；不代表 Gemini Live 失敗案例。 |

## 限制與待補驗證

- 以上影片是本機 CLI／MCP 操作錄影。
- Gemini Live 的實際結果需依各次執行紀錄標示 `LIVE_PASS`、`LIVE_FAIL` 或 `LIVE_NOT_RUN`。
- 2026-11-04 ADC／Vertex AI 實際呼叫：`LIVE_FAIL`，run_id=`e53eeb6ac8ac4f27986cf79246f5026b`。錯誤原因為 `BILLING_DISABLED`；請求在模型回覆前被拒絕，`tool_calls` 為空，未取得工具結果，`write_executed=false`。本次不啟用計費，因此目前沒有 ADC `LIVE_PASS`。執行紀錄：[gemini_live_adc_fail_billing_disabled.json](gemini_live_adc_fail_billing_disabled.json)