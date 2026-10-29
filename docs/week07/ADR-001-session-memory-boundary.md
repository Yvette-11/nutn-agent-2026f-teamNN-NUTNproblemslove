# ADR-001：修繕查詢結果採用 Session 範圍記憶

## 狀態

Proposed

## 背景與問題

`main()` 以 `last_read` 保存最近一次成功查詢，讓使用者接著建立草稿。
若新查詢或失敗測試後仍保留舊結果，選項 2 可能使用過期 evidence 建立草稿。

## 決策

採用 Week 07 路線 C：清除 Session 記憶。

- `last_read` 只存在目前程式執行期間，不寫入磁碟。
- 開始新查詢或重現失敗案例前，先清除舊的 `last_read`。
- 只有成功查詢才會設定新的 `last_read`。
- 沒有目前 Session 的成功查詢時，草稿流程停止並記錄 `BLOCKED_NO_CURRENT_READ`。
- 程式重新啟動後，`last_read` 從空狀態開始。

## 修改範圍

- `main.py`：選單中的 `last_read` 清除與更新時機。
- `main.py`：`create_draft` 的無有效查詢結果防護及紀錄。

## 替代方案

- 持久化使用者偏好：本專題目前不需要跨任務保存學生個人資料，故不採用。
- 設定 TTL：目前狀態只存在單次 CLI 執行期間，重啟即清空；額外時間型期限會增加實作成本，故不採用。

## 取捨與限制

- 優點：失敗後不能沿用舊查詢結果，重新啟動也不保留資料。
- 代價：查詢失敗後必須重新查詢才能建立草稿。
- 限制：本 CLI 沒有登入或使用者身分，因此本 ADR 驗證的是 Session 隔離，不宣稱已驗證多使用者隔離。

## 驗證證據

- 同一 Session：成功查詢後重現失敗，再選擇建立草稿，結果為 `BLOCKED_NO_CURRENT_READ`。
- 新 Session：上一個程式執行期間查詢後退出；重新啟動直接選擇建立草稿，結果為 `BLOCKED_NO_CURRENT_READ`。
- Gemini Live 正常流程仍待成功驗證；已知 503 失敗另記於 Week 07 README。

## 回復方式

移除 Session 清除增量並還原 Week 07 Baseline SHA：
`4bdf14e3ac6cd95c891f44e06defe4c211618135`