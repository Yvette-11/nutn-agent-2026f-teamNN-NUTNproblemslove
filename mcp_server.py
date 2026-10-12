"""Small stdio MCP server for the NUTN repair-agent class project."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
KNOWLEDGE_PATH = ROOT / "knowledge.json"
DRAFTS_DIR = ROOT / "drafts"
REGISTRY_PATH = DRAFTS_DIR / "request_registry.json"

TOOLS = [
    {
        "name": "get_repair_information",
        "description": (
            "唯讀查詢目前有固定 evidence 支援的學生宿舍空調修繕資訊。回傳本機 evidence 原文、"
            "source_id 與 chunk_ids；若超出範圍或證據不足，就回傳錯誤，不自行猜測。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "problem_description": {"type": "string", "description": "設備故障描述，不可空白"},
                "location": {"type": "string", "description": "故障位置，例如學生宿舍"},
            },
            "required": ["problem_description", "location"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
    },
    {
        "name": "create_repair_draft",
        "description": (
            "只建立本機 Markdown 報修草稿。Host 必須先顯示完整草稿，並在呼叫本工具前取得使用者本次明確確認。"
            "不可用來送出南大正式報修。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "problem_description": {"type": "string"},
                "location": {"type": "string"},
                "repair_category": {"type": "string"},
                "unit": {"type": "string"},
                "building": {"type": "string"},
                "request_id": {"type": "string"},
            },
            "required": ["problem_description", "location", "repair_category", "unit", "building", "request_id"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True},
    },
]


class ToolFailure(Exception):
    pass


def load_knowledge() -> dict[str, Any]:
    try:
        return json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToolFailure(f"KNOWLEDGE_LOAD_FAILED: {exc}") from exc


def require_text(args: dict[str, Any], key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ToolFailure(f"INVALID_INPUT: {key} must be a non-empty string")
    return value.strip()


def get_repair_information(args: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    problem = require_text(args, "problem_description")
    location = require_text(args, "location")
    normalized = f"{problem} {location}".casefold()
    supported_words = ("冷氣", "空調", "air conditioner", "air-conditioning", "air conditioning")
    dorm_words = ("宿舍", "dorm")
    if not any(word in normalized for word in supported_words) or not any(word in normalized for word in dorm_words):
        raise ToolFailure("OUT_OF_SCOPE: 目前只支援有固定 evidence 的學生宿舍空調修繕情境")

    knowledge = load_knowledge()
    evidence = knowledge.get("dorm_air_conditioning")
    chunks = evidence.get("chunks", []) if evidence else []
    if not evidence or not evidence.get("source_id") or not chunks:
        raise ToolFailure("INSUFFICIENT_EVIDENCE: 找不到可追溯的 source_id/chunks")
    if any(not chunk.get("chunk_id") or not chunk.get("text") for chunk in chunks):
        raise ToolFailure("INSUFFICIENT_EVIDENCE: chunk 缺少 ID 或 evidence 原文")

    result = {
        "repair_system": evidence["repair_system"],
        "repair_category": evidence["repair_category"],
        "required_information": evidence["required_information"],
        "source_id": evidence["source_id"],
        "chunk_ids": [chunk["chunk_id"] for chunk in chunks],
        "source_document": evidence.get("source_document", ""),
        "source_url": evidence.get("source_url", ""),
        "evidence": chunks,
        "evidence_note": evidence.get("evidence_note", ""),
    }
    state["last_verified_read"] = {
        "problem_description": problem,
        "location": location,
        "repair_category": result["repair_category"],
        "source_id": result["source_id"],
        "chunk_ids": result["chunk_ids"],
    }
    return result


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ToolFailure(f"DRAFT_REGISTRY_INVALID: {exc}") from exc


def create_repair_draft(args: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    problem = require_text(args, "problem_description")
    location = require_text(args, "location")
    category = require_text(args, "repair_category")
    unit = require_text(args, "unit")
    building = require_text(args, "building")
    request_id = require_text(args, "request_id")

    prior = state.get("last_verified_read")
    if not prior:
        raise ToolFailure("READ_REQUIRED: 必須先在本次執行成功取得修繕 evidence")
    if category != prior["repair_category"]:
        raise ToolFailure("WRITE_DATA_MISMATCH: repair_category 與已驗證 evidence 不一致")
    if problem != prior["problem_description"] or location != prior["location"]:
        raise ToolFailure("WRITE_DATA_MISMATCH: 問題或地點與本次已驗證輸入不一致")

    registry = load_registry()
    if request_id in registry:
        prior_record = registry[request_id]
        return {
            "status": "draft_created",
            "executed": False,
            "replayed": True,
            "draft_id": prior_record["draft_id"],
            "file": prior_record["file"],
        }

    draft_id = f"REPAIR-DRAFT-{uuid.uuid4().hex[:8].upper()}"
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    relative_file = f"drafts/{draft_id}.md"
    draft_path = ROOT / relative_file
    created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    content = (
        "# 校園設備修繕草稿\n\n"
        f"- 草稿編號：{draft_id}\n"
        f"- 建立時間：{created_at}\n"
        f"- 問題：{problem}\n"
        f"- 地點：{location}\n"
        f"- 修繕類別：{category}\n"
        f"- 單位：{unit}\n"
        f"- 所在建築：{building}\n"
        f"- Evidence：{prior['source_id']} / {', '.join(prior['chunk_ids'])}\n\n"
        "> 本檔案是本機草稿，尚未送出至南大正式修繕系統。\n"
    )
    draft_path.write_text(content, encoding="utf-8")
    registry[request_id] = {"draft_id": draft_id, "file": relative_file}
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "draft_created", "executed": True, "replayed": False, "draft_id": draft_id, "file": relative_file}


def tool_result(value: Any, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}],
        "structuredContent": value if isinstance(value, dict) else {"result": value},
        "isError": is_error,
    }


def dispatch(message: dict[str, Any], state: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "nutn-repair-agent", "version": "1.0.0"},
            },
        }
    if method == "ping":
        result: Any = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name not in {"get_repair_information", "create_repair_draft"}:
            result = tool_result({"error": "UNKNOWN_TOOL", "message": str(name)}, True)
        else:
            try:
                value = get_repair_information(args, state) if name == "get_repair_information" else create_repair_draft(args, state)
                result = tool_result(value)
            except ToolFailure as exc:
                result = tool_result({"error": str(exc).split(":", 1)[0], "message": str(exc)}, True)
            except OSError as exc:
                result = tool_result({"error": "LOCAL_WRITE_FAILED", "message": str(exc)}, True)
    else:
        if request_id is None:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

    if request_id is None:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> None:
    # Windows may choose a legacy console encoding for a child process. MCP
    # stdio is a UTF-8 JSON stream, so force UTF-8 before writing tool schemas
    # that contain Traditional Chinese text.
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    state: dict[str, Any] = {}
    for line in sys.stdin:
        try:
            message = json.loads(line)
            response = dispatch(message, state)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as exc:  # Keep protocol stdout clean; diagnostics go to stderr.
            print(f"MCP server error: {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
