import csv
from collections import Counter
from pathlib import Path

# このファイルの２つ上のフォルダ（プロジェクトの直下）から　data/testcases.csv を指す
DATA = Path(__file__).resolve().parent.parent / "data" / "testcases.csv"

def load_testcases(path=DATA):
    """テストデータを読み込み、１行を１つの辞書にしたリストを返す"""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

if __name__ == "__main__":
    cases = load_testcases()
    print(f"件数：{len(cases)}")
    print("用途：", Counter(c["split"] for c in cases))
    print("ラベル：", Counter(c["expected_label"] for c in cases))
