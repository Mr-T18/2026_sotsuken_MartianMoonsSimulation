import argparse
from pathlib import Path
import numpy as np


def print_binary_records(filepath: Path, num_lines: int):
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        return

    file_size = filepath.stat().st_size
    if file_size == 0:
        print(f"Warning: File is empty: {filepath}")
        return

    total_records = file_size // 56
    print(f"File: {filepath} ({file_size} bytes, Total records: {total_records})")
    print(f"Showing first {min(num_lines, total_records)} records:\n")

    # 指定行数分だけ読み込み (1行 = double 7個 = 56バイト)
    read_count = num_lines * 7
    data = np.fromfile(filepath, dtype=np.float64, count=read_count).reshape(-1, 7)

    # ヘッダーの表示
    headers = ["Index", "t [yr]", "x [rH]", "y [rH]", "z [rH]", "vx", "vy", "vz"]
    header_fmt = "{:>6} {:>16} {:>16} {:>16} {:>16} {:>16} {:>16} {:>16}"
    row_fmt = (
        "{:>6d} {:>16.8e} {:>16.8e} {:>16.8e} {:>16.8e} {:>16.8e} {:>16.8e} {:>16.8e}"
    )

    print(header_fmt.format(*headers))
    print("-" * 125)

    for i, row in enumerate(data):
        print(row_fmt.format(i, *row))


def main():
    parser = argparse.ArgumentParser(
        description="Print first N records of Hill simulation binary file (.bin)"
    )
    parser.add_argument("filepath", type=Path, help="Path to the .bin file")
    parser.add_argument(
        "lines",
        type=int,
        nargs="?",
        default=10,
        help="Number of lines to display (default: 10)",
    )

    args = parser.parse_args()
    print_binary_records(args.filepath, args.lines)


if __name__ == "__main__":
    main()
