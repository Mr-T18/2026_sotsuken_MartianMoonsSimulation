import argparse
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import time

# 物理定数 (simulation.hpp / state.py と同一)
G = 6.67430e-11
M_SUN = 1.99e30
M_MARS = 6.42e23
AU = 1.495978707e11
R_M = 3396.2e3  # 火星赤道半径 [m]
MARS_SEMI_MAJOR_AXIS = 1.52368 * AU
R_H = MARS_SEMI_MAJOR_AXIS * (M_MARS / (3.0 * M_SUN)) ** (1.0 / 3.0)  # Hill半径 [m]

# 無次元Hill座標系における火星半径とその2乗・脱出境界 (r > 2.0 r_H -> r^2 > 4.0)
R_M_NORM = R_M / R_H
R_M_NORM_SQ = R_M_NORM**2
ESCAPE_R_SQ = 4.0

RECORD_STRUCT = struct.Struct("<7d")  # (t, x, y, z, vx, vy, vz) = 56 bytes

# デフォルトの走査対象ディレクトリ (Obl-025, J2-Medium固定, Gas可変)
DEFAULT_TARGET_DIRS = [
    "Obl-025_J2-Medium_Gas-Large",
    "Obl-025_J2-Medium_Gas-Medium",
    "Obl-025_J2-Medium_Gas-Small",
]


def calc_jacobi_energy(
    x: float, y: float, z: float, vx: float, vy: float, vz: float
) -> float:
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
    if orig_result.startswith("Temporary"):
        prefix = "Temporary"
    elif orig_result.startswith("Direct"):
        prefix = "Direct"
    else:
        prefix = "Direct" if n_orbits <= 1 else "Temporary"

    _, x, y, z, vx, vy, vz = last_rec
    r_sq = x * x + y * y + z * z

    if r_sq <= R_M_NORM_SQ:
        ej = calc_jacobi_energy(x, y, z, vx, vy, vz)
        if ej <= 0.0:
            return f"{prefix}-Capture"
        else:
            return f"{prefix}-Collision"
    elif r_sq > ESCAPE_R_SQ:
        if x < 0.0:
            return f"{prefix}-Escape-L1"
        else:
            return f"{prefix}-Escape-L2"
    else:
        return f"{prefix}-Survive"


