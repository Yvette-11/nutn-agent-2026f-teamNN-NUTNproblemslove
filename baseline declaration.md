## User Story

身為國立臺南大學學生，
當我遇到校園行政、生活或設施相關問題時，
我希望可以直接描述問題，
讓系統協助判斷問題類型、負責單位與處理方式，
降低自行搜尋校方網站的成本。

## 範圍與固定資料

**In Scope**

- 冷氣故障 → 設備問題 → 總務相關單位 → 設備報修
- 飲水機故障 → 設備問題 → 總務相關單位 → 設備維修
- 教室燈光故障 → 設備問題 → 總務相關單位 → 設備維修
- 校園環境髒亂 → 環境問題 → 清潔相關單位 → 環境回報

**Out of Scope**

- 不即時爬取校方網站
- 不登入校務系統
- 不自動送出申請
- 不處理真實校園問題
- 不使用學生個人資料

**固定情境**

2030-06-17 10:00，學生在南大校園發現教室冷氣故障。

## 輸入/輸出協定
**Purpose**：

本文件定義「南大智慧校園問題解決 Agent」的輸入與輸出格式。
系統接收學生以自然語言描述的校園問題，判斷問題類型，並回傳對應的負責單位與處理流程。

### 1. Input(Request Format)

```
{
  "query": "我在教室上課，冷氣壞掉了，應該找誰處理？",
  "location": "南大教室",
  "problem_type": "設備故障",
  "model_profile": "mock-fast",
  "teaching_case": "normal"
}
```

### 2.output(Response)

```
can_handle: true

problem_category: "設備故障"
problem_name: "冷氣故障"

department: "總務相關單位"
recommendation: "建議提交校園設備報修"

reason: "根據輸入內容判斷為校園設備故障。"

HTTP: 200
```

## 三個驗收案例

### Case 1：AC01

Given（前置條件）
已建立固定校園資料，包含冷氣故障對應的問題類型、負責單位及建議處理方式。

When（執行動作）
學生輸入「教室冷氣壞掉了，應該找誰處理？」，且 teaching_case=normal。

Then（預期結果）
- HTTP：200
- can_handle=true
- problem_category="設備故障"
- department="總務相關單位"
- recommendation="建議提交校園設備報修"

### Case 2：AC02

Given（前置條件）
Request 的其他欄位與 AC01 相同，但 query 為空字串，違反必填欄位規則。

When（執行動作）
學生送出 POST /assistant/campus-problem。

Then（預期結果）
- HTTP：422
- Request validation 停止
- 回傳欄位驗證錯誤
- Agent 不執行問題分類或推薦

### Case 3：AC03

Given（前置條件）
Request 格式合法，但固定校園資料中沒有該問題的對應紀錄，且 teaching_case=ungrounded。

When（執行動作）
學生輸入「教室冷氣壞掉了，應該找誰處理？」並送出 Request。

Then（預期結果）
- HTTP：502（依照課堂指定的測試情境）
- 不產生未經資料支持的負責單位或解決方式
- 回傳錯誤訊息，說明目前無法根據固定資料提供建議

## Baseline and Known Failure

### Baseline

**固定輸入**
```
{
  "query": "教室冷氣壞掉了，應該找誰處理？",
  "location": "南大教室",
  "problem_type": "設備故障",
  "model_profile": "mock-fast",
  "teaching_case": "normal"
}
```
**預期輸出**
```
HTTP: 200
can_handle: true
problem_category: 設備故障
department: 總務相關單位
recommendation: 建議提交校園設備報修
```

### Failure

測試情境：資料依據不足
```teaching_case = "ungrounded"```

預期結果：
- HTTP：502（課堂測試設定）
- 不得產生沒有資料支持的負責單位或解決方式。
- 回傳錯誤訊息，說明資料不足。

## Evidence Status

目前狀態：`預期 / 未完整實測`
