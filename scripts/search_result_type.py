import argparse
from pathlib import Path
import sys
import pandas as pd


def resolve_target_columns(type1: str | None, type2: str | None) -> list[str]:
    t1 = type1.lower() if type1 else None
    t2 = type2.lower() if type2 else None

    if t1 and t2:
        prefix = "direct" if t1 == "direct" else "temp"
        return [f"{prefix}_{t2}"]
    if t1 and not t2:
        return [f"{t1}_total", f"{t1}_rate"]
    if not t1 and t2:
        return [f"{t2}_total", f"{t2}_rate"]
    return [
        "total_runs",
        "escape_total",
        "collision_total",
        "capture_total",
        "direct_total",
        "temporary_total",
    ]


def main():
    parser = argparse.ArgumentParser(
        description="result_type_summary.csv から指定条件に一致する項目と数値を抽出する"
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="stats/result_type_summary.csv",
        help="対象CSVファイルのパス (デフォルト: stats/result_type_summary.csv)",
    )
    parser.add_argument(
        "--Obl", type=int, default=None, help="自転軸傾斜角 obl (例: 25)"
    )
    parser.add_argument(
        "--J2", type=str, default=None, help="J2 パラメータ (No, Small, Medium, Large)"
    )
    parser.add_argument(
        "--Gas", type=str, default=None, help="Gas パラメータ (Small, Medium, Large)"
    )
    parser.add_argument("--v0", type=int, default=None, help="初速度 v0 (例: 20)")
    parser.add_argument(
        "--type1",
        type=str,
        default=None,
        choices=["Direct", "Temporary"],
        help="捕獲・通過タイプ1 (Direct または Temporary)",
    )
    parser.add_argument(
        "--type2",
        type=str,
        default=None,
        choices=["Capture", "Collision", "Escape"],
        help="最終結果タイプ2 (Capture, Collision, Escape)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"[Error] CSVファイルが見つかりません: {csv_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(csv_path)

    # 条件フィルタリング
    cond = pd.Series(True, index=df.index)
    if args.Obl is not None:
        cond &= df["obl"] == args.Obl
    if args.J2 is not None:
        cond &= df["j2"].astype(str).str.lower() == args.J2.lower()
    if args.Gas is not None:
        cond &= df["gas"].astype(str).str.lower() == args.Gas.lower()
    if args.v0 is not None:
        cond &= df["v0"] == args.v0

    filtered = df[cond]
    if filtered.empty:
        print("[Info] 指定された条件に一致するデータが見つかりませんでした。")
        sys.exit(0)

    key_cols = ["obl", "j2", "gas", "v0"]
    val_cols = resolve_target_columns(args.type1, args.type2)
    out_df = filtered[key_cols + val_cols]

    # 1行のみ一致した場合は項目名と数値を分かりやすく表示
    if len(out_df) == 1:
        row = out_df.iloc[0]
        print(
            f"Condition: Obl={row['obl']}, J2={row['j2']}, Gas={row['gas']}, v0={row['v0']}"
        )
        for col in val_cols:
            val = row[col]
            if isinstance(val, float) and col.endswith("_rate"):
                print(f"  {col}: {val:.6f} ({val * 100:.2f}%)")
            else:
                print(f"  {col}: {val}")
    else:
        print(out_df.to_string(index=False))


if __name__ == "__main__":
    main()
