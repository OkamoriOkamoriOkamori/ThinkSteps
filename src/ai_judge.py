"""AIで、1件の入力を判定する"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from load_testcases import load_testcases

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "judge_v1.md"

# ステップの英語名と日本語名（並び順もこの順）
STEPS = {
    "ideal": "理想",
    "premise": "前提・制約",
    "current": "現状",
    "problem": "問題",
    "cause": "原因",
    "task": "課題",
    "means": "手段",
}

# AIの出力の形（思考フレームワーク　5.3)
SCHEMA = {
    "type": "object",
    "properties": {
        "step": {"type": "string", "enum": list(STEPS)},
        "label": {
            "type": "string",
            "enum": ["ok", "wrong_category", "misaligned", "conflicts_premise", "ambiguous", "safety_concern"],
        },
        "looks_like": {"type": ["string", "null"]},
        "against": {"type": ["string", "null"]},
        "evidence": {"type": "string"},
        "good_point": {"type": "string"},
        "question": {"type": "string"},
    },
    "required": ["step", "label", "looks_like", "against", "evidence", "good_point", "question"],
    "additionalProperties": False,
}

def build_user_message(step, context, text):
    """判定するステップ、これまでの入力、判定する入力を、AIに渡す分にまとめる"""
    lines = ["これまでの入力:"]
    for key, name, in STEPS.items():
        if key == step:
            break
        value = context.get(key, "")
        lines.append(f"- {name}: {value if value else '(未入力)'}")
    lines.append(f"\n判定するステップ: {step} ({STEPS[step]})")
    lines.append(f"\n<input>\n{text}\n</input>")
    return "\n".join(lines)

def judge_with_ai(client, model, step, context, text):
    """AIに判定させ、結果を辞書で返す"""
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": PROMPT_PATH.read_text(encoding="utf-8")},
            {"role": "user", "content": build_user_message(step, context, text)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "judgement",
                "schema": SCHEMA,
                "strict": True,
            }
        },
    )
    return json.loads(response.output_text)

if __name__=="__main__":
    load_dotenv(ROOT / ".env")
    client = OpenAI()
    model = os.environ["OPENAI_MODEL"]

    # 試すケースのID(手元のCSVで、問題欄に「仕事の手応えを増やす」と書かれた行)
    case_id = "T018"
    case = next(c for c in load_testcases() if c["id"] == case_id)
    context = {key: case.get(f"ctx_{key}", "") for key in STEPS}

    print("AIに渡す文:\n" + build_user_message(case["step"], context, case["input"]) + "\n")
    result = judge_with_ai(client, model, case["step"], context, case["input"])
    print("AIの判定:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n正解: {case['expected_label']} {case['expected_looks_like']}")