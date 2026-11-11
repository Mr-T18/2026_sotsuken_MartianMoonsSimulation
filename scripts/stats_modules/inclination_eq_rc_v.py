from pathlib import Path
import numpy as np
import pandas as pd

# 定数設定
TIME_UNIT_FACTOR = 1.0
BIN_WIDTH_DEG = 5.0
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
G = 6.67430e-11
M_SUN = 1.99e30
AU = 1.495978707e11
MARS_SEMI_MAJOR_AXIS = 1.52368 * AU

SEC_PER_YEAR = 365.25 * 86400
OMEGA_K = np.sqrt(G * M_SUN / np.power(MARS_SEMI_MAJOR_AXIS, 3))
PHI = 25.0 * np.pi / 180.0

RH_OVER_RM = 319.1632070652  # Hill半径 [火星半径]
R_COROT_RM = 6.015  # 共回転半径 [火星半径]


def compute_semi_major_axis_rM(x, y, z, vx, vy, vz):
    """位置と速度から軌道長半径[rM]を算出"""
    r = np.sqrt(x**2 + y**2 + z**2)
    v_in_sq = (vx - y) ** 2 + (vy + x) ** 2 + vz**2

    inv_a = (2.0 / r) - (v_in_sq / 3.0)

    a_rH = np.where(inv_a > 0.0, 1.0 / inv_a, np.nan)
    return a_rH * RH_OVER_RM


def compute_eccentricity(x, y, z, vx, vy, vz):
    """位置と速度から離心率を算出"""
    r = np.sqrt(x**2 + y**2 + z**2)
    vx_in = vx - y
    vy_in = vy + x
    vz_in = vz
    v_in_sq = vx_in**2 + vy_in**2 + vz_in**2

    # 慣性系比角運動量ベクトル
    hx = y * vz_in - z * vy_in
    hy = z * vx_in - x * vz_in
    hz = x * vy_in - y * vx_in
    h_sq = hx**2 + hy**2 + hz**2

    # 比軌道エネルギー
    eps = 0.5 * v_in_sq - (3.0 / r)

    # e^2 = 1 + 2 * eps * h^2 / mu^2
    e_sq = 1.0 + (2.0 * eps * h_sq) / 9.0
    return np.sqrt(np.maximum(e_sq, 0.0))


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

    inc_list = []
    r_corot_rH = R_COROT_RM / RH_OVER_RM  # 共回転半径 [Hill半径]

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

            # 4096ステップ単位で Jacobi エネルギーを評価
            hit_step = None
            for start in range(0, n_records, 4096):
                chunk = m[start : min(start + 4096, n_records)]

                r_a = compute_semi_major_axis_rM(
                    chunk["x"],
                    chunk["y"],
                    chunk["z"],
                    chunk["vx"],
                    chunk["vy"],
                    chunk["vz"],
                )

                idx_cross = np.where((~np.isnan(r_a)) & (r_a <= R_COROT_RM))[0]
                if len(idx_cross) > 0:
                    hit_step = chunk[idx_cross[0]]
                    break

            if hit_step is None:
                continue

            # 到達時間の状態
            t = float(hit_step["t"])
            x = float(hit_step["x"])
            y = float(hit_step["y"])
            z = float(hit_step["z"])
            vx = float(hit_step["vx"])
            vy = float(hit_step["vy"])
            vz = float(hit_step["vz"])

            # 慣性系速度
            vx_in = vx - y
            vy_in = vy + x
            vz_in = vz

            # 角運動量ベクトル
            hx = y * vz_in - z * vy_in
            hy = z * vx_in - x * vz_in
            hz = x * vy_in - y * vx_in
            h_norm = np.sqrt(hx**2 + hy**2 + hz**2)
            if h_norm < 1e-12:
                continue

            # 火星自転軸ベクトル
            theta = -OMEGA_K * (t * SEC_PER_YEAR)
            sx = np.sin(PHI) * np.cos(theta)
            sy = np.sin(PHI) * np.sin(theta)
            sz = np.cos(PHI)

            # 赤道面に対する傾斜角
            cos_i = (hx * sx + hy * sy + hz * sz) / h_norm
            cos_i = np.clip(cos_i, -1.0, 1.0)
            i_eq = np.degrees(np.arccos(cos_i))

            inc_list.append(i_eq)

        except Exception:
            continue

    print(
        f"[v{ctx['v0']:03d}] Valid: {len(inc_list)} / {len(captured_ids)}",
        flush=True,
    )
    return {"v0": ctx["v0"], "inclinations": inc_list}


def aggregate_results(results: list, filter_info: dict, run_gnuplot):
    # 初速度ごとのリストを取り出し
    inc_dict = {
        r["v0"]: r["inclinations"] for r in results if r and "inclinations" in r
    }
    all_times = [t for times in inc_dict.values() for t in times]

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

    figures_dir = Path("stats/inclination_eq_rc")
    stats_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # ビン設定

    bins = np.arange(0.0, 180.0 + BIN_WIDTH_DEG, BIN_WIDTH_DEG)
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
        times = inc_dict.get(v, [])
        counts, _ = np.histogram(times, bins=bins)
        df_count[f"v{v:03d}_count"] = counts

        total_v = len(times)
        df_prob[f"v{v:03d}_prob"] = counts / total_v if total_v > 0 else 0.0

    raw_csv = stats_dir / f"inclination_eq_rc_raw_{tag}.csv"
    prob_csv = stats_dir / f"inclination_eq_rc_prob_{tag}.csv"
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
        png_path = figures_dir / f"inclination_eq_rc_{tag}_v{v:03d}.png"
        png_str = png_path.resolve().as_posix()

        script = f"""\
{load_config}set terminal pngcairo size 900, 550 font "MS Gothic,14"
set output "{png_str}"
set datafile separator ","
set title "共回転半径に達したときの軌道傾斜角: v0 = {v} m/s ({tag})" noenhanced
set xlabel "inclination [degree]"
set ylabel "Frequency"
set xrange [0:180]
set yrange [0:*]
set grid ytics lc rgb "#cccccc" dt 2
set style fill solid 0.7 border -1
set boxwidth {BIN_WIDTH_DEG}
plot "{csv_str}" using ($1 + {BIN_WIDTH_DEG / 2.0}):{col_idx} every ::1 with boxes lc rgb "#0066CC" notitle
"""
        run_gnuplot(script)
        print(f"[Saved PNG] {png_path}")