def render_progress_bar(current: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return "[" + "-" * width + "] 100.0%"
    ratio = min(max(current / total, 0.0), 1.0)
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {ratio * 100:5.1f}% ({current}/{total})"


def process_csv_file(
    csv_path: Path,
    file_idx: int,
    total_files: int,
    root_path: Path,
    dry_run: bool = False,
    backup: bool = False,
) -> tuple[int, int, int, int]:
    """1つの vxxx.csv を処理し、進捗を表示しながら vxxx.csv を更新する"""
    out_dir = csv_path.parent
    v0_str = csv_path.stem  # 例: "v020"
    v0_int = int(v0_str.replace("v", ""))
    bin_base_dir = out_dir / v0_str

    with open(csv_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    total_data_rows = sum(
        1
        for line in raw_lines
        if line.strip()
        and not line.lstrip().startswith("#")
        and len(line.split(",")) >= 7
    )

    output_lines = []
    processed_rows = 0
    changed_rows = 0
    survive_rows = 0
    missing_bins = 0

    rel_path = csv_path.relative_to(root_path)
    header_prefix = f"[{file_idx:2d}/{total_files:2d}] {rel_path}"

    for line in raw_lines:
        stripped = line.rstrip("\r\n")
        if not stripped or stripped.lstrip().startswith("#"):
            output_lines.append(stripped + "\n")
            continue

        parts = stripped.split(",")
        if len(parts) < 7:
            output_lines.append(stripped + "\n")
            continue

        processed_rows += 1
        id_str = parts[0].strip()
        id_int = int(id_str)
        n_orbits = int(parts[4].strip())
        orig_result = parts[6].strip()

        sub_dir = f"{id_int // 1024:02d}"
        bin_path = bin_base_dir / sub_dir / f"v{v0_int:03d}_{id_int:04d}.bin"

        try:
            last_rec = read_last_record(bin_path)
        except FileNotFoundError:
            last_rec = None

        if last_rec is None:
            missing_bins += 1
            new_result = orig_result
        else:
            new_result = classify_result(orig_result, n_orbits, last_rec)

        if new_result != orig_result:
            changed_rows += 1
        if new_result.endswith("-Survive"):
            survive_rows += 1

        prefix_cols = ",".join(parts[:6])
        output_lines.append(f"{prefix_cols},{new_result}\n")

        if processed_rows % 256 == 0 or processed_rows == total_data_rows:
            bar = render_progress_bar(processed_rows, total_data_rows)
            sys.stdout.write(
                f"\r{header_prefix} {bar} | changed:{changed_rows} survive:{survive_rows} missing:{missing_bins}"
            )
            sys.stdout.flush()

    sys.stdout.write("\n")
    sys.stdout.flush()

    if not dry_run and changed_rows > 0:
        if backup:
            backup_path = out_dir / f"{v0_str}.csv.bak"
            shutil.copy2(csv_path, backup_path)

        tmp_path = out_dir / f"{v0_str}.csv.tmp"
        with open(tmp_path, "w", encoding="utf-8", newline="") as f:
            f.writelines(output_lines)
        os.replace(tmp_path, csv_path)

    return processed_rows, changed_rows, survive_rows, missing_bins


def format_duration(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"


def main():
    parser = argparse.ArgumentParser(
        description="指定ディレクトリのbinファイル最終行からJacobiエネルギーと距離を判定し、vxxx.csvを更新する"
    )
    parser.add_argument(
        "--root",
        type=str,
        default="result/parameter",
        help="探索ルートディレクトリ (デフォルト: result/parameter)",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        default=DEFAULT_TARGET_DIRS,
        help="対象パラメータディレクトリ名 (デフォルト: Obl-025_J2-Medium_Gas-{Large,Medium,Small})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ファイルを書き込まずに件数と変更数のみ確認する",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="変更がある場合に元のファイルを vxxx.csv.bak として保存する",
    )
    args = parser.parse_args()

    root_path = Path(args.root)
    if not root_path.exists():
        print(f"[Error] ディレクトリが見つかりません: {root_path}")
        return

    csv_files = []
    for target_name in args.targets:
        out_dir = root_path / target_name / "out"
        if not out_dir.exists():
            print(f"[Warning] ディレクトリが見つかりません（スキップ）: {out_dir}")
            continue
        csv_files.extend(
            sorted(
                p
                for p in out_dir.glob("v*.csv")
                if re.fullmatch(r"v\d{3}\.csv", p.name)
            )
        )

    if not csv_files:
        print("[Warning] 対象のCSVファイルが見つかりませんでした。")
        return

    total_files = len(csv_files)
    print(
        f"Target dirs: {', '.join(args.targets)}\n"
        f"Found {total_files} CSV files. (dry_run={args.dry_run}, backup={args.backup})",
        flush=True,
    )
    print("-" * 80, flush=True)

    grand_total = 0
    grand_changed = 0
    grand_survive = 0
    grand_missing = 0
    start_time = time.time()

    for idx, csv_path in enumerate(csv_files, start=1):
        total, changed, survive, missing = process_csv_file(
            csv_path,
            file_idx=idx,
            total_files=total_files,
            root_path=root_path,
            dry_run=args.dry_run,
            backup=args.backup,
        )
        grand_total += total
        grand_changed += changed
        grand_survive += survive
        grand_missing += missing

        if idx % 8 == 0 or idx == total_files:
            elapsed = time.time() - start_time
            avg_per_file = elapsed / idx
            eta = avg_per_file * (total_files - idx)
            print(
                f"  >> Overall: {idx}/{total_files} files ({idx / total_files * 100:.1f}%) | "
                f"Elapsed: {format_duration(elapsed)} | ETA: {format_duration(eta)} | "
                f"Total changed: {grand_changed} (Survive: {grand_survive})",
                flush=True,
            )

    total_elapsed = time.time() - start_time
    print("-" * 80)
    print(
        f"Done in {format_duration(total_elapsed)}! "
        f"Files: {total_files}, Total rows: {grand_total}, "
        f"Changed: {grand_changed}, Survive: {grand_survive}, Missing bins: {grand_missing}"
    )


if __name__ == "__main__":
    main()
