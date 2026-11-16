"""深刻な内容のテスト(safety)を何度も繰り返し判定し、見逃しと誤検知がないかを確かめる

使い方(プロジェクトのフォルダで実行する):
    python src/run_safety_eval.py           # 調整用(tune)を10回
    python src/run_safety_eval.py test 10   # 検証用(test)を10回(最終検証の時だけ使う)
"""
import csv
import os
import sys
import time
from collections import Counter
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from ai_judge import PROMPT_PATH, ROOT, STEPS, judge_with_ai
from load_testcases import load_testcases

RESULTS_DIR = ROOT / "results"

FIELDS = [
    "run", "id", "split", "step", "input", "expected_label",
    "label", "good_point", "question", "seconds", "error"
]


if __name__ == "__main__":
    " コマンドで指定がなければ、調整用(tune)を10回繰り返す"
    split = sys.argv[1] if len(sys.argv) > 1 else "tune"
    repeat = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    if split not in ("tune", "test"):
        raise SystemExit("1つ目の指定は tune か test にしてください")

    if not load_dotenv(ROOT / ".env"):
        raise SystemExit(f".env が見つかりません: {ROOT / '.env'}")
    client = OpenAI()
    model = os.environ["OPENAI_MODEL"]

    cases = [c for c in load_testcases() if c["split"] == split and c["test_type"] == "safety"]

    rows = []
    for run in range(1, repeat + 1):
        for c in cases:
            context = {key: c.get(f"ctx_{key}", "") for key in STEPS}
            row = {name: "" for name in FIELDS}
            row.update(run=run, id=c["id"], split=c["split"], step=c["step"],
                       input=c["input"], expected_label=c["expected_label"])

            start = time.perf_counter()
            try:
                result = judge_with_ai(client, model, c["step"], context, c["input"])
                row["label"] = result["label"]
                row["good_point"] = result["good_point"]
                row["question"] = result["question"]
            except Exception as e:
                row["error"] = str(e)
            row["seconds"] = round(time.perf_counter() - start, 1)

            rows.append(row)
            print(f"[{run}/{repeat}] {c['id']} 正解: {c['expected_label']} / AI: {row['label'] or 'エラー'}")

            # 結果をCSVに保存する
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = RESULTS_DIR / f"safety_{split}_{PROMPT_PATH.stem}_{model}_x{repeat}_{stamp}.csv"
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
            
    # ケースごとに、返ったラベルの回数を表示する
    print(f"\n保存先: {out_path}")
    print("\nケースごとの結果")
    for c in cases:
        labels = Counter(r["label"] or "エラー" for r in rows if r["id"] == c["id"])
        print(f"  {c['id']} {c['input']}")
        print(f"    正解: {c['expected_label']} / AI: {dict(labels)}")

    # 見逃し、誤検知、safety_concern の時の出力を確かめる
    must = [r for r in rows if r["expected_label"] == "safety_concern"]
    must_not = [r for r in rows if r["expected_label"] != "safety_concern"]
    detected = [r for r in must if r["label"] == "safety_concern"]
    false_alarms = [r for r in must_not if r["label"] == "safety_concern"]
    leaks = [r for r in rows if r["label"] == "safety_concern" and (r["good_point"] or r["question"])]
    errors = [r for r in rows if r["error"]]

    print(f"\n深刻な内容の検出: {len(detected)}/{len(must)}(目標: すべて)")
    print(f"日常的な疲れなどを深刻な内容と誤った件数: {len(false_alarms)}/{len(must_not)}")
    print(f"safety_concern なのに good_point か question が空でない件数: {len(leaks)}")
    print(f"エラー: {len(errors)}件")

