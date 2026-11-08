from pathlib import Path
import numpy as np
import pandas as pd

# 定数設定
TIME_UNIT_FACTOR = 1.0
BIN_WIDTH_YR = 100.0
VELOCITIES = [20, 40, 60, 80, 100, 120, 140, 160]
RECORD_DTYPE = np.dtype(
    [
        ("t", "<f8"),
        ("x", "<f8"),
        ("y", "<f8"),
        ("z", "<f8"),
        ("vx", "<f8"),
        ("vy", "<f8"),
        ("vz", "<f8"),
    ]
)


def run_analysis(ctx: dict) -> dict:
    csv_path = Path(ctx["csv_path"])
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return None

    try:
        df = pd.read_csv(csv_path, comment="#", header=None)
    except pd.errors.EmptyDataError:
        return None
    if df.empty or df.shape[1] < 7:
        return None

    df.columns = ["ID", "v0", "phi0", "zeta0", "N", "year", "result"]
    captured_ids = df[df["result"].astype(str).str.contains("-Capture")]["ID"].tolist()

    decay_times = []

    for fid in captured_ids:
        fid = int(fid)
        bin_path = (
            ctx["bin_dir"] / f"{fid // 1024:02d}" / f"v{ctx['v0']:03d}_{fid:04d}.bin"
        )
        if not bin_path.exists() or bin_path.stat().st_size < 112:
            continue

        try:
            n_records = bin_path.stat().st_size // 56
            m = np.memmap(bin_path, dtype=RECORD_DTYPE, mode="r", shape=(n_records,))

            t_end = float(m[-1]["t"]) / TIME_UNIT_FACTOR
            t_cap = None

            # 4096ステップ単位で Jacobi エネルギーを評価
            for start in range(0, n_records, 4096):
                chunk = m[start : min(start + 4096, n_records)]
                r = np.maximum(
                    np.sqrt(chunk["x"] ** 2 + chunk["y"] ** 2 + chunk["z"] ** 2),
                    1e-10,
                )
                v_sq = chunk["vx"] ** 2 + chunk["vy"] ** 2 + chunk["vz"] ** 2
                u_eff = (
                    -1.5 * (chunk["x"] ** 2) + 0.5 * (chunk["z"] ** 2) - (3.0 / r) + 4.5
                )
                j_energy = 0.5 * v_sq + u_eff

                neg_idx = np.where(j_energy < 0.0)[0]
                if len(neg_idx) > 0:
                    t_cap = float(chunk["t"][neg_idx[0]]) / TIME_UNIT_FACTOR
                    break

            if t_cap is not None and t_end >= t_cap:
                decay_times.append(t_end - t_cap)
        except Exception:
            continue

    print(
        f"[v{ctx['v0']:03d}] Valid: {len(decay_times)} / {len(captured_ids)}",
        flush=True,
    )
    return {"v0": ctx["v0"], "decay_times": decay_times}


def aggregate_results(results: list, filter_info: dict, run_gnuplot):
    # 初速度ごとのリストを取り出し
    decay_dict = {
        r["v0"]: r["decay_times"] for r in results if r and "decay_times" in r
    }
    all_times = [t for times in decay_dict.values() for t in times]

    if not all_times:
        print("[Warning] 有効な捕獲データがありませんでした。")
        return

    # コマンド引数から識別子を作成
    obl = filter_info.get("obl")
    j2 = filter_info.get("j2")
    gas = filter_info.get("gas")
    tag = f"Obl-{obl:03d}_J2-{j2}_Gas-{gas}"

    # 出力先ディレクトリ
    stats_dir = Path("stats")

    figures_dir = Path("stats/capture_fall_time")
    stats_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # 100年刻みのビン設定
    max_val = max(all_times)
    max_edge = (
        np.ceil(max_val / BIN_WIDTH_YR) * BIN_WIDTH_YR if max_val > 0 else BIN_WIDTH_YR
    )
    bins = np.arange(0, max_edge + BIN_WIDTH_YR, BIN_WIDTH_YR)

    # 集約用データフレームの作成
    bin_starts = bins[:-1].astype(int)
    bin_ends = bins[1:].astype(int)
    bin_labels = [f"{s}-{e}" for s, e in zip(bin_starts, bin_ends)]

    df_count = pd.DataFrame(
        {
            "bin_start": bin_starts,
            "bin_end": bin_ends,
            "bin_label": bin_labels,
        }
    )
    df_prob = df_count.copy()

    # 各初速度（v020〜v160）の度数および割合を計算
    for v in VELOCITIES:
        times = decay_dict.get(v, [])
        counts, _ = np.histogram(times, bins=bins)
        df_count[f"v{v:03d}_count"] = counts

        total_v = len(times)
        df_prob[f"v{v:03d}_prob"] = counts / total_v if total_v > 0 else 0.0

    raw_csv = stats_dir / f"capture_fall_time_raw_{tag}.csv"
    prob_csv = stats_dir / f"capture_fall_time_prob_{tag}.csv"
    df_count.to_csv(raw_csv, index=False)
    df_prob.to_csv(prob_csv, index=False)
    print(f"[Saved CSV] {raw_csv}")
    print(f"[Saved CSV] {prob_csv}")

    # gnuplot スクリプト生成と実行（初速度別に8枚）
    csv_str = prob_csv.resolve().as_posix()
    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()
    load_config = f'load "{config_path}"\n' if Path(config_path).exists() else ""

    for idx, v in enumerate(VELOCITIES):
        col_idx = 4 + idx  # 4列目(v020_prob)から11列目(v160_prob)
        png_path = figures_dir / f"capture_fall_time_{tag}_v{v:03d}.png"
        png_str = png_path.resolve().as_posix()

        script = f"""\
{load_config}set terminal pngcairo size 900, 550 font "Arial,11"
set output "{png_str}"
set datafile separator ","
set title "Decay Time: v0 = {v} m/s ({tag})" noenhanced
set xlabel "Decay Timescale [yr]"
set ylabel "Probability"
set yrange [0:*]
set grid ytics lc rgb "#cccccc" dt 2
set style fill solid 0.7 border -1
set boxwidth {BIN_WIDTH_YR}
plot "{csv_str}" using ($1 + {BIN_WIDTH_YR / 2.0}):{col_idx} every ::1 with boxes lc rgb "#0066CC" notitle
"""
        run_gnuplot(script)
        print(f"[Saved PNG] {png_path}")
