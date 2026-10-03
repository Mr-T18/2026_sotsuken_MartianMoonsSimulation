import argparse
from pathlib import Path
import numpy as np

RECORD_BYTES = 56  # double 7個 = 56バイト


def print_binary_records(filepath: Path, num_lines: int, mode: str = "head"):
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        return

    file_size = filepath.stat().st_size
    if file_size == 0:
        print(f"Warning: File is empty: {filepath}")
        return

    total_records = file_size // RECORD_BYTES
    records_to_read = min(num_lines, total_records)

    print(f"File: {filepath} ({file_size} bytes, Total records: {total_records})")

    if mode == "tail":
        start_index = total_records - records_to_read
        print(f"Showing last {records_to_read} records:\n")
    else:
        start_index = 0
        print(f"Showing first {records_to_read} records:\n")

    # 対象位置までシークして指定レコード分のみ読み込み
    offset = start_index * RECORD_BYTES
    with open(filepath, "rb") as f:
        f.seek(offset)
        data = np.fromfile(f, dtype=np.float64, count=records_to_read * 7).reshape(
            -1, 7
        )

    headers = ["Index", "t [yr]", "x [rH]", "y [rH]", "z [rH]", "vx", "vy", "vz"]
    header_line = " ".join(headers)
    print(header_line)
    print("-" * len(header_line))

    # Indexと各数値を半角スペース1つで区切るフォーマット
    row_fmt = "{:d} " + " ".join(["{:.8e}"] * 7)

    for i, row in enumerate(data):
        print(row_fmt.format(start_index + i, *row))


def main():
    parser = argparse.ArgumentParser(
        description="Print records of Hill simulation binary file (.bin)"
    )
    parser.add_argument("filepath", type=Path, help="Path to the .bin file")
    parser.add_argument(
        "lines",
        type=int,
        nargs="?",
        default=10,
        help="Number of lines to display (default: 10)",
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["head", "tail"],
        default="head",
        help="Display mode: 'head' for beginning, 'tail' for end (default: head)",
    )

    args = parser.parse_args()
    print_binary_records(args.filepath, args.lines, args.mode)


if __name__ == "__main__":
    main()
