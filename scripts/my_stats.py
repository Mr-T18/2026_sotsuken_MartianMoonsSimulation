"""
シミュレーション結果プロット管理スクリプト
"""

import argparse
import concurrent.futures
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys


def find_gnuplot():
    """gnuplotの実行ファイルを探索"""
    for cmd in ["gnuplot", "gnuplot.exe"]:
        path = shutil.which(cmd)
        if path:
            return path
    return None


def collect_bin_files(target_path: Path):
    """単一ファイルまたはディレクトリから，.binファイルを収集"""
    if not target_path.exists():
        print(f"[Error] パスが存在しません: {target_path}")
        return []

    ".bin拡張子の単一ファイルならそれを返す"
    if target_path.is_file():
        return [target_path] if target_path.suffix == ".bin" else []

    "ディレクトリなら再帰的に集める"
    bin_files = []
    for root, _, files in os.walk(target_path, followlinks=True):
        for f in files:
            if f.endswith(".bin"):
                bin_files.append(Path(root) / f)

    return sorted(bin_files)


def convert_bin_to_png_path(bin_path: Path, plot_type: str) -> Path:
    """out 階層を figures/<plot_type> に置き換えて出力パスを生成"""
    parts = list(bin_path.parts)
    if "out" in parts:
        idx = len(parts) - 1 - parts[::-1].index("out")
        new_parts = parts[:idx] + ["figures", plot_type] + parts[idx + 1 :]
        return Path(*new_parts).with_suffix(".png")
    else:
        return bin_path.parent / "figures" / plot_type / (bin_path.stem + ".png")


def worker_task(args):
    """並列プロセスで実行される1ファイル分の処理"""
    bin_path, png_path, gnuplot_bin, generate_script_func = args

    # ファイルサイズが56未満のものは除外
    try:
        size = bin_path.stat().st_size
    except OSError as e:
        return ("error", bin_path, f"ファイル読み取り失敗: {e}")

    if size < 56:
        return ("skipped", bin_path, f"空ファイル {size} bytes")

    # 出力先ディレクトリの作成
    try:
        png_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return ("error", bin_path, f"ディレクトリ作成失敗: {e}")

    # 各モジュールで定義された gnuplot スクリプト文字列を取得
    try:
        gp_script = generate_script_func(bin_path, png_path)
    except Exception as e:
        return ("error", bin_path, f"スクリプト生成エラー: {e}")

    # gnuplotの実行
    try:
        proc = subprocess.run(
            [gnuplot_bin],
            input=gp_script,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        if proc.returncode != 0:
            return ("error", bin_path, proc.stderr.strip())
        return ("ok", bin_path, "")
    except Exception as e:
        return ("error", bin_path, str(e))


def load_plot_module(plot_type: str):
    """コマンド引数の文字から指定のプロットモジュールを読み込む"""
    try:
        module = importlib.import_module(f"plot_modules.{plot_type}")
        if not hasattr(module, "get_gnuplot_script"):
            raise AttributeError(
                f"モジュール plot_modules/{plot_type} に get_gnuplot_script 関数がありません"
            )
        return module.get_gnuplot_script
    except ModuleNotFoundError:
        print("[Error] プロット {plot_type} に対応するモジュールが見つかりません")
        return None
    except Exception as e:
        print(f"[Error] モジュール読み込みエラー: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="シミュレーション結果プロット一括実行スクリプト"
    )
    parser.add_argument(
        "target_path", type=str, help="対象ファイルまたは親ディレクトリ"
    )
    parser.add_argument("plot_type", type=str, help="プロットタイプ")
    parser.add_argument(
        "--workers", type=int, default=os.cpu_count() or 4, help="並列プロセス数"
    )

    args = parser.parse_args()

    # gnuplotの確認
    gnuplot_bin = find_gnuplot()
    if not gnuplot_bin:
        print("[Error]: gnuplotがありません")
        return

    # プロット関数の取得
    script_func = load_plot_module(args.plot_type)
    if script_func is None:
        return

    # 対象バイナリファイルの整理
    target_path = Path(args.target_path)
    bin_files = collect_bin_files(target_path)
    total = len(bin_files)

    if total == 0:
        print(f"[Warning] {target_path} 配下に .bin ファイルが見つかりませんでした")
        return

    print(f"[Info] 対象ファイル数: {total} 件, プロットタイプ: {args.plot_type}")

    tasks = [
        (
            bp,
            convert_bin_to_png_path(bp, args.plot_type),
            gnuplot_bin,
            script_func,
        )
        for bp in bin_files
    ]

    ok_count = 0
    skip_count = 0
    err_count = 0

    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executer:
        futures = [executer.submit(worker_task, t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            status, b_path, msg = future.result()
            if status == "ok":
                ok_count += 1
            elif status == "skipped":
                skip_count += 1
            else:
                err_count += 1
                print(f"    [Failed] {b_path.name}: {msg}")
            completed = ok_count + skip_count + err_count
            if completed % 100 == 0 or completed == total:
                print(f"Progress: [{completed} / {total}] 件 完了")

    print("\n=== 実行結果 ===")
    print(f"成功:     {ok_count} 件")
    print(f"スキップ: {skip_count} 件")
    print(f"エラー:   {err_count} 件")


if __name__ == "__main__":
    main()
