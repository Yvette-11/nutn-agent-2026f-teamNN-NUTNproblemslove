**User Story：**
> 身為學生，我希望可以透過 AI Agent 回報校園問題，快速找到適當的負責單位並解決問題，而不需要自己花時間搜尋相關資訊。
# 南大智慧校園問題解決 Agent

本專題目標是讓學生以自然語言描述校園問題，
由系統判斷問題類型，搜尋固定校園資料，
並回傳負責單位與處理流程。

## User Story

身為國立臺南大學學生，
當我遇到校園行政、生活或設施相關問題時，
我希望可以直接描述問題，
讓系統協助判斷問題類型、負責單位與處理方式，
降低自行搜尋校方網站的成本。

## Scope

目前支援：
- 課務
- 學生證
- 宿舍
- 獎學金
- 校園設施

## Out of Scope

目前不包含：
- 即時爬取校方網站
- 登入校務系統
- 自動送出申請
- 自動報修
- 預約與付款

## System Flow

User Question
→ LLM Issue Analysis
→ Structured JSON
→ Fixed Campus Knowledge Base
→ Department / Procedure
→ Response

## Input

```json
{
  "question": "宿舍冷氣壞掉了，要找誰？"
}
openai
pydantic
python-dotenv
fastapi
uvicorn

OPENAI_API_KEY=your_api_key_here

.env
__pycache__/
*.pyc
.venv/
