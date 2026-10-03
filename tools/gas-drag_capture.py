#!/usr/bin/env python3
import csv
from pathlib import Path

# 入出力パスの設定
INPUT_DIR = Path("result/gas-drag/out")
OUTPUT_FILE = Path("result/gas-drag_capture.csv")

# 対象の初速度リスト (20.0 ~ 160.0)
V0_LIST = [20, 40, 60, 80, 100, 120, 140, 160]


def main():
    if not INPUT_DIR.exists():
        print(f"Error: 入力ディレクトリが見つかりません: {INPUT_DIR}")
        return

    all_captured_rows = []
    capture_ids_per_v = {}
    found_files = 0

    print("=== gas-drag 捕獲データの抽出開始 ===")

    for v in V0_LIST:
        filename = f"v{v:03d}.csv"
        filepath = INPUT_DIR / filename

        if not filepath.exists():
            print(f"  [スキップ] {filename} が存在しません。")
            continue

        found_files += 1
        v_captures = []

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                # 空行やヘッダ行をスキップ
                if not row or row[0].startswith("#"):
                    continue

                # 列構成: ID(0), v0(1), phi0(2), zeta0(3), N(4), year(5), Capture/Escape/Survive(6)
                if len(row) >= 7 and row[6].strip() == "C":
                    rec = {
                        "v0": f"{float(row[1].strip()):.1f}",
                        "ID": row[0].strip(),
                        "phi0": row[2].strip(),
                        "zeta0": row[3].strip(),
                        "N": row[4].strip(),
                        "year": row[5].strip(),
                    }
                    all_captured_rows.append(rec)
                    v_captures.append(row[0].strip())

        capture_ids_per_v[v] = set(v_captures)
        print(f"  v = {v:3d} m/s: 捕獲件数 {len(v_captures):4d} / 4096 件")

    if found_files == 0:
        print("処理対象の CSV ファイルがありませんでした。")
        return

    # 出力先ディレクトリの作成と書き込み
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # ヘッダ
        writer.writerow(["v0", "ID", "phi0", "zeta0"])
        # 抽出データの書き出し
        for rec in all_captured_rows:
            writer.writerow(
                [rec["v0"], rec["ID"], rec["phi0"], rec["zeta0"], rec["N"], rec["year"]]
            )

    print("\n=== 抽出完了 ===")
    print(f"出力先: {OUTPUT_FILE}")
    print(f"総捕獲レコード数: {len(all_captured_rows)} 行")

    # すべての初速度で共通して捕獲 (C) された ID の確認
    if capture_ids_per_v:
        common_ids = sorted(
            list(set.intersection(*capture_ids_per_v.values())), key=int
        )
        print(
            f"\n全初速度 ({len(capture_ids_per_v)}速度) で共通して捕獲された ID 数:"
            f" {len(common_ids)} 件"
        )
        if common_ids:
            print(f"共通捕獲 ID: {', '.join(common_ids)}")


if __name__ == "__main__":
    main()
