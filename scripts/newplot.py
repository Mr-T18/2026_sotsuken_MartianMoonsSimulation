import concurrent.futures
import os
from pathlib import Path
import shutil
import subprocess
import sys

# ==============================================================================
# 設定パラメータ
# ==============================================================================
T_START = 0.0  # 描画開始時刻 [年] (None で最初から)
T_END = 5.0  # 描画終了時刻 [年] (None で最後まで)


def find_gnuplot():
    """gnuplotの実行ファイルを探索（Windows環境対応）"""
    for cmd in ["gnuplot", "gnuplot.exe"]:
        path = shutil.which(cmd)
        if path:
            return path

    typical_paths = [
        r"C:\Program Files\gnuplot\bin\gnuplot.exe",
        r"C:\Program Files (x86)\gnuplot\bin\gnuplot.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\gnuplot\bin\gnuplot.exe"),
    ]
    for p in typical_paths:
        if os.path.exists(p):
            return p

    return None


def convert_bin_to_png_path(bin_path: Path) -> Path:
    """out 階層を figures/trajectory に置き換えて出力先パスを決定

    例: result/bulge/out/v020/00/v020_0123.bin
     -> result/bulge/figures/trajectory/v020/00/v020_0123.png
    """
    parts = list(bin_path.parts)
    if "out" in parts:
        idx = len(parts) - 1 - parts[::-1].index("out")
        new_parts = parts[:idx] + ["figures", "trajectory"] + parts[idx + 1 :]
        return Path(*new_parts).with_suffix(".png")
    else:
        return bin_path.parent / "figures" / "trajectory" / (bin_path.stem + ".png")


def generate_single_plot(args):
    """1つのファイルをプロットし、詳細な実行結果を返す"""
    bin_path, png_path, gnuplot_bin = args

    # 1. ファイルサイズの検証
    try:
        size = bin_path.stat().st_size
    except OSError as e:
        return ("error", bin_path, f"Cannot read file stat: {e}")

    if size < 56:
        return (
            "skipped",
            bin_path,
            f"File empty or too small ({size} bytes). Run simulation first.",
        )

    # 2. 出力先ディレクトリを確実に作成
    try:
        png_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return ("error", bin_path, f"Failed to create directory: {e}")

    bin_str = bin_path.as_posix()
    png_str = png_path.as_posix()
    title_label = f"{bin_path.parent.name}/{bin_path.stem}"

    # 時間フィルタ条件の構築 (1列目 $1 が時刻 t)
    time_conditions = []
    if T_START is not None:
        time_conditions.append(f"$1 >= {T_START}")
    if T_END is not None:
        time_conditions.append(f"$1 <= {T_END}")

    if time_conditions:
        cond_str = " && ".join(time_conditions)
        # 条件を満たすときは x($2), 満たさないときは 1/0 (描画スキップ)
        using_clause = f"using (({cond_str}) ? $2 : 1/0):3"
    else:
        using_clause = "using 2:3"

    # タイトル用の時間表記
    time_title = ""
    if T_START is not None and T_END is not None:
        time_title = f" (t = {T_START:.1f} - {T_END:.1f} yr)"
    elif T_START is not None:
        time_title = f" (t >= {T_START:.1f} yr)"
    elif T_END is not None:
        time_title = f" (t <= {T_END:.1f} yr)"

    gp_script = f"""\
set terminal pngcairo size 600,600 font 'Arial,10'
set output "{png_str}"
set size ratio -1
set xrange [-1.5:1.5]
set yrange [-1.0:1.0]
set grid xtics ytics lc rgb "#cccccc" dt 3
set xlabel "x [r_H]"
set ylabel "y [r_H]"
set title "Trajectory {title_label}{time_title}"
set key top right

# Hill sphere (r = 1.0)
set object 1 circle at 0,0 size 1.0 fillcolor rgb "gray" fillstyle empty border lc rgb "#888888" dt 2 lw 1
# Mars
set object 2 circle at 0,0 size 0.025 fillcolor rgb "red" fillstyle solid border lc rgb "red"

# Binary Trajectory
plot "{bin_str}" binary format="%7double" {using_clause} with lines lc rgb "#9400D3" lw 1.2 title "Trajectory"
"""

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


def collect_bin_files(target_path: Path):
    """ファイルまたはディレクトリから .bin ファイルを再帰走査"""
    if not target_path.exists():
        print(f"[Error] Path not found: {target_path}")
        return []

    if target_path.is_file():
        return [target_path] if target_path.suffix == ".bin" else []

    bin_files = []
    for root, _, files in os.walk(target_path, followlinks=True):
        for f in files:
            if f.endswith(".bin"):
                bin_files.append(Path(root) / f)

    return sorted(bin_files)


def main():
    if len(sys.argv) < 2:
        print("Usage: python newplot.py <file_or_directory>")
        print("Examples:")
        print("  python newplot.py result/bulge")
        print("  python newplot.py result/gas-drag/out/v020")
        print("  python newplot.py result/bulge/out/v020/00/v020_0123.bin")
        return

    # 1. gnuplot の存在確認
    gnuplot_bin = find_gnuplot()
    if not gnuplot_bin:
        print("[Fatal Error] gnuplot is not found on your system.")
        print("Please install gnuplot or add its 'bin' directory to your PATH.")
        return
    print(f"[Info] Using gnuplot at: {gnuplot_bin}")

    # 2. 入力パスの検証と .bin ファイル収集
    input_path = Path(sys.argv[1])
    bin_files = collect_bin_files(input_path)
    total = len(bin_files)

    if total == 0:
        print(f"[Warning] No .bin files were found under '{input_path}'.")
        print(f"Current working directory is: {Path.cwd()}")
        return

    print(
        f"[Info] Found {total} .bin files. Rendering (t: {T_START} -> {T_END}" " yr)..."
    )

    # 3. 事前に親ディレクトリの作成を試みる
    sample_png = convert_bin_to_png_path(bin_files[0])
    sample_png.parent.mkdir(parents=True, exist_ok=True)
    print(f"[Info] Output destination example: {sample_png}")

    tasks = [(bp, convert_bin_to_png_path(bp), gnuplot_bin) for bp in bin_files]

    max_workers = os.cpu_count() or 4
    ok_count = 0
    skip_count = 0
    err_count = 0

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(generate_single_plot, t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            status, b_path, msg = future.result()
            if status == "ok":
                ok_count += 1
            elif status == "skipped":
                skip_count += 1
                print(f"  [Skipped] {b_path.name}: {msg}")
            else:
                err_count += 1
                print(f"  [Failed]  {b_path.name}: {msg}")

            completed = ok_count + skip_count + err_count
            if completed % 100 == 0 or completed == total:
                print(f"Progress: [{completed}/{total}] plots processed.")

    print("\n=== Result Summary ===")
    print(f"Successfully generated: {ok_count}")
    print(f"Skipped:                {skip_count}")
    print(f"Errors:                 {err_count}")


if __name__ == "__main__":
    main()
