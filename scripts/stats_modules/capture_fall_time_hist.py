import json
from pathlib import Path
import time
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# .bin 内の時間 t の単位設定
# t がすでに年 (year) 単位の場合は 1.0
# t が秒 (s) 単位の場合は 365.25 * 86400.0
SEC_TO_YEAR = 365.25 * 86400.0
TIME_UNIT_FACTOR = 1.0  # 必要に応じて SEC_TO_YEAR に変更

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

# ヒストグラムのビン幅（100年刻み）
BIN_WIDTH_YR = 100.0


def compute_jacobi_energy(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    vx: np.ndarray,
    vy: np.ndarray,
    vz: np.ndarray,
) -> np.ndarray:
    """Hill座標系におけるJacobiエネルギーを計算する"""
    r = np.sqrt(x**2 + y**2 + z**2)
    # ゼロ除算防止
    r = np.maximum(r, 1e-10)

    v_sq = vx**2 + vy**2 + vz**2
    u_eff = -1.5 * (x**2) + 0.5 * (z**2) - (3.0 / r) + 4.5
    return 0.5 * v_sq + u_eff


def get_bin_path(bin_dir: Path, v0: int, file_id: int) -> Path:
    sub_dir = f"{file_id // 1024:02d}"
    return bin_dir / sub_dir / f"v{v0:03d}_{file_id:04d}.bin"


def analyze_single_bin(bin_path: Path):
    """memmap を用いて Jacobi エネルギー J < 0 となる時刻・終了時刻・所要年数を特定する"""
    file_size = bin_path.stat().st_size
    if file_size < 56 * 2:
        return None

    n_records = file_size // 56

    try:
        m = np.memmap(bin_path, dtype=RECORD_DTYPE, mode="r", shape=(n_records,))

        t_end = float(m[-1]["t"]) / TIME_UNIT_FACTOR

        chunk_size = 4096
        t_cap = None

        for start in range(0, n_records, chunk_size):
            end = min(start + chunk_size, n_records)
            chunk = m[start:end]

            # Jacobi エネルギー J の計算
            j_energy = compute_jacobi_energy(
                chunk["x"],
                chunk["y"],
                chunk["z"],
                chunk["vx"],
                chunk["vy"],
                chunk["vz"],
            )

            # J < 0 となる最初のステップを探索（完全捕獲）
            neg_idx = np.where(j_energy < 0.0)[0]
            if len(neg_idx) > 0:
                t_cap = float(chunk["t"][neg_idx[0]]) / TIME_UNIT_FACTOR
                break

        if t_cap is not None:
            dt = t_end - t_cap
            if dt >= 0:
                return t_cap, t_end, dt

    except Exception:
        return None

    return None


def run_analysis(ctx: dict) -> dict:
    csv_path = Path(ctx["csv_path"])
    v0 = ctx["v0"]

    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return None

    try:
        df = pd.read_csv(csv_path, comment="#", header=None)
    except pd.errors.EmptyDataError:
        return None

    if df.empty or df.shape[1] < 7:
        return None

    df.columns = ["ID", "v0", "phi0", "zeta0", "N", "year", "result"]
    captured_df = df[df["result"].astype(str).str.contains("-Capture")]
    n_targets = len(captured_df)

    print(
        f"[v{v0:03d}] Start processing {n_targets} captured trajectories...",
        flush=True,
    )
    start_time = time.time()

    decay_times = []
    raw_records = []

    for _, row in captured_df.iterrows():
        fid = int(row["ID"])
        bin_path = get_bin_path(ctx["bin_dir"], v0, fid)

        if not bin_path.exists():
            continue

        res = analyze_single_bin(bin_path)
        if res is not None:
            t_cap, t_end, dt = res
            decay_times.append(dt)
            raw_records.append(
                {
                    "obl": ctx["obl"],
                    "j2": ctx["j2"],
                    "gas": ctx["gas"],
                    "v0": v0,
                    "id": fid,
                    "t_cap_yr": t_cap,
                    "t_end_yr": t_end,
                    "decay_yr": dt,
                }
            )

    elapsed = time.time() - start_time
    print(
        f"[v{v0:03d}] Finished: {len(decay_times)}/{n_targets} valid in {elapsed:.2f}s",
        flush=True,
    )

    return {
        "obl": ctx["obl"],
        "j2": ctx["j2"],
        "gas": ctx["gas"],
        "v0": v0,
        "captured_total": n_targets,
        "analyzed_valid": len(decay_times),
        "decay_mean_yr": np.mean(decay_times) if decay_times else np.nan,
        "decay_median_yr": np.median(decay_times) if decay_times else np.nan,
        "decay_min_yr": np.min(decay_times) if decay_times else np.nan,
        "decay_max_yr": np.max(decay_times) if decay_times else np.nan,
        "_raw_records_json": json.dumps(raw_records),
    }


def aggregate_results(df: pd.DataFrame) -> pd.DataFrame:
    all_raw = []
    for raw_str in df["_raw_records_json"]:
        if raw_str:
            all_raw.extend(json.loads(raw_str))

    df_clean = df.drop(columns=["_raw_records_json"])
    sort_cols = [c for c in ["obl", "j2", "gas", "v0"] if c in df_clean.columns]
    if sort_cols:
        df_clean = df_clean.sort_values(by=sort_cols).reset_index(drop=True)

    if not all_raw:
        return df_clean

    df_raw = pd.DataFrame(all_raw)

    stats_dir = Path("stats")
    stats_dir.mkdir(parents=True, exist_ok=True)

    # 1. 個別試行の生データCSV保存
    df_raw.to_csv(stats_dir / "capture_fall_raw.csv", index=False)

    # 2. 100年刻みのビン設定
    max_decay = df_raw["decay_yr"].max()
    max_bin_edge = np.ceil(max_decay / BIN_WIDTH_YR) * BIN_WIDTH_YR
    if max_bin_edge == 0:
        max_bin_edge = BIN_WIDTH_YR

    bins = np.arange(0, max_bin_edge + BIN_WIDTH_YR, BIN_WIDTH_YR)

    # 3. 度数分布表の作成・保存
    v0_list = sorted(df_raw["v0"].unique())
    hist_table = pd.DataFrame(
        {
            "bin_start_yr": bins[:-1],
            "bin_end_yr": bins[1:],
        }
    )

    for v in v0_list:
        sub_data = df_raw[df_raw["v0"] == v]["decay_yr"]
        counts, _ = np.histogram(sub_data, bins=bins)
        hist_table[f"v{v:03d}_count"] = counts

    total_counts, _ = np.histogram(df_raw["decay_yr"], bins=bins)
    hist_table["total_count"] = total_counts
    hist_table.to_csv(stats_dir / "capture_fall_hist_100yr.csv", index=False)

    # 4. ヒストグラム図の保存
    fig, ax = plt.subplots(figsize=(10, 6))

    data_by_v0 = [df_raw[df_raw["v0"] == v]["decay_yr"].values for v in v0_list]

    ax.hist(
        data_by_v0,
        bins=bins,
        stacked=True,
        label=[f"v0 = {v} km/s" for v in v0_list],
        edgecolor="black",
        linewidth=0.5,
    )

    ax.set_xlabel("Time from Capture to Collision [yr] (100-yr bins)")
    ax.set_ylabel("Count")
    ax.set_title(
        "Distribution of Orbital Decay Timescale after Capture (Jacobi Energy J < 0)"
    )
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.legend(title="Initial Velocity")

    fig.tight_layout()
    fig.savefig(stats_dir / "capture_fall_hist.png", dpi=300)
    plt.close(fig)

    return df_clean
