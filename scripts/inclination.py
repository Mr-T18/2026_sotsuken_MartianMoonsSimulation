#!/usr/bin/env python3
import concurrent.futures
import os
from pathlib import Path
import shutil
import subprocess
import sys

# constants.hpp に基づく換算定数 (r_H / r_M)
RH_OVER_RM = 319.1632070652


def find_gnuplot():
    """gnuplotの実行ファイルを探索（Windows環境対応）"""
    for cmd in ["gnuplot", "gnuplot.exe"]:
        path = shutil.which(cmd)
        if path:
            return path

    # 一般的な Windows のデフォルトインストール先を探索
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
    """out 階層を figures/inclination に置き換える"""
    parts = list(bin_path.parts)
    if "out" in parts:
        idx = len(parts) - 1 - parts[::-1].index("out")
        new_parts = parts[:idx] + ["figures", "inclination"] + parts[idx + 1 :]
        return Path(*new_parts).with_suffix(".png")
    else:
        return bin_path.parent / "figures" / "inclination" / (bin_path.stem + ".png")


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

    gp_script = f"""\
set terminal pngcairo size 900,600 font 'Arial,10'
set output "{png_str}"

set xrange [0:50]
set yrange [0:35]

set xlabel "Distance from Mars center r [r_M]"
set ylabel "Orbital Inclination i [deg]"
set title "Inclination vs Distance: {title_label}"
set key outside right top

set arrow from 1.0, 0 to 1.0, 180 nohead lc rgb "#cc0000" dt 2 lw 1
set arrow from 0, 90 to 50, 90 nohead lc rgb "#888888" dt 2 lw 1

scale_rM = {RH_OVER_RM}
r_norm_rM(x, y, z) = sqrt(x*x + y*y + z*z) * scale_rM

hx(y, z, vy, vz) = y*vz - z*vy
hy(x, z, vx, vz) = z*vx - x*vz
hz(x, y, vx, vy) = x*vy - y*vx
h_norm(x, y, z, vx, vy, vz) = sqrt(hx(y,z,vy,vz)**2 + hy(x,z,vx,vz)**2 + hz(x,y,vx,vy)**2)

clamp(v) = (v > 1.0) ? 1.0 : ((v < -1.0) ? -1.0 : v)
cos_i(x, y, z, vx, vy, vz) = (h_norm(x,y,z,vx,vy,vz) > 1e-12) ? clamp(hz(x,y,vx,vy) / h_norm(x,y,z,vx,vy,vz)) : 1/0
inc_deg(x, y, z, vx, vy, vz) = acos(cos_i(x,y,z,vx,vy,vz)) * 180.0 / pi

plot "{bin_str}" binary format="%7double" using (r_norm_rM($2,$3,$4)):(inc_deg($2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#0066CC" title "Points"
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
        print("Usage: python plot_inclination.py <file_or_directory>")
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

    print(f"[Info] Found {total} .bin files. Preparing render tasks...")

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

    print("\n=== Result Summary ===")
    print(f"Successfully generated: {ok_count}")
    print(f"Skipped:                {skip_count}")
    print(f"Errors:                 {err_count}")


if __name__ == "__main__":
    main()
