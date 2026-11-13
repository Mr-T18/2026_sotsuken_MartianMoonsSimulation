# ラプラス半径以遠（40 r_M）地点の公転面に対する自転軸傾斜角
# ラプラス半径以内（共回転半径；6.02 r_M）地点の赤道面に対する自転軸傾斜角
# この２つを比べ、その値に相関があるかどうかを散布図にプロットして調べる
# プロットはJ2を変化させて合計4枚

from pathlib import Path
import numpy as np
import pandas as pd
from state import State
from state import SEC_PER_YEAR, RH_OVER_RM, R_COROT_RM, R_M

# 定数設定
TIME_UNIT_FACTOR = 1.0
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

R_FILTER_RH_SQ = (60.0 / RH_OVER_RM) ** 2  # 足切り距離（90 r_M）


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
        df["result"].astype(str).str.contains("-Capture")
        & (df["v0"] == float(ctx["v0"]))
    ]["ID"].tolist()

    inc_list = []
    r_corot_rH = R_COROT_RM / RH_OVER_RM  # 共回転半径 [Hill半径]
    j2_val = ctx.get("j2", "Unknown")

    inc_comp_list = []
    rM40 = 40.0  # 40火星半径

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
            hit_step_rc = None
            hit_step_rM40 = None
            CHUNK_SIZE = 4096

            for start in range(0, n_records, CHUNK_SIZE):
                chunk = m[start : min(start + CHUNK_SIZE, n_records)]

                c_state = State(
                    chunk["t"],
                    chunk["x"],
                    chunk["y"],
                    chunk["z"],
                    chunk["vx"],
                    chunk["vy"],
                    chunk["vz"],
                )

                r_sq = c_state.x**2 + c_state.y**2 + c_state.z**2

                if np.min(r_sq) > R_FILTER_RH_SQ:
                    continue

                r_a = c_state.compute_semi_major_axis_rM()

                if hit_step_rM40 is None:
                    idx_cross_rM40 = np.where((~np.isnan(r_a)) & (r_a <= rM40))[0]
                    if len(idx_cross_rM40) > 0:
                        hit_step_rM40 = chunk[idx_cross_rM40[0]]
                if hit_step_rM40 is not None:
                    idx_cross_rc = np.where((~np.isnan(r_a)) & (r_a <= R_COROT_RM))[0]
                    if len(idx_cross_rc) > 0:
                        hit_step_rc = chunk[idx_cross_rc[0]]
                        break

            if hit_step_rc is None or hit_step_rM40 is None:
                continue

            # 到達時間の状態
            state_rc = State(
                float(hit_step_rc["t"]),
                float(hit_step_rc["x"]),
                float(hit_step_rc["y"]),
                float(hit_step_rc["z"]),
                float(hit_step_rc["vx"]),
                float(hit_step_rc["vy"]),
                float(hit_step_rc["vz"]),
            )

            state_rM40 = State(
                float(hit_step_rM40["t"]),
                float(hit_step_rM40["x"]),
                float(hit_step_rM40["y"]),
                float(hit_step_rM40["z"]),
                float(hit_step_rM40["vx"]),
                float(hit_step_rM40["vy"]),
                float(hit_step_rM40["vz"]),
            )

            i_eq = state_rc.compute_inclination_eq()
            i_orb = state_rM40.compute_inclination_orb()
            if i_eq is None or i_orb is None:
                continue

            inc_list.append(
                {
                    "ID": fid,
                    "inclination_eq_rc": float(i_eq),
                    "inclination_orb_rM40": float(i_orb),
                }
            )

        except Exception:
            continue

    print(
        f"[v{ctx['v0']:03d}] Valid: {len(inc_list)} / {len(captured_ids)}",
        flush=True,
    )
    return {"j2": j2_val, "inclinations": inc_list}


def aggregate_results(results: list, filter_info: dict, run_gnuplot):
    # J2ごとのリストを取り出し
    inc_dict = {}
    for r in results:
        if r and "j2" in r and "inclinations" in r:
            inc_dict.setdefault(r["j2"], []).extend(r["inclinations"])
    all_records = [rec for recs in inc_dict.values() for rec in recs]

    if not all_records:
        print("[Warning] 有効な捕獲データがありませんでした。")
        return

    # コマンド引数から識別子を作成
    obl = filter_info.get("obl")
    j2 = filter_info.get("j2")
    gas = filter_info.get("gas")
    v0 = filter_info.get("v0")
    tag = f"Obl-{obl:03d}_Gas-{gas}_v0-{v0}"

    # 出力先ディレクトリ
    stats_dir = Path("stats")

    figures_dir = Path("stats/inclination_stability/figures")
    data_dir = Path("stats/inclination_stability/data")
    stats_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()
    load_config = f'load "{config_path}"\n' if Path(config_path).exists() else ""

    # J2ごとにCSVと散布図pngを出力（計4セット）
    for j2_name in J2:
        records = inc_dict.get(j2_name, [])
        df_out = pd.DataFrame(
            records,
            columns=["ID", "inclination_orb_rM40", "inclination_eq_rc"],
        )

        raw_csv = data_dir / f"inclination_stability_J2-{j2_name}_{tag}.csv"
        df_out.to_csv(raw_csv, index=False)
        print(f"[Saved CSV] {raw_csv} ({len(df_out)} rows)")

        if df_out.empty:
            print(f"[Warning] J2 = {j2_name} のデータが空です")
            continue

        csv_str = raw_csv.resolve().as_posix()
        png_path = figures_dir / f"inclination_stability_J2-{j2_name}_{tag}.png"
        png_str = png_path.resolve().as_posix()

        script = f"""\
{load_config}set terminal pngcairo size 800, 800 font "MS Gothic,14"
set output "{png_str}"
set datafile separator ","
set title "40 r_M 公転傾斜角 vs r_C 赤道面傾斜角: J2 = {j2_name} ({tag})" noenhanced
set xlabel "Inclination of Orbital Plane at 40 r_M [degree]"
set ylabel "Inclination of Equatorial Plane at r_c [degree]"
set xrange [0:180]
set yrange [0:180]
set size square
set grid ytics lc rgb "#cccccc" dt 2
plot "{csv_str}" using 2:3 every ::1 with points pt 7 ps 0.7 lc rgb "#0066CC" notitle
"""
        run_gnuplot(script)
        print(f"[Saved PNG] {png_path}")
