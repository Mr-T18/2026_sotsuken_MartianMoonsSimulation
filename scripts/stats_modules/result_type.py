from pathlib import Path
import pandas as pd


def run_analysis(ctx: dict) -> dict:
    csv_path = Path(ctx["csv_path"])

    # 空ファイル（0バイト）のチェック
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        print(f"Warning: Empty or missing file: {csv_path}")
        return None

    try:
        # comment='#' でヘッダーコメントを除外して読み込み
        df = pd.read_csv(csv_path, comment="#", header=None)
    except pd.errors.EmptyDataError:
        print(f"Warning: No data rows in file: {csv_path}")
        return None

    # 列数が足りない場合のチェック（正常なら7列）
    if df.empty or df.shape[1] < 7:
        print(f"Warning: Invalid format in file: {csv_path}")
        return None

    df.columns = ["ID", "v0", "phi0", "zeta0", "N", "year", "result"]
    total = len(df)

    # result列を分解 (Direct-Escape-L2 など)
    split_res = df["result"].astype(str).str.split("-", expand=True)
    df["origin"] = split_res[0]
    df["outcome"] = split_res[1]

    counts = df.groupby(["origin", "outcome"]).size().to_dict()

    dir_esc = counts.get(("Direct", "Escape"), 0)
    dir_col = counts.get(("Direct", "Collision"), 0)
    dir_cap = counts.get(("Direct", "Capture"), 0)

    tmp_esc = counts.get(("Temporary", "Escape"), 0)
    tmp_col = counts.get(("Temporary", "Collision"), 0)
    tmp_cap = counts.get(("Temporary", "Capture"), 0)

    tot_esc = dir_esc + tmp_esc
    tot_col = dir_col + tmp_col
    tot_cap = dir_cap + tmp_cap
    tot_dir = dir_esc + dir_col + dir_cap
    tot_tmp = tmp_esc + tmp_col + tmp_cap

    return {
        "obl": ctx["obl"],
        "j2": ctx["j2"],
        "gas": ctx["gas"],
        "v0": ctx["v0"],
        "total_runs": total,
        "escape_total": tot_esc,
        "collision_total": tot_col,
        "capture_total": tot_cap,
        "escape_rate": tot_esc / total if total > 0 else 0.0,
        "collision_rate": tot_col / total if total > 0 else 0.0,
        "capture_rate": tot_cap / total if total > 0 else 0.0,
        "direct_total": tot_dir,
        "temporary_total": tot_tmp,
        "direct_rate": tot_dir / total if total > 0 else 0.0,
        "temporary_rate": tot_tmp / total if total > 0 else 0.0,
        "direct_escape": dir_esc,
        "direct_collision": dir_col,
        "direct_capture": dir_cap,
        "temp_escape": tmp_esc,
        "temp_collision": tmp_col,
        "temp_capture": tmp_cap,
    }
