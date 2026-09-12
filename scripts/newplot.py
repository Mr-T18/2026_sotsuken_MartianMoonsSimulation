import concurrent.futures
import os
from pathlib import Path
import subprocess

# ==============================================================================
# 設定パラメータ
# ==============================================================================
T_START = 0.0  # 描画開始時刻 [年] (None で最初から)
T_END = 5.0  # 描画終了時刻 [年] (None で最後まで)

GNUPLOT_CMD = "gnuplot"


def generate_single_plot(args):
    bin_path, png_path, title_label = args

    # if png_path.exists():
    #     return True

    if bin_path.stat().st_size < 56:
        return False

    png_path.parent.mkdir(parents=True, exist_ok=True)

    bin_str = bin_path.as_posix()
    png_str = png_path.as_posix()

    # 時間フィルタ条件の構築 (1列目 $1 が時刻 t)
    time_conditions = []
    if T_START is not None:
        time_conditions.append(f"$1 >= {T_START}")
    if T_END is not None:
        time_conditions.append(f"$1 <= {T_END}")

    if time_conditions:
        cond_str = " && ".join(time_conditions)
        # 条件を満たすときは x($2), 満たさないときは 1/0 (スキップ)
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
set terminal pngcairo size 600,600
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
        subprocess.run(
            [GNUPLOT_CMD],
            input=gp_script,
            text=True,
            encoding="utf-8",
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else "Unknown error"
        print(f"Error processing {bin_path.name}: {err_msg}")
        return False


def main():
    out_dir = Path("out")
    figures_dir = Path("figures/trajectory")

    bin_files = []
    for root, _, files in os.walk(out_dir, followlinks=True):
        for f in files:
            if f.endswith(".bin"):
                bin_files.append(Path(root) / f)

    bin_files = sorted(bin_files)
    total_files = len(bin_files)
    print(f"Found {total_files} binary files in '{out_dir}'.")

    if total_files == 0:
        print("No .bin files found.")
        return

    tasks = []
    for bin_path in bin_files:
        try:
            rel_path = bin_path.relative_to(out_dir)
        except ValueError:
            rel_path = bin_path.relative_to(out_dir.resolve())

        png_path = (figures_dir / rel_path).with_suffix(".png")
        title_label = f"{rel_path.parent.as_posix()}/{bin_path.stem}"
        tasks.append((bin_path, png_path, title_label))

    max_workers = os.cpu_count() or 4
    print(f"Rendering (t: {T_START} -> {T_END} yr) with {max_workers} processes...")

    completed = 0
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(generate_single_plot, task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            if completed % 100 == 0 or completed == total_files:
                print(f"Progress: [{completed}/{total_files}] plots rendered.")

    print("All plots completed successfully.")


if __name__ == "__main__":
    main()
