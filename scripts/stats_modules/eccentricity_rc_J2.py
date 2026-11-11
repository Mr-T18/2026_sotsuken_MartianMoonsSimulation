from pathlib import Path
import numpy as np
import pandas as pd

# 定数設定
BIN_WIDTH_ECC = 0.02  # 離心率用ビン幅（0.0 〜 1.0 を 50 分割）
J2 = ["No", "Small", "Midium", "Large"]
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

RH_OVER_RM = 319.1632070652  # Hill半径 [火星半径]
R_COROT_RM = 6.015  # 共回転半径 [火星半径]

# 足切りフィルタ用（r_M換算で 15 r_M の2乗を Hill単位系に変換）
R_FILTER_RH_SQ = (15.0 / RH_OVER_RM) ** 2


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
    captured_ids = df[
        df["result"].astype(str).str.contains("-Capture") & (df["v0"] == 20.0)
    ]["ID"].tolist()

    ecc_list = []
    j2_val = ctx.get("j2", "Unknown")

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

            hit_step = None
            CHUNK_SIZE = 65536
            for start in range(0, n_records, CHUNK_SIZE):
                chunk = m[start : min(start + CHUNK_SIZE, n_records)]

                # 距離の2乗が 15 r_M より遠ければスキップ
                r_sq = chunk["x"] ** 2 + chunk["y"] ** 2 + chunk["z"] ** 2
                if np.min(r_sq) > R_FILTER_RH_SQ:
                    continue

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

            # 到達時点の位置と速度
            x = float(hit_step["x"])
            y = float(hit_step["y"])
            z = float(hit_step["z"])
            vx = float(hit_step["vx"])
            vy = float(hit_step["vy"])
            vz = float(hit_step["vz"])

            ecc = compute_eccentricity(x, y, z, vx, vy, vz)
            ecc_list.append(ecc)

        except Exception:
            continue

    print(
        f"[v{ctx['v0']:03d}] Valid: {len(ecc_list)} / {len(captured_ids)}",
        flush=True,
    )
    return {"j2": j2_val, "eccentricities": ecc_list}


def aggregate_results(results: list, filter_info: dict, run_gnuplot):
    ecc_dict = {}
    for r in results:
        if r and "j2" in r and "eccentricities" in r:
            ecc_dict.setdefault(r["j2"], []).extend(r["eccentricities"])
    all_eccs = [e for eccs in ecc_dict.values() for e in eccs]

    if not all_eccs:
        print("[Warning] 有効な捕獲データがありませんでした。")
        return

    obl = filter_info.get("obl")
    j2 = filter_info.get("j2")
    gas = filter_info.get("gas")
    v0 = filter_info.get("v0")
    tag = f"Obl-{obl:03d}_Gas-{gas}_v0-{v0}"

    stats_dir = Path("stats")
    figures_dir = Path("stats/eccentricity_rc_J2")
    stats_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # 離心率用ビン（0.0 から 1.0 まで）
    bins = np.arange(0.0, 1.0 + BIN_WIDTH_ECC, BIN_WIDTH_ECC)
    bin_starts = bins[:-1]
    bin_ends = bins[1:]
    bin_labels = [f"{s:.2f}-{e:.2f}" for s, e in zip(bin_starts, bin_ends)]

    df_count = pd.DataFrame(
        {
            "bin_start": bin_starts,
            "bin_end": bin_ends,
            "bin_label": bin_labels,
        }
    )
    df_prob = df_count.copy()

    for j2_name in J2:
        eccs = ecc_dict.get(j2_name, [])
        counts, _ = np.histogram(eccs, bins=bins)
        df_count[f"J2-{j2_name}_count"] = counts

        total_v = len(eccs)
        df_prob[f"J2-{j2_name}_prob"] = counts / total_v if total_v > 0 else 0.0

    raw_csv = stats_dir / f"eccentricity_rc_J2_raw_{tag}.csv"
    prob_csv = stats_dir / f"eccentricity_rc_J2_prob_{tag}.csv"
    df_count.to_csv(raw_csv, index=False)
    df_prob.to_csv(prob_csv, index=False)
    print(f"[Saved CSV] {raw_csv}")
    print(f"[Saved CSV] {prob_csv}")

    csv_str = prob_csv.resolve().as_posix()
    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()
    load_config = f'load "{config_path}"\n' if Path(config_path).exists() else ""

    for idx, j2_name in enumerate(J2):
        col_idx = 4 + idx
        png_path = figures_dir / f"eccentricity_rc_J2-{j2_name}_{tag}.png"
        png_str = png_path.resolve().as_posix()

        # 【修正3】xrange を [0:1]、boxwidth を BIN_WIDTH_ECC に変更
        script = f"""\
{load_config}set terminal pngcairo size 900, 550 font "MS Gothic,14"
set output "{png_str}"
set datafile separator ","
set title "共回転半径に達したときの離心率: J2 = {j2_name} ({tag})" noenhanced
set xlabel "Eccentricity e"
set ylabel "Probability"
set xrange [0:1]
set yrange [0:*]
set grid ytics lc rgb "#cccccc" dt 2
set style fill solid 0.7 border -1
set boxwidth {BIN_WIDTH_ECC}
plot "{csv_str}" using ($1 + {BIN_WIDTH_ECC / 2.0}):{col_idx} every ::1 with boxes lc rgb "#0066CC" notitle
"""
        run_gnuplot(script)
        print(f"[Saved PNG] {png_path}")
