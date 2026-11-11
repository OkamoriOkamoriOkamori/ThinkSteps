"""語尾や単語だけで判定する、ルールによる簡易判定（AIと比べる基準）"""
from collections import Counter

from load_testcases import load_testcases

# 判定に使う言葉の一覧
SAFETY_WORDS = ["眠れ", "消えて", "消えたい", "怒鳴", "体調を崩"]
MEANS_WORDS = ["転職", "になる", "通う", "資格", "相談する", "申し出る", "探す", "調べる"]
TASK_ENDINGS = ("する", "広げる", "積む", "増やす", "確保", "目指す", "必要がある", "ようにしたい")
PROBLEM_ENDINGS = ("ていない", "足りない", "とどまっている", "少なさ,", "不足")
VAGUE_WORDS = ["やる気", "自信がない", "頑張る", "良くしたい", "やりがいのある", "改善する", "忙しい"]

def judge(step, text):
    """ステップと入力文から、ラベルを１つ返す"""
    if any(w in text for w in SAFETY_WORDS):
        return "safety_concern"
    if step != "means" and any(w in text for w in MEANS_WORDS):
        return "wrong_category"
    if step == "problem" and text.endswith(TASK_ENDINGS):
        return "wrong_category"
    if step == "task" and text.endswith(PROBLEM_ENDINGS):
        return "wrong_category"
    if any(w in text for w in VAGUE_WORDS):
        return "ambiguous"
    return "ok"

if __name__ == "__main__":
    # 調整用(true)だけを使う。禁止事項のテスト（guardrail)はラベルがないので除く
    cases = [c for c in load_testcases() if c["split"] == "tune" and c["test_type"] != "guardrail"]

    correct = 0
    by_label = Counter()
    by_label_correct = Counter()
    misses = []

    for c in cases:
        expected = c["expected_label"]
        predicted = judge(c["step"], c["input"])
        by_label[expected] += 1
        if predicted == expected:
            correct += 1
            by_label_correct[expected] += 1
        else:
            misses.append((c["id"], c["step"], c["input"], expected, predicted))
    
    print(f"正答率： {correct}/{len(cases)} ({correct / len(cases):.0%})")
    print("\nラベル別の正答率")
    for label, n in by_label.items():
        print(f" {label}: {by_label_correct[label]}/{n}")
    print(f"\n外れたケース({len(misses)}件)")
    for m in misses:
        print("  "," | ".join(m))