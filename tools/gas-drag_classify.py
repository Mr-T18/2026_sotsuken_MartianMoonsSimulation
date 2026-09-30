#!/usr/bin/env python3
import csv
from pathlib import Path
import math
import struct

DIRECT = 0x10
TEMPORARY = 0x20

COLLISION = 0x01
CAPTURE = 0x02
ESCAPE = 0x04

RESULT_TYPE = {
    0: "TC",  # 一時捕獲を経由して捕獲: Temporary Capture
    1: "TL",  # 一時捕獲を経由して衝突: Temporary coLlision
    2: "TE",  # 一時捕獲を経由してエスケープ: Temporary Escape
    3: "DC",  # 直接捕獲: Direct Capture
    4: "DL",  # 直接衝突: Direct coLlision
    5: "DE",  # 直接エスケープ: Direct Escape
}

# 入出力パスの設定
INPUT_DIR = Path("result/gas-drag/out")
OUTPUT_DIR = Path("result/gas-drag_result_type")

# 対象の初速度リスト (20.0 ~ 160.0)
V0_LIST = [20, 40, 60, 80, 100, 120, 140, 160]


# 物理定数
G = 6.67430e-11
M_SUN = 1.99e30
M_MARS = 6.42e23
AU = 1.495978707e11
R_M_REAL = 3396.2e3  # 火星赤道半径 [m]
A_MARS = 1.52368 * AU


# Hill 半径 [m] および無次元化火星半径 [r_H] (約 0.003133)
R_H_REAL = A_MARS * ((M_MARS / (3.0 * M_SUN)) ** (1.0 / 3.0))
R_M_NORM = R_M_REAL / R_H_REAL


# バイナリ 1 レコードの形式: double 7 個 (t, x, y, z, vx, vy, vz) -> 56 バイト
RECORD_FORMAT = "7d"
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)


def get_bin_path(v0_int: int, angle_id: int) -> Path:
    """IDから.binのパスを探し出す"""
    sub_dir = angle_id // 1024
    candidate = (
        INPUT_DIR
        / f"v{v0_int:03d}"
        / f"{sub_dir:02d}"
        / f"v{v0_int:03d}_{angle_id:04d}.bin"
    )
    if candidate.exists():
        return candidate

    # サブディレクトリ階層がない場合のフォールバック
    fallback = INPUT_DIR / f"v{v0_int:03d}" / f"v{v0_int:03d}_{angle_id:04d}.bin"
    if fallback.exists():
        return fallback

    return candidate


def is_caputured_by_jacobi(bin_path: Path) -> bool:
    """.binを走査し，Jacobiエネルギー <= 0に達した(完全捕獲)かどうかを判定する"""
    if not bin_path.exists() or bin_path.stat().st_size < RECORD_SIZE:
        return False

    with open(bin_path, "rb") as f:
        while True:
            buf = f.read(RECORD_SIZE)
            if len(buf) < RECORD_SIZE:
                break

            t, x, y, z, vx, vy, vz = struct.unpack(RECORD_FORMAT, buf)

            r2 = x * x + y * y + z * z
            r = math.sqrt(r2)

            v2 = vx * vx + vy * vy + vz * vz
            ej = 0.5 * v2 - 1.5 * (x * x) + 0.5 * (z * z) - 3.0 / r + 4.5

            if ej <= 0.0:
                return True
    return False


def type_result_of(bin_path: Path):
    """.binを走査し，{一時捕獲，一時捕獲でない}，{捕獲，衝突，エスケープ}の計6通りに分ける"""
    is_temporary_capture = False
    is_1year_passed = False

    last_t = 0

    if not bin_path.exists() or bin_path.stat().st_size < RECORD_SIZE:
        return None, 0

    with open(bin_path, "rb") as f:
        while True:
            buf = f.read(RECORD_SIZE)
            if len(buf) < RECORD_SIZE:
                break

            t, x, y, z, vx, vy, vz = struct.unpack(RECORD_FORMAT, buf)
            last_t = t

            r2 = x * x + y * y + z * z
            r = math.sqrt(r2)
            v2 = vx * vx + vy * vy + vz * vz
            ej = 0.5 * v2 - 1.5 * (x * x) + 0.5 * (z * z) - 3.0 / r + 4.5

            if not is_1year_passed:
                if t >= 1.88:
                    is_1year_passed = True

            if ej > 0 and is_1year_passed:  # 1火星年経過時にJacobiが正: 一時捕獲
                is_temporary_capture = True

            if ej <= 0:  # 捕獲状態
                if is_temporary_capture:  # 一時捕獲を経由
                    return "Temporary-Capture", t
                else:  # 直接
                    return "Direct-Capture", t

            if r <= R_M_NORM:  # 火星に落ちた
                if is_temporary_capture:  # 一時捕獲を経由して衝突
                    return "Temporary-Collision", t
                else:  # 一時捕獲を経由せずに衝突
                    return "Direct-Collision", t

        # whileを抜ける = エスケープ
        if is_temporary_capture:  # 一時捕獲を経由してエスケープ
            return "Temporary-Escape", last_t
        else:  # 一時捕獲を経由せずにエスケープ
            return "Direct-Escape", last_t


