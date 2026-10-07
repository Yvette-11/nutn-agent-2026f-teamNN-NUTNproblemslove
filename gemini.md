# Tool 1: get_repair_information
#   - 唯讀
#   - 查詢修繕資訊
#
# Tool 2: create_repair_draft
#   - 寫入
#   - 使用者確認後建立本地報修草稿


# =========================
# Fixed Repair Data
# =========================

repair_data = {
    "repair_system": "國立臺南大學修繕系統",
    "repair_category": "土木、空調或水電／其他維修",
    "required_information": [
        "申請類別",
        "單位",
        "所在建築",
        "故障情況"
    ],
    "source_id": "NUTN-DORM-REPAIR",
    "chunk_ids": [
        "NUTN-DORM-REPAIR-001",
        "NUTN-DORM-REPAIR-002",
        "NUTN-DORM-REPAIR-003"
    ]
}


# =========================
# Tool 1 - Read
# =========================

def get_repair_information(problem_description, location):
    """
    唯讀工具：
    根據使用者輸入，回傳南大修繕相關資訊。
    """

    # Input Validation
    if not problem_description or problem_description.strip() == "":
        return {
            "status": "error",
            "error": "INVALID_INPUT",
            "message": "problem_description 不得為空",
            "executed": False
        }

    if not location or location.strip() == "":
        return {
            "status": "error",
            "error": "INVALID_INPUT",
            "message": "location 不得為空",
            "executed": False
        }

    # 成功回傳固定修繕資訊
    return {
        "status": "success",
        "executed": True,
        "problem_description": problem_description,
        "location": location,
        "repair_system": repair_data["repair_system"],
        "repair_category": repair_data["repair_category"],
        "required_information": repair_data["required_information"],
        "source_id": repair_data["source_id"],
        "chunk_ids": repair_data["chunk_ids"]
    }


# =========================
# Tool 2 - Write
# =========================

def create_repair_draft(
    problem_description,
    location,
    confirmed=False,
    request_id="REQ-REPAIR-001"
):
    """
    寫入工具：
    使用者確認後，建立本地 repair_draft.md。
    """

    # 必填欄位驗證
    if not problem_description or problem_description.strip() == "":
        return {
            "status": "error",
            "error": "INVALID_INPUT",
            "message": "problem_description 不得為空",
            "executed": False
        }

    if not location or location.strip() == "":
        return {
            "status": "error",
            "error": "INVALID_INPUT",
            "message": "location 不得為空",
            "executed": False
        }

    # Human Confirmation
    if not confirmed:
        return {
            "status": "cancelled",
            "accepted": False,
            "executed": False,
            "message": "使用者未確認，不執行寫入"
        }

    # 建立報修草稿內容
    content = f"""# NUTN Repair Draft

## Problem
{problem_description}

## Location
{location}

## Repair System
{repair_data["repair_system"]}

## Repair Category
{repair_data["repair_category"]}

## Required Information
- 申請類別
- 單位
- 所在建築
- 故障情況

## Request ID
{request_id}

## Note
此檔案僅為課堂測試用報修草稿，
不代表已送出正式南大修繕申請。
"""

    # 寫入檔案
    try:
        with open("repair_draft.md", "w", encoding="utf-8") as f:
            f.write(content)

    except Exception as e:
        return {
            "status": "error",
            "error": "WRITE_FAILED",
            "message": str(e),
            "executed": False
        }

    # 成功結果
    return {
        "status": "draft_created",
        "accepted": True,
        "executed": True,
        "draft_id": "REPAIR-DRAFT-001",
        "request_id": request_id,
        "file": "repair_draft.md"
    }


# =========================
# Test Cases
# =========================

if __name__ == "__main__":

    print("====================================")
    print("TEST 1 - SUCCESSFUL READ")
    print("====================================")

    result1 = get_repair_information(
        "宿舍冷氣壞掉了",
        "學生宿舍"
    )

    print(result1)


    print("\n====================================")
    print("TEST 2 - SUCCESSFUL WRITE")
    print("====================================")

    result2 = create_repair_draft(
        problem_description="宿舍冷氣壞掉了",
        location="學生宿舍",
        confirmed=True,
        request_id="REQ-REPAIR-001"
    )

    print(result2)


    print("\n====================================")
    print("TEST 3 - INVALID INPUT")
    print("====================================")

    result3 = get_repair_information(
        "",
        "學生宿舍"
    )

    print(result3)


    print("\n====================================")
    print("TEST 4 - USER REJECTS WRITE")
    print("====================================")

    result4 = create_repair_draft(
        problem_description="宿舍冷氣壞掉了",
        location="學生宿舍",
        confirmed=False,
        request_id="REQ-REPAIR-002"
    )

    print(result4)
