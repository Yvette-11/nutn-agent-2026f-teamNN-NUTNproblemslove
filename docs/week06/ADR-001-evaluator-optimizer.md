# ADR-001：以有限次 Evaluator–optimizer 檢查修繕回答

- 狀態：提案，待實作與測試
- 日期：2026-10-21
- Baseline SHA：ecad57e0e77fdb1d3757d6a430e7219c4ba23ad3

## 問題

Gemini 曾在宿舍空調修繕回答中補充 evidence 未提及的寢室房號要求。只在提示中要求「根據 evidence 回答」不足以保證所有回答內容都有依據。

## 決策

在唯讀查詢回答流程中採用 Evaluator–optimizer：
1. Evaluator 只根據本次工具 evidence 檢查初稿。
2. 初稿不合格時，提供具體 unsupported_claims 與修正回饋。
3. Optimizer 最多修訂一次。
4. 再以相同規準檢查；仍不合格就停止，記錄 GROUNDING_REJECTED。

本流程只提供 get_repair_information，不提供 create_repair_draft。

## 考慮過的替代方案

- 只加強 system prompt：修改成本低，但先前曾出現未受 evidence 支持的內容，因此單靠提示不足。
- 使用固定答案模板：可降低自行補充內容的風險，但回答彈性較低；可作為後續回退方案。
- 維持現有流程：不增加額外模型呼叫，但無法處理已觀察到的 unsupported claim。

## Scaffold 與資訊邊界

Evaluator 只收到本次問題、工具 evidence、待檢查初稿及固定評估規準；不提供舊請求或無關執行紀錄。每個事實主張須對應本次 evidence。驗證與修訂上限由 host 控制。寫入工具維持不可用。

## 代價與已知風險

- 比現有流程增加 Evaluator 模型呼叫；若需修訂，還會增加 Optimizer 與再次評估呼叫。
- 可能增加延遲、token 用量及 provider 失敗機會；目前尚未量測，完成測試後再填實際數據。
- Evaluator 也可能判斷錯誤，因此仍須用固定案例與 evidence 核對，不把模型自己的 pass 當作唯一證明。

## 停止與回退

- Provider、工具或 Evaluator 失敗：記錄錯誤並停止，不自動重試。
- 修訂一次後仍未通過：記錄 GROUNDING_REJECTED，不顯示未驗證答案。
- 候選流程未達驗收條件：保留 baseline SHA `ecad57e0e77fdb1d3757d6a430e7219c4ba23ad3`，不宣稱改善；由該基準還原或使用 Git revert 回退。

## 驗收條件

完成四條測試；正常流程的實際 Gemini 回答須由 evidence 支持。若未能通過，結論記為未通過或尚未驗證，不宣稱採用成功。