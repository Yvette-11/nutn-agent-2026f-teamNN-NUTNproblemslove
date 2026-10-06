## proposal
user：國立臺南大學學生

情境：學生在校園中遇到設備故障問題，例如教室冷氣、燈光或飲水機故障，希望知道應該向哪個單位反映，以及可以採取什麼處理方式。

claim：南大學生遇到校園設備故障時，可以根據南大官方校園資訊，確認該問題應聯絡的負責單位與處理方式。

Data Scope：僅處理校園設備故障相關資訊，包含教室冷氣、照明、飲水機等設備，以及負責單位、回報方式與官方聯絡資訊。

Refusal Condition：若找不到相關 evidence、資料不足、來源衝突或資料已失效，Agent 不自行推測，回傳 ```INSUFFICIENT_EVIDENCE```。

## three fixed queries

### Case 1：Static Knowledge Retrieval

**Query**

```text
宿舍冷氣壞掉了，要怎麼報修？
```

**Expected Decision**

```text
需要外部校園知識 evidence
```

**Expected Route**

```text
static_knowledge_corpus
```

### Case 2：No Retrieval

**Query**

```text
請把我提供的冷氣報修公告整理得更簡短。
```

**Expected Decision**

```text
使用者已提供完整內容
```

**Expected Route**

```text
no_retrieval
```

### Case 3：Live Data Required

**Query**

```text
現在冷氣報修的承辦人員有值班嗎？
```

**Expected Decision**

```text
需要即時狀態資料
```

**Expected Route**

```text
live_data_source
```

### Summary

| Case | Query 類型 | Expected Route | Retrieval |
|---|---|---|---|
| Case 1 | 校園固定知識 | `static_knowledge_corpus` | Yes |
| Case 2 | 使用者已提供內容 | `no_retrieval` | No |
| Case 3 | 即時狀態 | `live_data_source` | No static retrieval |

## chunk
### Chunk 1

chunk_id: NUTN-DORM-REPAIR-001

title: 國立臺南大學修繕系統

source_id: NUTN-DORM-REPAIR

text:
國立臺南大學學生宿舍「宿舍修繕/網路」頁面提供「國立臺南大學修繕系統」入口，學生可透過該系統進行相關設備修繕申請。

supported_aspects:
- repair_system
- repair_method

### Chunk 2

chunk_id: NUTN-DORM-REPAIR-002

title: 空調設備相關修繕類別

source_id: NUTN-DORM-REPAIR

text:
國立臺南大學修繕系統提供「土木、空調或水電／其他維修」申告類別，可用於處理空調相關設備的修繕申請。

supported_aspects:
- repair_category
- air_conditioner_related

### Chunk 3

chunk_id: NUTN-DORM-REPAIR-003

title: 修繕申請所需資訊

source_id: NUTN-DORM-REPAIR

text:
進行國立臺南大學修繕申請時，系統要求填寫相關申請資訊，包括申請類別、單位、所在建築及故障情況，以提供修繕所需的問題與位置資訊。

supported_aspects:
- required_information
- repair_process
