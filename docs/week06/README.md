# Week 06 Workflow 增量紀錄

## 原專案與基準
- 專案：南大智慧校園問題解決 Agent
- 工作分支：week06-workflow
- Baseline SHA：ecad57e0e77fdb1d3757d6a430e7219c4ba23ad3
- 本次只改善：學生宿舍空調的唯讀查詢回答流程
- 業務終點：回覆有 evidence 支持的修繕資訊；不建立或送出報修

## 原流程缺口
Gemini 曾在回答中加入 evidence 沒有提及的寢室房號要求。回答必須能逐項對應工具回傳的 evidence。

## 選擇的 Workflow
Evaluator–optimizer。檢查初稿的事實主張是否都有 evidence 支持；若有不支持的內容，提供具體回饋，最多修訂一次，再用相同規準檢查。修訂後仍不符合就停止並揭露，不輸出為已驗證答案。

## 固定正常案例
- 問題描述：宿舍冷氣壞掉了
- 地點：學生宿舍
- 工具：只允許唯讀 get_repair_information
- 寫入工具：本流程不呼叫 create_repair_draft

## 待測案例
1. 正常查詢：實際呼叫 Gemini 和唯讀工具，檢查回答及 evidence。
2. 非法輸入：拒絕請求，不沿用舊結果，也不呼叫工具。
3. Provider 或工具失敗：有限停止並記錄實際錯誤。
4. Workflow 邊界：初稿含 evidence 不支持的房號要求；最多修訂一次，未通過就停止。

## 評估規準與停止條件（規劃）

### 評估規準
Evaluator 只使用本次 get_repair_information 回傳的資料檢查初稿。

回答必須符合以下條件才算通過：
- 報修系統名稱與 repair_system 一致。
- 申請類別與 repair_category 一致。
- 所需資訊只能列出 required_information 已提供的項目，不可自行增加。
- 每項事實主張都能對應到一個或多個 evidence chunks。
- 不可聲稱已建立草稿或已送出正式報修。
- 不可補充 chunks 未提及的棟別、寢室、房號、聯絡方式或處理時限。

### Evaluator 輸出
Evaluator 必須回傳：
- verdict：pass 或 revise
- unsupported_claims：不受 evidence 支持的主張清單
- feedback：需要如何修正的具體說明

只有 verdict 為 pass，且 unsupported_claims 為空，才可顯示最終答案。

### 修訂上限與停止
- 初稿不通過時，將 unsupported_claims 和 feedback 提供給 Optimizer。
- 最多修訂一次，再以相同規準評估。
- 第二次仍不通過時，停止輸出答案，記錄 GROUNDING_REJECTED；保存初稿、評估結果與修訂稿供追蹤。
- Provider、工具或 Evaluator 發生錯誤時，停止並記錄實際錯誤，不自動重試。
- 此流程只使用唯讀查詢工具，不呼叫 create_repair_draft。

### 狀態
規格已定義；程式實作與測試尚未執行。

## 原流程、程式位置與預計差異

| 檔案／函式 | 目前用途 | 本週處理 |
|---|---|---|
| main.py：gemini_live_read | Gemini 透過 LangChain 呼叫唯讀查詢工具並產生回答 | 修改：在初稿後加入 evaluator；最多修訂一次並重新評估 |
| main.py：MCPClient.call_tool | 透過 MCP client 執行工具 | 保留：沿用既有工具呼叫方式 |
| main.py：unpack_tool_result | 解析 MCP 工具回傳內容 | 保留：沿用既有解析方式 |
| main.py：save_run | 儲存每次執行紀錄 | 擴充：加入初稿、評估結果、修訂次數與最終狀態 |
| mcp_server.py：get_repair_information | 驗證問題並回傳固定 evidence | 保留：作為查詢 evidence 的來源 |
| mcp_server.py：create_repair_draft | 建立本機報修草稿 | 保留但不納入本週流程；Gemini 不可呼叫 |

## 前後流程

### Baseline
輸入 → Gemini 呼叫唯讀查詢 → MCP 回傳 evidence → Gemini 產生回答 → 記錄結果

### Candidate（規劃中）
輸入 → Gemini 呼叫唯讀查詢 → MCP 回傳 evidence → 產生初稿 A
→ Evaluator 依固定規準檢查
→ 通過：顯示答案
→ 未通過：Optimizer 最多修訂一次，再用同一規準評估
→ 仍未通過：停止並記錄 GROUNDING_REJECTED

Candidate 尚未實作或測試。

## 四條必備測試（目前都尚未執行）

