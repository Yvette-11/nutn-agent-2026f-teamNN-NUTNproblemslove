# Week 05 Refactoring Decision

## Decision

Evaluate LangChain `create_agent` as a replacement for the hand-written Gemini function-call orchestration loop in `gemini_live_read()`. Keep the current MCP stdio server/client and the local CLI. The candidate is **not yet approved for adoption**. A candidate Gemini Live run confirms the LangChain tool loop works, but the generated answer added an unsupported room-number requirement. The prompt has been tightened; a new Live run is still needed to check grounding.

## What changes and what stays

- **Replaced in the candidate:** manual Gemini request → function-call parsing → MCP call → follow-up request, with LangChain `create_agent` and `ChatGoogleGenerativeAI`.
- **Retained:** `get_repair_information` MCP implementation, fixed evidence and validation, `create_repair_draft`, explicit user confirmation, draft read-back verification, CLI, and run logging.
- **Permission boundary:** the agent receives only the read-only repair-information tool. It cannot access `create_repair_draft`.
- **Dependencies:** `langchain==1.4.6`; `langchain-google-genai==4.4.2` (see `requirements.txt`).
- **Timeout/retry behavior:** request timeout is 120 seconds; automatic retries are set to zero. A failed call is logged as `LIVE_FAIL`; no automatic resend is made.

## Comparison evidence

The committed baseline revision is `5bdcb357e4b1cdfb4e5498461ffadf35251e4b35`. Both paths use the same local MCP server, evidence, read/write tools, CLI cases, and write-confirmation rules. The candidate changes only Gemini orchestration. The LangChain candidate has been committed and pushed on branch `week05-framework-refactor`. Latest branch commit SHA: [b5d57ae93816c80a77c73bad29378ae43fc345ed].

| Case | Baseline | LangChain candidate | Comparison |
|---|---|---|---|
| AC01 Gemini Live read | Historical `LIVE_PASS`, run `979fe9e1340646f79469819effa6b63d`; later provider high-demand `LIVE_FAIL`, run `a6319d0239df49268b653c87babfa5be`. | First run: `LIVE_PASS`, run `e3cbb967d93a492c8fd66c386948f6d6`; one read-only call, evidence IDs returned, no write; location mistyped as `學生色設`, and answer added unsupported room-number instructions. Second run after prompt tightening, with correct location: `LIVE_FAIL`, run `de24df7ed24f4d05946bba3cc70fd8f5`, provider `504 DEADLINE_EXCEEDED`. | First orchestration succeeded but grounding review failed. Second run produced no answer, so grounding after the prompt change remains untested. Neither candidate run gives a clean same-input, grounded success. Records: `evidence/week05_langchain_live_pass_ungraded.json`, `evidence/week05_langchain_live_fail_504.json`. |
| AC02 empty description | `INVALID_INPUT`, no write; run `0d09305d577e4ead9b2c44a3320fbf03`. | `INVALID_INPUT`, no write; run `278fac3dba724daf9f06062e7051e707`. | Expected offline validation behavior preserved. |
| AC03 reject draft | No write/no draft; run `1401fb55939e4ab3a9f3a60ec392162d`. | No write/no draft; run `c64ac6f123584604b6fe8a6aec6c7e76`. | Expected offline approval behavior preserved. |

## Benefits, costs, and current finding

- **Potential benefit:** LangChain provides a framework-managed agent/tool execution loop, reducing the amount of orchestration code maintained by this project.
- **Measured benefit:** not established yet. The candidate is longer in this code diff and depends on two packages; no runtime, latency, or answer-quality comparison has been made.
- **Current finding:** keep as an experimental candidate / **needs Live validation**. Offline guardrails pass. The first candidate Live run was not fully grounded and used a mistyped location; the second run, after tightening the prompt and correcting the location, timed out with provider 504 before producing an answer. Therefore the prompt change has not yet been evaluated and a framework advantage is not established.

## Rollback and next steps

The existing committed baseline remains available on `main`. To discard the candidate and return to that baseline, switch to `main`; do not overwrite or delete the candidate branch. Before any adoption decision:

1. If quota and provider availability allow, make one later AC01 attempt using location exactly `學生宿舍`; save the actual Live record (including failure if the provider fails). Do not repeatedly retry the 504.
2. If a response is returned, check that it adds no details beyond the evidence, then compare tool-call count, evidence IDs, answer, status, and write flag against the baseline record.
3. Review the diff and decide adopt, retain baseline, or gather more evidence.
4. If adopting, commit the candidate and update this report with its commit SHA. Keep `.env` private; never commit it.
