import argparse
from concurrent.futures import ProcessPoolExecutor
import importlib
from pathlib import Path
import shutil
import subprocess
import sys
import pandas as pd


# gnuplotの実行環境を探して返す
def find_gnuplot():
    for cmd in ["gnuplot", "gnuplot.exe"]:
        path = shutil.which(cmd)
        if path:
            return path
    return None


def run_gnuplot(script: str, gnuplot_bin: str = None) -> bool:
    if gnuplot_bin is None:
        gnuplot_bin = find_gnuplot()
    if not gnuplot_bin:
        print("[Warning] gnuplot が見つかりません", file=sys.stderr)
        return False

    # サブプロセスでgnuplotを実行
    try:
        proc = subprocess.run(
            [gnuplot_bin],
            input=script,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        if proc.stderr.strip():
            print(f"[gnuplot log]\n{proc.stderr.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"[gnuplot execution failed] {e}", file=sys.stderr)
        return False


# csvのパスを受け取って設定コンテキストにして返す
def parse_context(csv_path: Path) -> dict:
    param_dir = csv_path.parents[1].name
    obl_str, j2_str, gas_str = param_dir.split("_")
    return {
        "obl": int(obl_str.split("-")[1]),
        "j2": j2_str.split("-")[1],
        "gas": gas_str.split("-")[1],
        "v0": int(csv_path.stem.replace("v", "")),
        "csv_path": csv_path,
        "bin_dir": csv_path / csv_path.stem,
        "out_dir": csv_path.parent,
    }


def worker_task(ctx: dict, module_name: str) -> list:
    mod = importlib.import_module(module_name)
    return mod.run_analysis(ctx)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("metric", type=str)
    parser.add_argument("--root", type=str, default="result/parameter")
    parser.add_argument("--Obl", type=int, default=None)
    parser.add_argument("--J2", type=str, default=None)
    parser.add_argument("--Gas", type=str, default=None)
    parser.add_argument("--v0", type=int, default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    # モジュール探索
    mod = None
    module_name = None
    full_name = f"stats_modules.{args.metric}"
    try:
        mod = importlib.import_module(full_name)
        module_name = full_name
    except ModuleNotFoundError:
        mod = None
        module_name = None

    if mod is None or module_name is None:
        print(f"[ERROR]: Module '{args.metric}' not found.", file=sys.stderr)
        sys.exit(1)

    # コマンド引数からフォルダ名のフォーマットを構築
    root_path = Path(args.root)
    obl_pat = f"Obl-{args.Obl:03d}" if args.Obl is not None else "Obl-*"
    j2_pat = f"J2-{args.J2}" if args.J2 is not None else "J2-*"
    gas_pat = f"Gas-{args.Gas}" if args.Gas is not None else "Gas-*"
    v0_pat = f"v{args.v0:03d}.csv" if args.v0 is not None else "v*.csv"

    # フォルダ名の下のcsvファイルを検索してリスト化
    search_pattern = f"{obl_pat}_{j2_pat}_{gas_pat}/out/{v0_pat}"
    target_csv_files = sorted(list(root_path.glob(search_pattern)))

    if not target_csv_files:
        print(f"No files matched: {root_path / search_pattern}", file=sys.stderr)
        sys.exit(1)

    target_contexts = [parse_context(p) for p in target_csv_files]
    print(f"Processing {len(target_contexts)} units.")

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        worker_outputs = list(
            executor.map(
                worker_task,
                target_contexts,
                [module_name] * len(target_contexts),
            )
        )

    # 各ワーカーが返したリスト（辞書）を1つに統合
    all_records = []
    for out in worker_outputs:
        if out is not None:
            if isinstance(out, list):
                all_records.extend(out)
            else:
                all_records.append(out)

    filter_info = {
        "obl": args.Obl,
        "j2": args.J2,
        "gas": args.Gas,
        "v0": args.v0,
        "out": args.out,
    }

    gnuplot_bin = find_gnuplot()

    def gnuplot_runner(srcipt: str) -> bool:
        return run_gnuplot(srcipt, gnuplot_bin=gnuplot_bin)

    if hasattr(mod, "aggregate_results"):
        mod.aggregate_results(
            all_records, filter_info=filter_info, run_gnuplot=gnuplot_runner
        )
    else:
        df = pd.DataFrame(all_records)
        out_csv = (
            Path(args.out) if args.out else Path(f"stats/{args.metric}_summary.csv")
        )
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_csv, index=False)
        print(f"Saved: {out_csv}")


if __name__ == "__main__":
    main()
