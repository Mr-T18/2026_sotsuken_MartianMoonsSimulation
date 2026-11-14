# 初速度ごとの生存時間のヒストグラムを作成


from pathlib import Path
import numpy as np
import pandas as pd

# 定数設定
BIN_WIDTH_YR = 2.0
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


# 捕獲されたタイミングを探す
# csvあるいはファイル内を走査し，必要な情報を辞書にして返す
def run_analysis(ctx: dict) -> dict:

    # コンテキストから入力csvを特定
    csv_path = Path(ctx["csv_path"])
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return None

    # csvを読み込み，不適切なデータなら例外処理
    try:
        df = pd.read_csv(csv_path, comment="#", header=None)
    except pd.errors.EmptyDataError:
        return None
    if df.empty or df.shape[1] < 7:
        return None

    df.columns = ["ID", "v0", "phi0", "zeta0", "N", "year", "result"]
    captured_ids = df[df["result"].astype(str).str.contains("-Capture")]["ID"].tolist()

    lifetimes = []

    for fid in captured_ids:
        fid = int(fid)
        bin_path = (
            ctx["bin_dir"] / f"{fid // 1024:02d}" / f"v{ctx["v0"]:03d}_{fid:04d}.bin"
        )
        if not bin_path.exists() or bin_path.stat().st_size < 112:
            continue

        try:
            n_records = bin_path.stat().st_size // 56
            m = np.memmap(bin_path, dtype=RECORD_DTYPE, mode="r", shape=(n_records,))

            lifetime = float(m[-1]["t"])

            if lifetime is not None:
                lifetimes.append(lifetime)

        except Exception:
            continue
    print(
        f"[v{ctx['v0']:03d}] Vaild: {len(lifetimes)} / {len(captured_ids)}",
        flush=True,
    )
    return {"v0": ctx["v0"], "lifetimes": lifetimes}


def aggregate_results(results: list, filter_info: dict, run_gnuplot):
    # 初速度ごとのリストを取り出し
    lifetime_dict = {r["v0"]: r["lifetimes"] for r in results if r and "lifetimes" in r}
    all_records = [t for times in lifetime_dict.values() for t in times]

    if not all_records:
        print("[Warning] 有効な捕獲データがありませんでした")
        return

    # コマンド引数から識別子を作成
    obl = filter_info.get("obl")
    j2 = filter_info.get("j2")
    gas = filter_info.get("gas")
    v0 = filter_info.get("v0")
    out = filter_info.get("out")
    tag = f"Obl-{obl:03d}_J2-{j2}_Gas-{gas}"

    # 出力先ディレクトリ
    stats_dir = Path("stats")

    figures_dir = Path("stats/lifetime/figure")
    data_dir = Path("stats/lifetime/data")
    stats_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # 10年刻みのビン設定
    max_val = max(all_records)
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

    # 各初速度(v020 - v160)の度数および割合を計算
    for v in VELOCITIES:
        lifetimes = lifetime_dict.get(v, [])
        counts, _ = np.histogram(lifetimes, bins=bins)
        df_count[f"v{v:03d}_count"] = counts

        total_v = len(lifetimes)
        df_prob[f"v{v:03d}_prob"] = counts / total_v if total_v > 0 else 0.0

    raw_csv = data_dir / f"lifetime_raw_{tag}.csv"
    prob_csv = data_dir / f"lifetime_prob_{tag}.csv"
    df_count.to_csv(raw_csv, index=False)
    df_prob.to_csv(prob_csv, index=False)
    print(f"[Saved CSV] {raw_csv}")
    print(f"[Saved CSV] {prob_csv}")

    # gnuplot スクリプトの生成と実行（初速度ごとに8枚）
    csv_str = prob_csv.resolve().as_posix()
    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()
    load_config = f'load "{config_path}"\n' if Path(config_path).exists() else ""

    for idx, v in enumerate(VELOCITIES):
        col_idx = 4 + idx
        png_path = figures_dir / f"lifetime_{tag}_v{v:03d}.png"
        png_str = png_path.resolve().as_posix()

        script = f"""\
{load_config} set terminal pngcairo size 900, 550 font "MS Gothic,18"
set output "{png_str}"            
set datafile separator ","
set title "Lifetime: v0 = {v} m/s ({tag})" noenhanced
set xlabel "Lifetime [yr]"
set ylabel "Probability"
set xrange[0:*]
set yrange[0:*]
set grid ytics lc rgb "#cccccc" dt 2
set style fill solid 0.7 border -1
set boxwidth {BIN_WIDTH_YR}
plot "{csv_str}" u ($1 + {BIN_WIDTH_YR / 2.0}):{col_idx} every ::1 with boxes lc rgb "#0066CC" notitle            
"""
        run_gnuplot(script)
        print(f"[Saved PNG] {png_path}")
