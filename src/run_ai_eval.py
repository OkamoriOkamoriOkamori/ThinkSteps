"""調整用のテストデータをまとめてAIに判定させ、結果をCSVに保存する"""
import csv
import os
import time
from collections import Counter
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from ai_judge import PROMPT_PATH, ROOT, STEPS, judge_with_ai
from load_testcases import load_testcases

RESULTS_DIR = ROOT / "results"

# 結果のCSVの例（テストデータの列 + AIの判定 + 正誤・時間・エラー　)
FIELDS = [
    "id", "split", "case_id", "test_type", "step", "input","expected_label", "expected_looks_like",
    "label", "looks_like", "against", "evidence", "good_point", "question",
    "correct", "seconds", "error"
]
AI_FIELDS = ["label", "looks_like", "against", "evidence", "good_point", "question"]


if __name__ == "__main__":
    if not load_dotenv(ROOT / ".env"):
        raise SystemExit(f".envが見つかりません: {ROOT / '.env'}")
    client = OpenAI()
    model = os.environ["OPENAI_MODEL"]

    # 調整用(tune)だけを使う。検証用(test)は最後まで使わない
    cases = [c for c in load_testcases() if c["split"] == "tune"]

    rows = []
    for i, c in enumerate(cases, start=1):
        context = {key: c.get(f"ctx_{key}", "") for key in STEPS}
        row = {name: c.get(name, "") for name in FIELDS}

        start = time.perf_counter()
        try:
            result = judge_with_ai(client, model, c["step"], context, c["input"])
            for name in AI_FIELDS:
                row[name] = result[name] if result[name] is not None else ""
        except Exception as e:
            row["error"] = str(e)
        row["seconds"] = round(time.perf_counter() - start, 1)
        
            # 禁止事項のテスト(guardrail)はラベルがないので、正誤は付けない
        if c["test_type"] != "guardrail" and not row["error"]:
            row["correct"] = row["label"] == c["expected_label"]
            
        rows.append(row)
        print(f"[{i}/{len(cases)}] {c['id']} 正解: {c['expected_label'] or '-'} / AI: {row['label'] or 'エラー'}")

        # 結果をCSVに保存する(ファイル名に、指示文の版・モデル名・日時を入れる)
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = RESULTS_DIR / f"ai_tune_{PROMPT_PATH.stem}_{model}_{stamp}.csv"
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        
    # 集計を表示する
    scored = [r for r in rows if r["correct"] != ""]
    correct = sum(1 for r in scored if r["correct"])
    by_label = Counter(r["expected_label"] for r in scored)
    by_label_correct = Counter(r["expected_label"] for r in scored if r["correct"])
    errors = [r for r in rows if r["error"]]

    print(f"\n保存先: {out_path}")
    print(f"正答率: {correct}/{len(scored)} ({correct / len(scored):.0%})" if scored else "正答率: 判定できたケースなし")
    print("\nラベル別の正答率")
    for label, n in by_label.items():
        print(f" {label}: {by_label_correct[label]}/{n}")
    print(f"\nエラー: {len(errors)}件")
    print("\n外れたケース")
    for r in scored:
        if not r["correct"]:
            print(f"  {r['id']} | {r['step']} | {r['input']} | 正解: {r['expected_label']} | AI: {r['label']}")