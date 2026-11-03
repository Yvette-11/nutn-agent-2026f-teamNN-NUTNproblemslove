## 南大智慧校園問題解決 Agent

專題簡介：本專題希望建立一個 AI Agent，協助國立臺南大學學生快速處理校園生活中遇到的問題。
學生只要輸入文字描述，例如：資誠樓三樓的飲水機沒有水。
Agent 會協助判斷問題類型、整理回報需要的資訊、建議可能負責的單位，並產生可直接使用的正式回報文字。

## 題目發想與最終選題
本組由兩位組員分別提出 AI Agent 專題題目，經討論後，選擇較符合「讓南大更好」目標、且適合課程實作的題目進行開發。

| 組員 | 學號 | 初步題目 |

| 李怡萱 | S11182001 | 南大智慧校園問題解決 Agent |

| 張傑 | S11182016 | 大學生智慧時間規劃 Agent |

### 題目一：南大智慧校園問題解決 Agent
學生描述在校園中遇到的問題後，Agent 可自主判斷問題類型、搜尋相關資訊、尋找可能的負責單位、整理處理流程，並生成回報內容。

**User Story：**
> 身為學生，我希望可以透過 AI Agent 回報校園問題，快速找到適當的負責單位並解決問題，而不需要自己花時間搜尋相關資訊。


### 題目二：大學生智慧時間規劃 Agent
大學生除了課業外，常常還需要兼顧打工、社團、活動與私人行程，因此容易出現時間分配不均、讀書計畫難以維持，以及臨時行程變動後需要重新安排的問題。
此 Agent 可蒐集課程與行程資訊、分析任務的重要性與截止時間、自主安排讀書計畫、追蹤完成進度，並在臨時行程或任務變動時重新規劃。

**User Story：**
> 身為一名可能同時需要兼顧課業、打工與社團的大學生，我希望能透過 AI Agent 協助規劃讀書時間與每日行程，合理分配可使用的時間，降低自行安排課表與調整計畫的成本，讓我能更專注在實際學習上。

### 最終選題與原因
經討論後，本組決定執行：**南大智慧校園問題解決 Agent**

選擇原因如下：
1. 題目直接回應「如何讓南大更好」，與課程要求高度相關。
2. 能解決學生不知道回報單位、流程與回報格式的實際問題。
3. Agent 可展現資訊蒐集、問題分類、判斷、規劃與生成回報內容等能力。
4. 題目範圍明確，適合在課程期間完成可操作的原型。

## 組員與分工
| 姓名 | 學號 | GitHub 帳號 | 分工 |

| 李怡萱 | S11182001 | Yvette-11 | Agent 流程設計、Prompt 設計、問題分類、系統功能整合 |

| 張傑 | S11182016 | jamisonchang | 蒐集南大校園資料、整理負責單位與解決方式、介面設計、測試 |

# 10/6南大修繕 Agent｜本機示範版

這是一個可在 Windows 本機操作的 Python CLI 範例，包含：

- MCP stdio server：提供 `tools/list`、`tools/call`、`get_repair_information`、`create_repair_draft`。
- 修繕查詢：目前只支援學生宿舍空調，找不到 evidence 或輸入不支援時會停止。
- 本機草稿：先顯示內容，只有輸入「確認建立」才呼叫寫入工具；建立後會讀回核對。
- Gemini Live：可選擇透過 Gemini API 做真實 function calling；不提供寫入工具給模型。
- 重現失敗：選單 4 會送出空白問題描述，留下 MCP validation failure 紀錄。

> `knowledge.json` 已整理專題 GitHub 中 `week4-fixed queries、chunk.md` 的三段固定 chunks，查詢結果會回傳 chunk 原文、標題、source_id 與 chunk_id。提交前請確認該 GitHub 文件仍是組員認可的 Week 3 evidence 版本。

## 不用 API key 就能先操作

- 輸入 `5`：列出 MCP tools，存一筆 `MCP_TOOLS_LIST` 紀錄。
- 輸入 `1`：查詢；可試「宿舍冷氣壞掉了」和「學生宿舍」。
- 輸入 `2`：在成功查詢後建立本機草稿。輸入完整的「確認建立」才會寫入。
- 輸入 `4`：重現空白問題描述的失敗案例。這是本機 MCP validation failure，不會冒充 Gemini Live failure。
- 輸入 `0`：離開。

每次操作的 JSON 紀錄會寫在 `runs/`。草稿放在 `drafts/`。請用虛構樓棟／測試資料做課堂展示；不要把個資、API key 或 `.env` 上傳。

## 設定 Gemini Live

程式只把 `get_repair_information` 唯讀函式提供給 Gemini。模型回傳 function call 後，Host 透過本機 MCP server 執行，將結果回傳 Gemini，再顯示最終摘要。寫入工具不提供給模型。成功／失敗紀錄會分別標記 `LIVE_PASS`／`LIVE_FAIL`；沒有 key 時不會假裝已做 live 測試。

Gemini Live 會透過 HTTPS 傳送你輸入的問題和地點給 Google Gemini API，並可能產生 API 用量。避免輸入房號、姓名或其他不必要的個人資訊。

### SHA

5aa6e99f95300a6504924bdca253f6a8bc216bb0

___________________________
## 環境設定

- Windows、Python 3.11 以上版本。
- 本程式只使用 Python 標準函式庫，不需另外安裝套件。
- 解壓縮專案，保留 `main.py`、`mcp_server.py`、`knowledge.json` 等檔案。

確認 Python 版本：

```powershell
py -3 --version
```

### Gemini 設定（選用）

離線功能不需要 API key。使用 Gemini Live 前，在專案資料夾執行：

```powershell
Copy-Item .env.example .env
notepad .env
```

填入設定並儲存：

```dotenv
GEMINI_API_KEY=自己的API金鑰
GEMINI_MODEL=帳號可用且支援function_calling的模型ID
```

修改後請重新啟動程式。不要將 `.env` 或金鑰上傳 GitHub。

## 啟動方式

雙擊 `start.bat`，或在專案資料夾開啟 PowerShell 執行：

```powershell
py -3 main.py
```

主程式會自動啟動 MCP Server，不需另外執行。

## 操作步驟

| 選項 | 功能 | 操作說明 |
|---|---|---|
| `1` | 查詢修繕資訊 | 輸入「宿舍冷氣壞掉了」及「學生宿舍」 |
| `2` | 建立本機草稿 | 先成功查詢，再填寫單位與建築，輸入「確認建立」才寫入 |
| `3` | Gemini Live 查詢 | 需設定 API key；模型呼叫唯讀工具後產生摘要 |
| `4` | 重現輸入錯誤 | 送出空白描述，檢查工具是否拒絕；不呼叫 Gemini |
| `5` | 查看 MCP 工具 | 列出查詢與草稿工具 |
| `0` | 離開 | 結束程式 |

建立草稿時，直接按 Enter 可沿用查詢的問題與地點；若要修改，請先重新查詢。未輸入「確認建立」就會取消寫入。

## 輸出與限制

- `runs/`：本次操作紀錄。
- `drafts/`：本機 Markdown 草稿。
- `evidence/`：歷史測試證據，不代表本次已重新測試。
- 目前僅支援固定資料中的「學生宿舍空調修繕」，不查即時狀態、不送出正式報修。
- Gemini 的 `LIVE_PASS` 表示模型與工具往返完成，不代表已報修或答案完全正確。
- 測試請使用虛構資料；分享紀錄前先清除個資與金鑰。

若無法啟動，請確認 Python 已安裝；Gemini 失敗時，請查看 `runs/` 的錯誤，檢查金鑰、模型、配額與網路。
