"""保存済みのAI判定結果を、今の正解ラベルで採点し直す(APIは呼ばない)

使い方(プロジェクトのフォルダで実行する):
    python src/rescore.py results/ai_tune_juddge_v1_*.csv results/ai_tune_judge_v2_*.csv
"""
import csv
import sys
from pathlib import Path

from load_testcases import load_testcases


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def rescore(path, cases):
    """1つの結果ファイルを、今の正解ラベルで採点し直す"""
    old = [] #当時の採点(CSVの　correct列)
    results = {} # 今の正解ラベルでの採点 {id: True/False}
    notes = [] # 除外したケースや、正解を変えたケースのメモ

    rows = read_csv(path)
    for r in rows:
        if r["correct"] != "":
            old.append(r["correct"] == "True")
        
        c = cases.get(r["id"])
        if c is None:
            notes.append(f"{r['id']}: 今のテストデータにないため除外")
            continue
        if c["input"].strip() != r["input"].strip():
            notes.append(f"{r['id']}: 入力文が変わったため除外")
            continue
        if c["test_type"] == "guardrail" or r["error"]:
            continue
        
        results[r["id"]] = r["label"] == c["expected_label"]
        if r["expected_label"] != c["expected_label"]:
            mark = "○" if results[r["id"]] else "×"
            notes.append(
                f"{r['id']}: 正解を {r['expected_label']} → {c['expected_label']} に変更"
                f" / AI: {r['label']} → {mark}"
            )
    
    # 今のテストデータにはあるが、実行したときにはなかったケース
    done = {r["id"] for r in rows}
    for c in cases.values():
        if c["split"] == "tune" and c["id"] not in done:
            notes.append(f"{c['id']}: 実行したときにはなかったケース")

    return old, results, notes


if __name__ == "__main__":
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        raise SystemExit("使い方: python src/rescore.py 結果のCSV [結果のCSV...]")

    cases = {c["id"]: c for c in load_testcases()}
    all_results = {}

    for path in paths:
        old, results, notes = rescore(path, cases)
        all_results[path.name] = results
        print(f"\n{path.name}")
        print(f"  当時の正解での採点: {sum(old)}/{len(old)}")
        print(f"  今の正解での採点: {sum(results.values())}/{len(results)}")
        for note in notes:
            print(f" {note}")

    # すべてのファイルで採点できたケースだけで比べる（条件を揃えるため）
    common = set.intersection(*(set(r) for r in all_results.values()))
    print(f"\n共通するケース({len(common)}件での正答率)")
    for name,results in all_results.items():
        n = sum(results[i] for i in common)
        print(f" {name}: {n}/{len(common)} ({n / len(common):.0%})")