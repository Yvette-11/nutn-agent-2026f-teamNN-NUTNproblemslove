# Week 07：Session 記憶增量

## Baseline

- Week 07 Baseline SHA：`4bdf14e3ac6cd95c891f44e06defe4c211618135`
- 原本流程：`main()` 以 `last_read` 保存最近一次成功查詢，供選項 2 建立草稿。
- 已知缺口：選項 3 Gemini Live 失敗、選項 4 驗證失敗時，舊的 `last_read` 可能仍存在。

## 選擇路線

- 路線 C：清除 session 記憶，避免失效資料繼續影響後續操作。
- 只修改目前程式執行期間的查詢狀態，不新增持久化個人記憶。

## Memory Contract

- 新查詢或失敗案例開始前，先清除舊的 `last_read`。
- 只有本次查詢成功，才保存新的 `last_read`。
- 新查詢失敗後，選項 2 不得使用先前查詢結果建立草稿。
- 程式重新啟動時，記憶從空狀態開始。
- 查詢結果不寫入長期記憶或個人資料檔。

## 固定測試情境

1. 成功查詢一次，確認選項 2 可使用該次結果。
2. 開始新的查詢但失敗，之後選項 2 應要求重新查詢，不得沿用前一次結果。
3. 重新啟動程式，確認選項 2 不得使用上一個 session 的結果。

### Session 清除測試結果

- 操作：選項 1 成功查詢 → 選項 4 重現輸入驗證失敗 → 選項 2 嘗試建立草稿
- 預期：要求先成功查詢；不顯示草稿預覽、不建立檔案
- 實際：PASS；顯示「請先在本次程式執行中成功查詢修繕資訊，再建立草稿。」
- 判定：失敗案例後舊查詢結果已清除；未呼叫寫入工具
- 證據：run_id=96b40faac0b44210b3265cde5626f5e6；status=BLOCKED_NO_CURRENT_READ；stop_reason=no_current_session_read；write_executed=false

### 新 session 隔離測試

- 操作：在第一個程式執行期間成功查詢並退出；重新啟動後直接選擇 2 建立草稿
- 預期：要求先在本次執行中成功查詢，不沿用上一個 session 的資料
- 實際：PASS；`status=BLOCKED_NO_CURRENT_READ`
- 證據：`run_id=9b75ad4b4e60458e9f4f7a7fbaf4d93b`；`stop_reason=no_current_session_read`；`write_executed=false`

## 狀態

- 程式修改：NOT_RUN
- 測試：NOT_RUN
- Candidate SHA：待完成後記錄

## Week 07 測試矩陣

| 案例 | 預期結果 | 實際結果／證據 |
|---|---|---|
| C01 正常主流程 | 原修繕任務正常完成；工具結果與回答一致 | LIVE_FAIL；run_id=4acfa6fe0e51458faf35b5bba3f43d4c；model=gemini-3.6-flash；error=503 UNAVAILABLE；本輪停止，未能驗證正常回答與 Evaluator 流程。 |
| C02 跨使用者隔離 | 不同使用者不能讀到彼此資料 | NOT_RUN／不適用：CLI 沒有登入或使用者身分；本週增量只使用 process-local session 記憶，未實作多使用者記憶儲存 |
| C03 同一 session 失敗後清除 | 新查詢失敗後，選項 2 不沿用舊查詢結果 | PASS；run_id=`96b40faac0b44210b3265cde5626f5e6`；status=`BLOCKED_NO_CURRENT_READ`；write_executed=`false` |
| C04 新 session 不沿用舊結果 | 重新啟動後，選項 2 不使用上一個 session 的查詢結果 | PASS；run_id=`9b75ad4b4e60458e9f4f7a7fbaf4d93b`；status=`BLOCKED_NO_CURRENT_READ`；write_executed=`false` |
| W01 未授權寫入 | 未確認時不建立草稿 | PASS；run_id=644e22025e6740f7a95423de77116ca6；accepted=false；executed=false；拒絕後沒有執行寫入。 |
| W02 同 ID 重送 | 相同 request ID 重送不增加副作用 | PASS；run_id=d0ffe27c2e7241a498dd5e7f5f103cda；request_id=REQ-WEEK07-IDEMPOTENCY-7CB50D4B；第一次 executed=true、replayed=false；重送 executed=false、replayed=true；兩次 draft_id 相同（REPAIR-DRAFT-A6D57CD6）；replay_created_new_draft=false。 |

## 目前限制

- C01 尚未取得 Week 07 Candidate 的真實 Gemini 成功紀錄。
- C02 因目前沒有使用者身分與多使用者儲存，不能宣稱已實測跨使用者隔離。
- W01、W02 尚待確認既有 Week 04 測試紀錄是否足以支援本週驗收。

## Baseline 與 Candidate 比較

| 比較項目 | Week 07 Baseline | Week 07 Candidate |
|---|---|---|
| 查詢記憶 | `last_read` 保存最近一次成功查詢；開始失敗測試或 Gemini Live 失敗時可能保留舊結果 | 新查詢或失敗測試開始前清除 `last_read`；只有本次成功查詢才保存新結果 |
| 草稿流程 | 有舊 `last_read` 時，可能使用過期查詢結果建立草稿 | 沒有本次 session 的成功查詢時，回傳 `BLOCKED_NO_CURRENT_READ`，不呼叫寫入工具 |
| Session 範圍 | 程式重新啟動後變數會重設 | 明確驗證重新啟動後不能沿用前一 session 的查詢結果 |
| Gemini 回答品質 | — | 尚無可比較的 Week 07 Gemini 成功結果；C01 仍待測 |
| 模型成本 | 未測 | Session 清除測試沒有呼叫 Gemini；tokens 與延遲未測 |

### 比較限制

本次已驗證 session 失敗後清除、新 session 不沿用舊結果，以及草稿拒絕與相同 request ID 重送。由於尚未取得 Week 07 Candidate 的正常 Gemini Live 成功紀錄，目前不能比較兩版的 Gemini 回答品質、tokens 或延遲。