| 案例 | 測試輸入／方式 | 預期結果 | 實際結果 |
|---|---|---|---|
| 1. 正常流程 | 真實 Gemini；問題「宿舍冷氣壞掉了」；地點「學生宿舍」 | 呼叫唯讀查詢工具，回傳 source_id 與 chunk_ids；回答只包含 evidence 支持的資訊；不呼叫寫入工具 | NOT_RUN |
| 2. 非法輸入 | 使用現有選單 4 重現空白問題描述 | 回傳 INVALID_INPUT；不使用舊結果；不呼叫寫入工具；停止原因有紀錄 | PASS；run_id=350c06d3c1124675937703b6ef802ade；status=EXPECTED_TOOL_ERROR；回傳 INVALID_INPUT；write_executed=false；本機 MCP 驗證失敗，非 Gemini LIVE_FAIL。 |
| 3. Provider／工具失敗 | 以可重現的錯誤案例測試 provider 或工具失敗；與真實 Gemini 失敗紀錄分開 | 有限停止；保留錯誤來源與 stop reason；不自動重試、不產生未驗證答案 | PASS（注入失敗）；run_id=16ff64373aaa4633b003dbd5b86fe351；mode=INJECTED_PROVIDER_FAILURE；error_source=test_switch；tool_calls=0；write_executed=false；沒有自動重送；error=INJECTED_PROVIDER_FAILURE: Week 06 controlled failure test|
| 4. Evaluator–optimizer 邊界 | 使用測試資料讓初稿含「需要填寫寢室房號」等 evidence 未支持內容，且一次修訂後仍未移除 | Evaluator 判定不通過；最多修訂一次；停止並記錄 GROUNDING_REJECTED；不顯示未驗證答案、不呼叫寫入工具 | PASS（本機固定評估資料；共用評估流程）；run_id=99ec3880d8a146bfa7f2bc005513f722；status=GROUNDING_REJECTED；revision_attempts=1；evaluate=2；revise=1；answer_displayed=false；write_executed=false。此測試未呼叫 Gemini。 |

### 真實 Gemini provider failure（額外紀錄）

- 實際結果：`LIVE_FAIL`
- run_id：`7fba7dad059045de99b186d918b2b4bc`
- 錯誤：`503 UNAVAILABLE`
- 結果：本輪停止，沒有自動重送；未能驗證後續評估器流程。

## Baseline 與 Candidate 比較

### 流程差異

| 項目 | Week 05 Baseline | Week 06 Candidate |
|---|---|---|
| Agent 流程 | LangChain `create_agent` 呼叫唯讀修繕查詢工具，再產生回答 | 保留唯讀查詢；新增 evidence 評估、最多一次修訂、再次評估 |
| 未受 evidence 支持的內容 | Baseline 曾出現 evidence 未支持的「寢室房號」要求 | 共用評估流程若修訂後仍不通過，回傳 `GROUNDING_REJECTED` 並停止顯示答案 |
| 寫入工具 | Gemini Live 流程不提供寫入工具 | Gemini Live 流程仍不提供寫入工具 |
| 本機邊界測試 | 無 Week 06 共用評估流程測試 | 固定資料測試確認評估兩次、修訂一次，最後停止且不顯示答案、不寫入 |
| 正常 Live 流程 | 曾有 Live 執行紀錄 | 尚未取得成功紀錄；目前實測遇到 `503 UNAVAILABLE` |

### 實測紀錄與比較限制

- Week 06 固定資料邊界測試：`run_id=99ec3880d8a146bfa7f2bc005513f722`；結果為 `GROUNDING_REJECTED`；評估 2 次、修訂 1 次；未呼叫 Gemini。
- Week 06 注入失敗測試：`run_id=16ff64373aaa4633b003dbd5b86fe351`；結果為 `EXPECTED_INJECTED_FAILURE`；沒有呼叫工具，也沒有寫入。
- Week 06 真實 Gemini 呼叫：`run_id=7fba7dad059045de99b186d918b2b4bc`；結果為 `LIVE_FAIL`，錯誤為 `503 UNAVAILABLE`。

目前沒有取得同一模型、同一輸入、同一 evidence 下的 Baseline 與 Candidate 成功輸出，因此本次不能做公平的端到端回答品質、延遲或 token 用量比較。這些數值標記為「未測」，不推算改善幅度。

### 已知問題與後續計畫

- 正常 Gemini Live 案例尚未成功完成；目前保存的 503 是真實 Provider failure，不代表 Candidate 正常流程通過或失敗。
- Gemini 服務可用後，以相同問題「宿舍冷氣壞掉了」和地點「學生宿舍」重跑正常流程，記錄模型、`run_id`、工具呼叫、evidence 評估結果及回答。
- 若仍無法取得成功紀錄，保留 `NOT_RUN`／`LIVE_FAIL` 狀態與錯誤證據，並在提交時說明限制。

### 執行紀錄規則
- 每次實測填入實際狀態、run_id、版本／SHA、錯誤與寫入狀態。
- fixture 或注入錯誤標為 INJECTED／SIMULATED；不可冒充真實 Gemini 執行。
- Provider 真實失敗標為 LIVE_FAIL；不得改寫為成功。
- 本週只修改唯讀查詢流程，沒有新增寫入行為，因此目前不加第 5 條寫入重送測試。