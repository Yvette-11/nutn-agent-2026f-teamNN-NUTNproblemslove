# Week 05 CLI Baseline and Test Results

## Scope

This repository currently runs an interactive local CLI, not the HTTP `POST /assistant/campus-problem` API described in an earlier project draft. The implemented fixed-data query supports student dormitory air-conditioning repair. Gemini Live is read-only and does not receive the draft-writing tool.

## Fixed test cases

| Case | Input/action | Expected result |
|---|---|---|
| AC01 | Select `3`; problem `宿舍冷氣壞掉了`; location `學生宿舍` | Gemini calls `get_repair_information` once, grounds the answer in returned evidence, reports `LIVE_PASS`, and performs no write. |
| AC02 | Select `4` to send an empty problem description | MCP returns `INVALID_INPUT`; write tool is not called and no draft is created. This is a local validation failure, not a Gemini Live failure. |
| AC03 | Complete a read, select `2`, then decline the proposal | The app says the action was cancelled; write tool is not called and no draft is created. |

## Baseline results (before LangChain refactor)

Baseline revision: `5bdcb357e4b1cdfb4e5498461ffadf35251e4b35` (branch `week05-framework-refactor`, the committed state before the current uncommitted refactor).

| Case | Result | Record |
|---|---|---|
| AC01 | Historical success: `LIVE_PASS`; an additional run failed because the provider reported high demand. Both outcomes are retained; the failure does not erase the earlier success. | Success `979fe9e1340646f79469819effa6b63d` (`evidence/gemini live_pass.json`); high-demand failure `a6319d0239df49268b653c87babfa5be` (`runs/`). Other historical failures: timeout `9797ee59bd0b460f8b0d8191719309f9`, bad request `9769daeb99284d848d5f230e1d768560` (both in `evidence/`). |
| AC02 | PASS: validation returned `INVALID_INPUT`; no write. | `0d09305d577e4ead9b2c44a3320fbf03` (`runs/`). |
| AC03 | PASS: user declined; no write and no draft. | `1401fb55939e4ab3a9f3a60ec392162d` (`runs/`). |

## LangChain candidate results (current uncommitted working tree)

| Case | Result | Record |
|---|---|---|
| AC01 | 第一次 LIVE_PASS，但回答加入 evidence 未支持的房號資訊，grounding 未通過；第二次 LIVE_FAIL，錯誤為 504 DEADLINE_EXCEEDED，沒有產生回答。 | 第一次 run_id：e3cbb967d93a492c8fd66c386948f6d6；第二次 run_id：de24df7ed24f4d05946bba3cc70fd8f5。結論：尚未驗證通過。 |
| AC02 | PASS: same validation failure behavior, no write. | `278fac3dba724daf9f06062e7051e707` (`runs/`). |
| AC03 | PASS: user declined; no write and no draft. | `c64ac6f123584604b6fe8a6aec6c7e76` (`runs/`). |

The earlier baseline Live failure `a6319d0239df49268b653c87babfa5be` was caused by temporary provider high demand. The first candidate Live run confirmed the framework tool loop works but failed grounding review because the answer added an unsupported room-number requirement. A second candidate run used the corrected location after the prompt change, but the provider returned `504 DEADLINE_EXCEEDED`; no answer was available for grounding review. The prompt change therefore remains unvalidated. Do not repeatedly retry the provider failure or relabel it as a successful run.

## Evidence to preserve for each run

- commit SHA (for this uncommitted candidate, label it as working tree and record the SHA only after committing)
- case ID, exact input/action, framework path, run ID, actual status
- model and tool calls for Live runs; returned source/chunk IDs when present
- whether any write ran and whether a draft file was created

`runs/` contains local runtime records and is ignored by Git. Copy only sanitized records needed for submission into `evidence/`; never include `.env` or API keys.
