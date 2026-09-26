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

## 1. Purpose

本文件定義「南大智慧校園問題解決 Agent」的輸入與輸出格式。
系統接收學生以自然語言描述的校園問題，判斷問題類型，並回傳對應的負責單位與處理流程。

---
## 2. Input

### Request Format

系統接收 JSON 格式資料：

```json
{
  "question": "宿舍冷氣壞掉了，要找誰？"
}

**##三個案例**

# Acceptance Cases

本文件定義「南大智慧校園問題解決 Agent」Baseline v0.1 的三個驗收案例。

---

## Case 1：200 Success

### Purpose

驗證系統在收到有效的校園問題，且固定資料中存在對應資訊時，能正確完成問題分析並回傳處理結果。

### Given

- 系統正常運作
- LLM 服務可正常使用
- 固定資料中存在「學生證遺失」相關資訊

### When

輸入：

```json
{
  "question": "我的學生證不見了，要怎麼辦？"
}
```

### Then

系統應回傳：

```text
HTTP 200 OK
```

並符合以下條件：

- `status` = `success`
- `category` = `學生證`
- `issue` 不可為空
- `department` 不可為空
- `procedure` 至少包含一個步驟
- 系統不可發生 crash

---

## Case 2：422 Invalid Input

### Purpose

驗證系統在收到不合法輸入時，能正確拒絕處理，並回傳明確的錯誤資訊。

### Given

- `question` 為必要欄位
- `question` 不可為空字串

### When

輸入：

```json
{
  "question": ""
}
```

### Then

系統應回傳：

```text
HTTP 422 Unprocessable Entity
```

並符合以下條件：

- `status` = `error`
- `error` = `INVALID_INPUT`
- 系統不呼叫 LLM
- 系統不進行校園資料搜尋
- 系統不可發生 crash

---

## Case 3：502 LLM Service Error

### Purpose

驗證 LLM 或外部服務失敗時，系統能正確處理錯誤，而不是讓整個系統中止。

### Given

- 使用者提供合法問題
- 系統需要呼叫 LLM 進行問題分析
- 模擬 LLM API timeout、連線錯誤或回傳無法解析的格式

### When

輸入：

```json
{
  "question": "宿舍冷氣壞掉了，要找誰？"
}
```

### Then

系統應回傳：

```text
HTTP 502 Bad Gateway
```

並符合以下條件：

- `status` = `error`
- `error` = `LLM_SERVICE_ERROR`
- 系統不可發生 crash
- 系統應回傳可理解的錯誤訊息
- 系統應記錄錯誤供後續除錯

---

## Acceptance Summary

| Case | 測試內容 | 預期 HTTP Status |
|---|---|---:|
| Case 1 | 有效校園問題，正常完成處理 | `200` |
| Case 2 | `question` 缺失或為空 | `422` |
| Case 3 | LLM / 外部服務失敗 | `502` |

---

## Evidence Status

目前狀態：`預期 / 未完整實測`

待程式完成並實際執行後，再補上：

- 實際 Request
- 實際 Response
- 執行指令
- HTTP Status
- 測試結果




**BASELINE**

# Baseline and Known Failure

## Baseline

### Baseline Name

`Baseline v0.1`

### Baseline Type

LLM 問題理解 + 固定校園資料查詢

### Description

系統接收學生以自然語言描述的校園問題，由 LLM 判斷問題類型，再從固定校園資料中取得負責單位與處理流程。

目前支援：

- 課務
- 學生證
- 宿舍
- 獎學金
- 校園設施

### System Flow

```text
學生輸入問題
    ↓
LLM 分析問題
    ↓
查詢固定校園資料
    ↓
回傳負責單位與處理流程



**證據狀態**

# Evidence Status

本文件記錄「南大智慧校園問題解決 Agent」Baseline v0.1 的驗證證據狀態。

---

## Current Status

目前狀態：`預期 / 未完整實測`

目前已完成：

- User Story
- Scope / Out of Scope
- Fixed Data
- I/O Contract
- Acceptance Cases
- Baseline
- Known Failure

目前尚未完成：

- 實際執行程式
- 實際 HTTP Response 紀錄
- 實際錯誤案例測試
- 測試結果截圖或紀錄

---

## Evidence To Be Collected

完成程式實作後，需補上：

- 實際執行指令
- 實際 Input
- 實際 Output
- HTTP Status Code
- 測試是否通過
- 錯誤訊息或失敗紀錄

---

## Expected Evidence

### Case 1：200 Success

應記錄：

- 輸入問題
- 實際 Response
- HTTP `200`
- 是否符合 Acceptance Criteria

### Case 2：422 Invalid Input

應記錄：

- 空白或缺少 `question` 的輸入
- 實際 Response
- HTTP `422`
- 是否未呼叫 LLM

### Case 3：502 LLM Service Error

應記錄：

- 合法問題輸入
- 模擬 LLM 服務失敗
- 實際 Response
- HTTP `502`
- 系統是否正常處理錯誤

---

## Evidence Status Summary

| 項目 | 狀態 |
|---|---|
| 規格文件 | 已完成 |
| 固定資料 | 已建立 |
| 驗收案例 | 已定義 |
| 程式實測 | 尚未完成 |
| HTTP 結果 | 尚未完成 |
| 錯誤處理實測 | 尚未完成 |

