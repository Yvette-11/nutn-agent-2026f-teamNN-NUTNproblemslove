"""Interactive host: CLI + Gemini function calling + local stdio MCP client."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parent
class GroundingEvaluation(BaseModel):
    verdict: Literal["pass", "revise"]
    unsupported_claims: list[str]
    feedback: str

def evaluate_grounding(
    chat_model: ChatGoogleGenerativeAI,
    problem: str,
    location: str,
    evidence: dict[str, Any],
    draft: str,
) -> GroundingEvaluation:
    evaluator = chat_model.with_structured_output(
        GroundingEvaluation.model_json_schema(),
        method="json_schema",
    )

    messages = [
        (
            "system",
            "你是回答內容的 evidence 評估器。"
            "只能用提供的 evidence 核對 draft 中的事實主張。"
            "若有任何主張無法由 evidence 支持，verdict 必須是 revise，"
            "並列出 unsupported_claims 和具體 feedback。"
            "若每項事實主張都受 evidence 支持，verdict 才能是 pass。"
            "不得自行補充資料。",
        ),
        (
            "human",
            f"問題：{problem}\n"
            f"地點：{location}\n"
            f"Evidence：{json.dumps(evidence, ensure_ascii=False)}\n"
            f"待評估回答：{draft}",
        ),
    ]

    result = evaluator.invoke(messages)
    return GroundingEvaluation.model_validate(result)

def grounding_passed(evaluation: GroundingEvaluation) -> bool:
    return (
        evaluation.verdict == "pass"
        and not evaluation.unsupported_claims
    )

def run_grounding_cycle(
    draft: str,
    evaluate: Callable[[str], GroundingEvaluation],
    revise: Callable[[str, GroundingEvaluation], str],
) -> dict[str, Any]:
    evaluation_trace = []

    first_evaluation = evaluate(draft)
    evaluation_trace.append({
        "draft": draft,
        "evaluation": first_evaluation.model_dump(),
    })

    if grounding_passed(first_evaluation):
        return {
            "status": "PASS",
            "final_answer": draft,
            "revision_attempts": 0,
            "evaluation_trace": evaluation_trace,
        }

    revised_draft = revise(draft, first_evaluation)
    if not revised_draft.strip():
        return {
            "status": "GROUNDING_REJECTED",
            "final_answer": None,
            "revision_attempts": 1,
            "evaluation_trace": evaluation_trace,
        }

    second_evaluation = evaluate(revised_draft)
    evaluation_trace.append({
        "draft": revised_draft,
        "evaluation": second_evaluation.model_dump(),
    })

    if not grounding_passed(second_evaluation):
        return {
            "status": "GROUNDING_REJECTED",
            "final_answer": None,
            "revision_attempts": 1,
            "evaluation_trace": evaluation_trace,
        }

    return {
        "status": "PASS",
        "final_answer": revised_draft,
        "revision_attempts": 1,
        "evaluation_trace": evaluation_trace,
    }

def run_grounding_boundary_test() -> dict[str, Any]:
    run_id = uuid.uuid4().hex
    unsupported_claim = "需要填寫寢室房號"

    fixed_evaluations = iter([
        GroundingEvaluation(
            verdict="revise",
            unsupported_claims=[unsupported_claim],
            feedback="提供的 evidence 沒有要求填寫寢室房號。",
        ),
        GroundingEvaluation(
            verdict="revise",
            unsupported_claims=[unsupported_claim],
            feedback="修訂後仍包含 evidence 未支持的寢室房號要求。",
        ),
    ])

    call_counts = {"evaluate": 0, "revise": 0}

    def fixed_evaluate(draft: str) -> GroundingEvaluation:
        call_counts["evaluate"] += 1
        return next(fixed_evaluations)

    def fixed_revise(
        draft: str,
        evaluation: GroundingEvaluation,
    ) -> str:
        call_counts["revise"] += 1
        return draft

    initial_draft = "請透過修繕系統報修，並填寫寢室房號。"
    cycle_result = run_grounding_cycle(
        draft=initial_draft,
        evaluate=fixed_evaluate,
        revise=fixed_revise,
    )

    if cycle_result["status"] != "GROUNDING_REJECTED":
        raise AssertionError("預期修訂後仍不通過時應回傳 GROUNDING_REJECTED")
    if cycle_result["revision_attempts"] != 1:
        raise AssertionError("預期最多修訂一次")
    if call_counts != {"evaluate": 2, "revise": 1}:
        raise AssertionError(f"評估或修訂次數不符：{call_counts}")

    result = {
        "run_id": run_id,
        "mode": "LOCAL_GROUNDING_BOUNDARY_TEST",
        **cycle_result,
        "stop_reason": "revision_limit_reached_with_unsupported_claims",
        "answer_displayed": False,
        "write_executed": False,
        "test_call_counts": call_counts,
    }
    save_run(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


SERVER_PATH = ROOT / "mcp_server.py"
RUNS_DIR = ROOT / "runs"


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def save_run(payload: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(exist_ok=True)
    filename = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.json"
    path = RUNS_DIR / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class MCPClient:
    def __init__(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, str(SERVER_PATH)],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self.next_id = 1
        init = self.request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "nutn-repair-agent-cli", "version": "1.0.0"},
        })
        if init.get("protocolVersion") != "2025-06-18":
            raise RuntimeError("MCP initialize failed: unexpected protocol version")
        self.notify("notifications/initialized")

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP server streams are unavailable")
        request_id = self.next_id
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("MCP server stopped without replying")
        response = json.loads(line)
        if "error" in response:
            raise RuntimeError(response["error"].get("message", "MCP protocol error"))
        return response.get("result", {})

    def notify(self, method: str) -> None:
        if self.process.stdin:
            self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
            self.process.stdin.flush()

    def list_tools(self) -> dict[str, Any]:
        return self.request("tools/list")

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()


def unpack_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("isError"):
        text = result.get("content", [{}])[0].get("text", "Tool failed")
        raise RuntimeError(text)
    return result.get("structuredContent") or {}


def show_tools(client: MCPClient) -> None:
    result = client.list_tools()
    print("\nMCP tools/list：")
    for tool in result.get("tools", []):
        print(f"- {tool['name']}: {tool['description']}")
    save_run({"run_id": uuid.uuid4().hex, "mode": "MCP_TOOLS_LIST", "tools": result.get("tools", [])})


def read_info(client: MCPClient) -> dict[str, Any] | None:
    print("\n目前固定 evidence 只支援：學生宿舍空調修繕。")
    problem = input("故障描述：").strip()
    location = input("故障地點：").strip()
    run_id = uuid.uuid4().hex
    try:
        raw = client.call_tool("get_repair_information", {
            "problem_description": problem,
            "location": location,
        })
        value = unpack_tool_result(raw)
        # Keep the exact user input alongside the tool result so the next
        # menu action can build a proposal from the same verified read.
        value["problem_description"] = problem
        value["location"] = location
        print("\n查詢結果：")
        print(json.dumps(value, ensure_ascii=False, indent=2))
        print("\nEvidence 來源：GitHub 專題文件 week4-fixed queries、chunk.md；上方已列出各 chunk 原文與 ID。")
        save_run({
            "run_id": run_id,
            "mode": "MCP_READ_DEMO",
            "status": "TOOL_SUCCESS",
            "input": {"problem_description": problem, "location": location},
            "tool": "get_repair_information",
            "tool_result": value,
        })
        return value
    except Exception as exc:
        print(f"\n查詢停止：{exc}")
        save_run({
            "run_id": run_id,
            "mode": "MCP_READ_DEMO",
            "status": "TOOL_FAIL",
            "input": {"problem_description": problem, "location": location},
            "tool": "get_repair_information",
            "error": str(exc),
            "write_executed": False,
        })
        return None


def create_draft(client: MCPClient, last_read: dict[str, Any] | None) -> None:
    if not last_read:
        run_id = uuid.uuid4().hex
        message = "請先在本次程式執行中成功查詢修繕資訊，再建立草稿。"
        print(message)
        save_run({
            "run_id": run_id,
            "mode": "SESSION_MEMORY_GUARD",
            "status": "BLOCKED_NO_CURRENT_READ",
            "action": "create_repair_draft",
            "stop_reason": "no_current_session_read",
            "write_executed": False,
        })
        return
    problem = input(f"問題描述 [{last_read['problem_description']}]：").strip() or last_read["problem_description"]
    location = input(f"地點 [{last_read['location']}]：").strip() or last_read["location"]
    unit = input("申請單位（依實際表單填寫）：").strip()
    building = input("具體建築／棟別（例如 A 棟）：").strip()
    proposal = {
        "problem_description": problem,
        "location": location,
        "repair_category": last_read["repair_category"],
        "unit": unit,
        "building": building,
        "request_id": f"REQ-REPAIR-{uuid.uuid4().hex[:10].upper()}",
    }
    print("\n報修草稿預覽（只會建立本機草稿，不會送出正式系統）：")
    for key, value in proposal.items():
        if key != "request_id":
            print(f"- {key}: {value}")
    answer = input('\n若要建立，請完整輸入「確認建立」：').strip()
    if answer != "確認建立":
        print("已取消；沒有呼叫寫入工具，也沒有建立檔案。")
        save_run({"run_id": uuid.uuid4().hex, "mode": "WRITE_CONFIRMATION", "accepted": False, "executed": False, "proposal": {k: v for k, v in proposal.items() if k != "request_id"}})
        return
    try:
        raw = client.call_tool("create_repair_draft", proposal)
        result = unpack_tool_result(raw)
        if result.get("status") != "draft_created":
            raise RuntimeError(f"Unexpected write result: {result}")
        draft_path = ROOT / result["file"]
        read_back = draft_path.read_text(encoding="utf-8")
        checks = [problem, location, proposal["repair_category"], unit, building]
        if not all(value in read_back for value in checks):
            raise RuntimeError("READ_BACK_MISMATCH: 草稿內容與確認資料不一致")
        print(f"\n草稿已建立並完成讀回核對：{draft_path}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        save_run({
            "run_id": uuid.uuid4().hex,
            "mode": "MCP_WRITE_DEMO",
            "status": "WRITE_AND_READBACK_PASS",
            "accepted": True,
            "executed": result.get("executed"),
            "proposal": {k: v for k, v in proposal.items() if k != "request_id"},
            "request_id": proposal["request_id"],
            "tool_result": result,
            "readback_verified": True,
        })
    except Exception as exc:
        print(f"\n寫入或讀回核對失敗：{exc}")
        save_run({
            "run_id": uuid.uuid4().hex,
            "mode": "MCP_WRITE_DEMO",
            "status": "WRITE_FAIL",
            "accepted": True,
            "error": str(exc),
            "request_id": proposal["request_id"],
        })

def run_idempotency_test(
    client: MCPClient,
    last_read: dict[str, Any] | None,
) -> None:
    if not last_read:
        print("請先成功查詢修繕資訊，再執行同 ID 重送測試。")
        return

    proposal = {
        "problem_description": last_read["problem_description"],
        "location": last_read["location"],
        "repair_category": last_read["repair_category"],
        "unit": "學生",
        "building": "測試用棟別",
        "request_id": f"REQ-WEEK07-IDEMPOTENCY-{uuid.uuid4().hex[:8].upper()}",
    }

    print("\nW02 同 ID 重送測試預覽（只會建立一份本機草稿）：")
    for key, value in proposal.items():
        print(f"- {key}: {value}")
    print("- 動作：確認後以相同 request_id 呼叫寫入工具兩次")
    answer = input('若要執行，請完整輸入「確認建立」：').strip()

    if answer != "確認建立":
        print("已取消；沒有呼叫寫入工具，也沒有建立檔案。")
        save_run({
            "run_id": uuid.uuid4().hex,
            "mode": "IDEMPOTENCY_TEST",
            "status": "CANCELLED",
            "accepted": False,
            "write_executed": False,
        })
        return

    run_id = uuid.uuid4().hex
    first_call_attempted = False
    first_result: dict[str, Any] | None = None
    try:
        first_call_attempted = True
        first_result = unpack_tool_result(
            client.call_tool("create_repair_draft", proposal)
        )
        second_result = unpack_tool_result(
            client.call_tool("create_repair_draft", proposal)
        )

        passed = (
            first_result.get("executed") is True
            and first_result.get("replayed") is False
            and second_result.get("executed") is False
            and second_result.get("replayed") is True
            and first_result.get("draft_id") == second_result.get("draft_id")
        )

        result = {
            "run_id": run_id,
            "mode": "IDEMPOTENCY_TEST",
            "status": "PASS" if passed else "FAIL",
            "request_id": proposal["request_id"],
            "first_result": first_result,
            "replay_result": second_result,
            "same_draft_id": first_result.get("draft_id") == second_result.get("draft_id"),
            "write_executed": first_result.get("executed") is True,
            "replay_created_new_draft": second_result.get("executed") is True,
        }
    except Exception as exc:
        state_unknown = first_call_attempted and first_result is None
        result = {
            "run_id": run_id,
            "mode": "IDEMPOTENCY_TEST",
            "status": "WRITE_STATE_UNKNOWN" if state_unknown else "FAIL",
            "request_id": proposal["request_id"],
            "first_result": first_result,
            "error": str(exc),
            "write_executed": (
                first_result.get("executed") is True
                if first_result is not None
                else None
            ),
            "replay_created_new_draft": False,
        }

    save_run(result)
    print("\nW02 測試結果：")
    print(json.dumps(result, ensure_ascii=False, indent=2))

def gemini_live_read(client: MCPClient) -> dict[str, Any] | None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
    if not api_key:
        print("找不到 GEMINI_API_KEY。先用一般查詢／草稿功能；要做 Live 測試時，依 README 建立 .env。")
        return None

    problem = input("請用一句話描述問題（此模式目前支援宿舍空調）：").strip()
    location = input("問題地點：").strip()
    run_id = uuid.uuid4().hex
    user_prompt = (
        "只處理學生宿舍空調問題。必須呼叫 get_repair_information 取得 evidence；"
        "只根據工具結果回答，不得呼叫任何寫入工具、不得聲稱已建立報修。"
        "若問題不支援或輸入不完整，直接說明。" + "\n"
        + f"問題：{problem}" + "\n" + f"地點：{location}"
    )

    tool_invocations: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    messages: list[Any] = []

    @tool
    def get_repair_information(problem_description: str, location: str) -> str:
        """唯讀查詢固定 evidence 中的學生宿舍空調修繕系統、類別和必填資訊；不得猜測。"""
        invocation = {
            "name": "get_repair_information",
            "args": {
                "problem_description": problem_description,
                "location": location,
            },
        }
        tool_invocations.append(invocation)
        if len(tool_invocations) > 1:
            raise RuntimeError("LIVE_FAIL: LangChain agent attempted more than one tool call")
        raw = client.call_tool("get_repair_information", invocation["args"])
        value = unpack_tool_result(raw)
        tool_results.append(value)
        return json.dumps(value, ensure_ascii=False)

    try:
        if os.environ.get("WEEK06_INJECT_PROVIDER_FAILURE") == "1":
            raise RuntimeError(
                "INJECTED_PROVIDER_FAILURE: Week 06 controlled failure test"
            )
        chat_model = ChatGoogleGenerativeAI(
            model=model,
            api_key=api_key,
            temperature=1.0,
            retries=0,
            request_timeout=120,
        )
        agent = create_agent(
            model=chat_model,
            tools=[get_repair_information],
            system_prompt=(
                "你是南大校園修繕助理。只處理學生宿舍空調問題。"
                "每次只呼叫一次 get_repair_information 取得 evidence；"
                "只根據工具結果回答，不可補充工具結果未列出的具體要求或事實。"
                "例如 evidence 只寫『所在建築』時，不可自行增加棟別、寢室或房號要求。"
                "不可呼叫寫入工具或聲稱已建立報修。"
                "若工具回傳錯誤，說明無法根據固定資料提供建議。"
            ),
        )
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_prompt}]},
            config={"recursion_limit": 6},
        )
        messages = result.get("messages", [])
        model_tool_calls = [
            call
            for message in messages
            for call in (getattr(message, "tool_calls", None) or [])
        ]
        if len(tool_invocations) != 1 or len(model_tool_calls) != 1:
            raise RuntimeError(
                "LIVE_FAIL: 預期一次 get_repair_information 呼叫；"
                f"實際 MCP 呼叫次數={len(tool_invocations)}，模型 tool call 次數={len(model_tool_calls)}"
            )
        if model_tool_calls[0].get("name") != "get_repair_information":
            raise RuntimeError("LIVE_FAIL: agent 呼叫了非預期工具")
        if len(tool_results) != 1:
            raise RuntimeError("LIVE_FAIL: MCP 工具沒有回傳可用 evidence")

        final_message = next(
            (message for message in reversed(messages) if getattr(message, "type", None) == "ai"),
            None,
        )
        if final_message is None:
            raise RuntimeError("LIVE_FAIL: agent 沒有回傳最終 AI 訊息")
        content = final_message.content
        if isinstance(content, str):
            final_text = content.strip()
        elif isinstance(content, list):
            final_text = "\n".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ).strip()
        else:
            final_text = str(content).strip()

        tool_value = tool_results[0]
        function_call = model_tool_calls[0]

        if not final_text:
            raise RuntimeError("LIVE_FAIL: tool result 後沒有取得 Gemini 文字摘要")

        def evaluate_candidate(candidate: str) -> GroundingEvaluation:
            return evaluate_grounding(
                chat_model=chat_model,
                problem=problem,
                location=location,
                evidence=tool_value,
                draft=candidate,
            )

        def revise_candidate(
            candidate: str,
            evaluation: GroundingEvaluation,
        ) -> str:
            revision_message = [
                (
                    "system",
                    "請依照評估意見修正回答。只能使用提供的 evidence，"
                    "刪除沒有 evidence 支持的主張，不得自行補充資訊。",
                ),
                (
                    "human",
                    f"Evidence：{json.dumps(tool_value, ensure_ascii=False)}\n"
                    f"原回答：{candidate}\n"
                    f"評估意見：{evaluation.feedback}\n"
                    f"未支持主張：{json.dumps(evaluation.unsupported_claims, ensure_ascii=False)}",
                ),
            ]
            revised = chat_model.invoke(revision_message)
            return str(revised.content).strip()

        grounding_result = run_grounding_cycle(
            draft=final_text,
            evaluate=evaluate_candidate,
            revise=revise_candidate,
        )
        evaluation_trace = grounding_result["evaluation_trace"]

        if grounding_result["status"] == "GROUNDING_REJECTED":
            print("\nGROUNDING_REJECTED：修訂一次後仍未通過 evidence 檢查，停止顯示回答。")
            save_run({
                "run_id": run_id,
                "mode": "GEMINI_LIVE",
                "status": "GROUNDING_REJECTED",
                "model": model,
                "input": {"problem_description": problem, "location": location},
                "evaluation_trace": evaluation_trace,
                "revision_attempts": grounding_result["revision_attempts"],
                "answer_displayed": False,
                "write_executed": False,
            })
            return None

        final_text = grounding_result["final_answer"]

        
        print("\n" + "Gemini 最終回答：" + "\n" + final_text)
        print("\n" + f"LIVE_PASS | framework=LangChain create_agent | model={model} | run_id={run_id}")
        value = {
            "run_id": run_id,
            "mode": "GEMINI_LIVE",
            "status": "LIVE_PASS",
            "framework": "langchain.create_agent",
            "model": model,
            "input": {"problem_description": problem, "location": location},
            "function_call": function_call,
            "mcp_tool_result": tool_value,
            "tool_response_returned_to_agent": True,
            "final_answer": final_text,
            "evaluation_trace": evaluation_trace,
            "grounding_status": "PASS",
            "usage_metadata": getattr(final_message, "usage_metadata", None) or "not returned",
            "write_executed": False,
        }
        save_run(value)
        return {**tool_value, "problem_description": problem, "location": location}
    except Exception as exc:
        reason = str(exc)
        injected = reason.startswith("INJECTED_PROVIDER_FAILURE:")

        if injected:
            mode = "INJECTED_PROVIDER_FAILURE"
            status = "EXPECTED_INJECTED_FAILURE"
            error_source = "test_switch"
            label = "EXPECTED_INJECTED_FAILURE"
        else:
            mode = "GEMINI_LIVE"
            status = "LIVE_FAIL"
            error_source = "provider_or_tool"
            label = "LIVE_FAIL"

        print(f"\n{label} | {reason}\n本輪停止；沒有自動重送。")
        save_run({
            "run_id": run_id,
            "mode": mode,
            "status": status,
            "framework": "langchain.create_agent",
            "model": model,
            "input": {"problem_description": problem, "location": location},
            "tool_calls": tool_invocations,
            "mcp_tool_results": tool_results,
            "error_source": error_source,
            "error": reason,
            "write_executed": False,
        })
        return None

def main() -> None:
    # Keep the interactive host and MCP child's JSON stream consistent on
    # Windows consoles that otherwise fall back to a legacy code page.
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv()
    if not SERVER_PATH.exists():
        print(f"找不到 MCP server：{SERVER_PATH}")
        raise SystemExit(1)
    print("南大修繕 Agent｜本機示範版")
    print("只支援學生宿舍空調的固定 evidence；建立的是本地草稿，不會送出正式報修。")
    client = MCPClient()
    last_read: dict[str, Any] | None = None
    try:
        while True:
            print("\n選單： 1 查詢修繕資訊 | 2 建立報修草稿 | 3 Gemini Live 查詢 | 4 重現輸入錯誤 | 5 顯示 MCP tools/list | 6 W02 同 ID 重送測試 | 0 離開")
            choice = input("請輸入選項：").strip()
            if choice == "1":
                last_read = None
                last_read = read_info(client)
            elif choice == "2":
                create_draft(client, last_read)
            elif choice == "3":
                last_read = None
                result = gemini_live_read(client)
                if result:
                    last_read = result
            elif choice == "4":
                last_read = None
                run_id = uuid.uuid4().hex
                raw = client.call_tool(
                    "get_repair_information",
                    {
                        "problem_description": "",
                        "location": "學生宿舍",
                    },
                )
                print("\n預期失敗結果：")
                print(json.dumps(raw, ensure_ascii=False, indent=2))
            elif choice == "5":
                show_tools(client)
            elif choice == "6":
                run_idempotency_test(client, last_read)
            elif choice == "0":
                break
            else:
                print("請輸入 0–。")
    except (EOFError, KeyboardInterrupt):
        print("\n已結束。")
    finally:
        client.close()


if __name__ == "__main__":
    main()
