"""Interactive host: CLI + Gemini function calling + local stdio MCP client."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI


ROOT = Path(__file__).resolve().parent
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
        print("請先在本次程式執行中成功查詢修繕資訊，再建立草稿。")
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
        if not final_text:
            raise RuntimeError("LIVE_FAIL: tool result 後沒有取得 Gemini 文字摘要")

        tool_value = tool_results[0]
        function_call = model_tool_calls[0]
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
            "usage_metadata": getattr(final_message, "usage_metadata", None) or "not returned",
            "write_executed": False,
        }
        save_run(value)
        return {**tool_value, "problem_description": problem, "location": location}
    except Exception as exc:
        reason = str(exc)
        print("\n" + f"LIVE_FAIL | {reason}" + "\n" + "本輪停止；沒有自動重送。")
        save_run({
            "run_id": run_id,
            "mode": "GEMINI_LIVE",
            "status": "LIVE_FAIL",
            "framework": "langchain.create_agent",
            "model": model,
            "input": {"problem_description": problem, "location": location},
            "tool_calls": tool_invocations,
            "mcp_tool_results": tool_results,
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
            print("\n選單： 1 查詢修繕資訊 | 2 建立報修草稿 | 3 Gemini Live 查詢 | 4 重現輸入錯誤 | 5 顯示 MCP tools/list | 0 離開")
            choice = input("請輸入選項：").strip()
            if choice == "1":
                last_read = read_info(client)
            elif choice == "2":
                create_draft(client, last_read)
            elif choice == "3":
                result = gemini_live_read(client)
                if result:
                    last_read = result
            elif choice == "4":
                run_id = uuid.uuid4().hex
                raw = client.call_tool("get_repair_information", {"problem_description": "", "location": "學生宿舍"})
                print("\n預期失敗結果：")
                print(json.dumps(raw, ensure_ascii=False, indent=2))
                print("這是本機 MCP 輸入驗證案例，不是 Gemini LIVE_FAIL。")
                save_run({
                    "run_id": run_id,
                    "mode": "REPRODUCIBLE_LOCAL_FAILURE",
                    "status": "EXPECTED_TOOL_ERROR" if raw.get("isError") else "UNEXPECTED_PASS",
                    "input": {"problem_description": "", "location": "學生宿舍"},
                    "mcp_tool_result": raw,
                    "write_executed": False,
                })
            elif choice == "5":
                show_tools(client)
            elif choice == "0":
                break
            else:
                print("請輸入 0–5。")
    except (EOFError, KeyboardInterrupt):
        print("\n已結束。")
    finally:
        client.close()


if __name__ == "__main__":
    main()