def main():
    if not INPUT_DIR.exists():
        print(f"Error: 入力ディレクトリが見つかりません: {INPUT_DIR}")
        return

    v_results = []

    print("=== gas-drag 捕獲データの抽出開始 ===")

    for v in V0_LIST:
        print(f"v0 = {v} START.")
        v_results.clear()
        for angle_id in range(4096):
            bin_filepath = get_bin_path(v, angle_id)
            if not bin_filepath.exists():
                print(f"  [スキップ] {bin_filepath} が存在しません。")
                continue

            result, year = type_result_of(bin_filepath)
            if result is None:
                continue

            rec = {
                "v0": f"{v:.1f}",
                "ID": f"{angle_id:04d}",
                "year": f"{year:.15e}",
                "result": result,
            }
            v_results.append(rec)

            # 出力先ディレクトリの作成と書き込み
            output_file = OUTPUT_DIR / f"v{v:03d}.csv"
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # ヘッダ
                writer.writerow(["v0", "ID", "year", "result"])
                # 抽出データの書き出し
                for rec in v_results:
                    writer.writerow(
                        [
                            rec["v0"],
                            rec["ID"],
                            rec["year"],
                            rec["result"],
                        ]
                    )
            print(f"\rv = {v}, [{angle_id} / 4096]", end="")

        print(f"v = {v} FINITSH")

    # for v in V0_LIST:
    #     filename = f"v{v:03d}.csv"
    #     filepath = INPUT_DIR / filename

    #     if not filepath.exists():
    #         print(f"  [スキップ] {filename} が存在しません。")
    #         continue

    #     found_files += 1
    #     v_captures = []
    #     total_c_count = 0

    #     with open(filepath, "r", encoding="utf-8") as f:
    #         reader = csv.reader(f)
    #         for row in reader:
    #             # 空行やヘッダ行をスキップ
    #             if not row or row[0].startswith("#"):
    #                 continue

    #             # 列構成: ID(0), v0(1), phi0(2), zeta0(3), N(4), year(5), Capture/Escape/Survive(6)
    #             if len(row) >= 7 and row[6].strip() == "C":
    #                 total_c_count += 1
    #                 angle_id = int(row[0].strip())

    #                 bin_path = get_bin_path(v, angle_id=angle_id)

    #                 if is_caputured_by_jacobi(bin_path):
    #                     rec = {
    #                         "v0": f"{float(row[1].strip()):.1f}",
    #                         "ID": row[0].strip(),
    #                         "phi0": row[2].strip(),
    #                         "zeta0": row[3].strip(),
    #                         "N": row[4].strip(),
    #                         "year": row[5].strip(),
    #                     }
    #                     all_captured_rows.append(rec)
    #                     v_captures.append(row[0].strip())

    #     capture_ids_per_v[v] = set(v_captures)
    #     print(f"  v = {v:3d} m/s: 捕獲件数 {len(v_captures):4d} / 4096 件")

    # if found_files == 0:
    #     print("処理対象の CSV ファイルがありませんでした。")
    #     return

    # # 出力先ディレクトリの作成と書き込み
    # OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    # with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    #     writer = csv.writer(f)
    #     # ヘッダ
    #     writer.writerow(["v0", "ID", "phi0", "zeta0", "N", "year"])
    #     # 抽出データの書き出し
    #     for rec in all_captured_rows:
    #         writer.writerow(
    #             [rec["v0"], rec["ID"], rec["phi0"], rec["zeta0"], rec["N"], rec["year"]]
    #         )


if __name__ == "__main__":
    main()
