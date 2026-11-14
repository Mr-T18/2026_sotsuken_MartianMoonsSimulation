import argparse
import os
from pathlib import Path
import re
import struct

# 物理定数 (simulation.hpp / state.py と同一)
G = 6.67430e-11
M_SUN = 1.99e30
M_MARS = 6.42e23
AU = 1.495978707e11
R_M = 3396.2e3  # 火星赤道半径 [m]
MARS_SEMI_MAJOR_AXIS = 1.52368 * AU
R_H = MARS_SEMI_MAJOR_AXIS * (M_MARS / (3.0 * M_SUN)) ** (1.0 / 3.0)  # Hill半径 [m]

# 無次元Hill座標系における火星半径とその2乗
R_M_NORM = R_M / R_H
R_M_NORM_SQ = R_M_NORM**2

RECORD_STRUCT = struct.Struct("<7d")  # (t, x, y, z, vx, vy, vz) = 56 bytes


def calc_jacobi_energy(x: float, y: float, z: float, vx: float, vy: float, vz: float) -> float:
    """無次元Hill座標系におけるJacobiエネルギーを計算"""
    r = (x * x + y * y + z * z) ** 0.5
    v2 = vx * vx + vy * vy + vz * vz
    return 0.5 * v2 - 1.5 * (x * x) + 0.5 * (z * z) - (3.0 / r) + 4.5


def read_last_record(bin_path: Path):
    """バイナリファイルの末尾56バイト(最後の1ステップ)のみを読み取る"""
    with open(bin_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        if size < RECORD_STRUCT.size:
            return None
        f.seek(-RECORD_STRUCT.size, os.SEEK_END)
        raw = f.read(RECORD_STRUCT.size)
    return RECORD_STRUCT.unpack(raw)


def classify_result(orig_result: str, n_orbits: int, last_rec: tuple) -> str:
    """最終レコードと元の経過分類(Temporary/Direct)から新しいresult文字列を判定"""
    # 経過（Temporary / Direct）は元のCSVの値をそのまま引き継ぐ
    if orig_result.startswith("Temporary"):
        prefix = "Temporary"
    elif orig_result.startswith("Direct"):
        prefix = "Direct"
    else:
        prefix = "Direct" if n_orbits <= 1 else "Temporary"

    _, x, y, z, vx, vy, vz = last_rec
    r_sq = x * x + y * y + z * z

    if r_sq <= R_M_NORM_SQ:
        # 火星半径以下（落下）：落下時のJacobiエネルギーの正負で捕獲・衝突を判定
        ej = calc_jacobi_energy(x, y, z, vx, vy, vz)
        if ej < 0.0:
            return f"{prefix}-Capture"
        else:
            return f"{prefix}-Collision"
    else:
        # それ以外（脱出）：xの正負でL1/L2を判定
        if x < 0.0:
            return f"{prefix}-Escape-L1"
        else:
            return f"{prefix}-Escape-L2"


def process_csv_file(csv_path: Path, dry_run: bool = False) -> tuple[int, int, int]:
    """1つの vxxx.csv を処理し、vxxx_save.csv を出力する"""
    out_dir = csv_path.parent
    v0_str = csv_path.stem  # 例: "v020"
    v0_int = int(v0_str.replace("v", ""))
    bin_base_dir = out_dir / v0_str

    save_csv_path = out_dir / f"{v0_str}_save.csv"

    output_lines = []
    total_rows = 0
    changed_rows = 0
    missing_bins = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\r\n")
            if not stripped or stripped.lstrip().startswith("#"):
                output_lines.append(stripped + "\n")
                continue

            parts = stripped.split(",")
            if len(parts) < 7:
                output_lines.append(stripped + "\n")
                continue

            total_rows += 1
            id_str = parts[0].strip()
            id_int = int(id_str)
            n_orbits = int(parts[4].strip())
            orig_result = parts[6].strip()

            sub_dir = f"{id_int // 1024:02d}"
            bin_path = bin_base_dir / sub_dir / f"v{v0_int:03d}_{id_int:04d}.bin"

            last_rec = read_last_record(bin_path) if bin_path.exists() else None
            if last_rec is None:
                missing_bins += 1
                new_result = orig_result
            else:
                new_result = classify_result(orig_result, n_orbits, last_rec)

            if new_result != orig_result:
                changed_rows += 1

            # 元のCSVの最初の6列のフォーマットを一切崩さずresult列のみ置換
            prefix_cols = ",".join(parts[:6])
            output_lines.append(f"{prefix_cols},{new_result}\n")

    if not dry_run:
        with open(save_csv_path, "w", encoding="utf-8", newline="") as f:
            f.writelines(output_lines)

    return total_rows, changed_rows, missing_bins


def main():
    parser = argparse.ArgumentParser(
        description="binファイルの最終行からJacobiエネルギーと距離を判定し、vxxx_save.csvを作成する"
    )
    parser.add_argument(
        "--root",
        type=str,
        default="result/parameter",
        help="探索ルートディレクトリ (デフォルト: result/parameter)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ファイルを書き込まずに件数と変更数のみ確認する",
    )
    args = parser.parse_args()

    root_path = Path(args.root)
    if not root_path.exists():
        print(f"[Error] ディレクトリが見つかりません: {root_path}")
        return

    # v020.csv などの元サマリーCSVのみを対象（*_save.csv は除外）
    csv_files = sorted(
        p
        for p in root_path.glob("Obl-*_J2-*_Gas-*/out/v*.csv")
        if re.fullmatch(r"v\d{3}\.csv", p.name)
    )

    if not csv_files:
        print(f"[Warning] 対象のCSVファイルが見つかりませんでした: {root_path}")
        return

    print(f"Found {len(csv_files)} CSV files. (dry_run={args.dry_run})", flush=True)

    grand_total = 0
    grand_changed = 0
    grand_missing = 0

    for idx, csv_path in enumerate(csv_files, start=1):
        total, changed, missing = process_csv_file(csv_path, dry_run=args.dry_run)
        grand_total += total
        grand_changed += changed
        grand_missing += missing

        rel_path = csv_path.relative_to(root_path)
        print(
            f"[{idx:3d}/{len(csv_files):3d}] {rel_path} -> "
            f"rows: {total}, changed: {changed}, missing_bin: {missing}",
            flush=True,
        )

    print("-" * 60)
    print(
        f"Done! Files: {len(csv_files)}, Total rows: {grand_total}, "
        f"Changed: {grand_changed}, Missing bins: {grand_missing}"
    )


if __name__ == "__main__":
    main()
