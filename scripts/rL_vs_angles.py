from pathlib import Path
import shutil
import subprocess
import numpy as np

# --- 設定 ---
OBL_DEG = 25.0  # 火星自転軸傾斜角 [deg]
SPIN_PHI_DEG = 0.0  # 慣性系における火星自転軸の経度 [deg]（初期t=0で+x方向なら0.0）

J2_CASES = [
    (
        "Large",
        0.01955,
        "result/ideal/Obl-025_J2-Large_Gas-Large/out/Obl-025_J2-Large_Gas-Large_ideal.bin",
        "#80cc0000",
    ),
    (
        "Medium",
        0.001955,
        "result/ideal/Obl-025_J2-Medium_Gas-Large/out/Obl-025_J2-Medium_Gas-Large_ideal.bin",
        "#8000aa00",
    ),
    (
        "Small",
        0.0001955,
        "result/ideal/Obl-025_J2-Small_Gas-Large/out/Obl-025_J2-Small_Gas-Large_ideal.bin",
        "#800000cc",
    ),
]

# config.gp と同一の物理定数
G = 6.67430e-11
MS = 1.99e30  # 太陽質量 [kg]
MM = 6.42e23  # 火星質量 [kg]
Ms = 1.06e16  # 衛星質量 [kg]
AU = 1.495978707e11  # 天文単位 [m]
rM = 3396.2e3  # 火星赤道半径 [m]
MARS_SEMI_MAJOR_AXIS = 1.52368 * AU  # 火星の軌道長半径 [m]
rH = MARS_SEMI_MAJOR_AXIS * (MM / (3.0 * MS)) ** (1.0 / 3.0)  # Hill半径 [m]

SEC_PER_YEAR = 365.25 * 24.0 * 3600.0
omegaK = np.sqrt(G * MS / (MARS_SEMI_MAJOR_AXIS**3))

OUT_DIR = Path("stats/rL_vs_angles")
OUT_DIR.mkdir(parents=True, exist_ok=True)

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


def m_to_rM(x: float) -> float:
    return x / rM


def calc_rL(j2_val: float) -> float:
    # config.gp: r_L(J2) = m_to_rM((J2 * (rM**2) * (MARS_SEMI_MAJOR_AXIS**3) * MM / MS)**(1.0/5.0))
    return m_to_rM(
        (j2_val * (rM**2) * (MARS_SEMI_MAJOR_AXIS**3) * MM / MS) ** (1.0 / 5.0)
    )


def compute_series(bin_path: Path, j2_val: float) -> np.ndarray:
    n_records = bin_path.stat().st_size // 56
    m = np.memmap(bin_path, dtype=RECORD_DTYPE, mode="r", shape=(n_records,))

    t = m["t"]
    x, y, z = m["x"], m["y"], m["z"]
    vx, vy, vz = m["vx"], m["vy"], m["vz"]

    # ラプラス半径で規格化した距離 r [r_L]
    r_rM = np.sqrt(x**2 + y**2 + z**2) * (rH / rM)
    r_norm = r_rM / calc_rL(j2_val)

    # 回転座標系における慣性角運動量ベクトル h = r × v_in
    vxi = vx - y
    vyi = vy + x
    hx = y * vz - z * vyi
    hy = z * vxi - x * vz
    hz = x * vyi - y * vxi
    h_norm = np.sqrt(hx**2 + hy**2 + hz**2)

    # 慣性空間固定基準軸への回転 (+omegaK * t_sec)
    psi = omegaK * (t * SEC_PER_YEAR)
    hx_in = hx * np.cos(psi) - hy * np.sin(psi)
    hy_in = hx * np.sin(psi) + hy * np.cos(psi)
    hz_in = hz

    valid = h_norm > 1e-12
    safe_h = np.where(valid, h_norm, 1.0)
    theta_rad = np.where(valid, np.arcsin(np.clip(hz_in / safe_h, -1.0, 1.0)), np.nan)
    theta_deg = np.degrees(theta_rad)
    phi_rad = np.where(valid, np.arctan2(hy_in, hx_in), np.nan)
    phi_deg = np.degrees(phi_rad)
    costheta_phi = np.cos(theta_rad) * phi_deg

    # 列: [0: r/rL, 1: theta_deg, 2: phi_deg, 3: costheta_phi]
    return np.column_stack([r_norm, theta_deg, phi_deg, costheta_phi]).astype("<f8")


def plot_with_gnuplot(
    data: np.ndarray,
    col_idx: int,
    ylabel: str,
    yrange: str,
    target_val: float,
    target_label: str,
    out_png: Path,
    color: str,
):
    gnuplot_bin = shutil.which("gnuplot") or shutil.which("gnuplot.exe")
    if not gnuplot_bin:
        raise RuntimeError("gnuplot が見つかりません")

    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()
    load_config = f'load "{config_path}"\n' if Path(config_path).exists() else ""

    n_rows = data.shape[0]
    script = f"""\
{load_config}set terminal pngcairo size 900, 600 enhanced font "MS Gothic, 14"
set output "{out_png.resolve().as_posix()}"
set xrange [0:5]
set yrange {yrange}
set xlabel "ラプラス半径で規格化した距離 r [r_L]"
set ylabel "{ylabel}"
set grid ytics lc rgb "#dddddd" dt 2
set arrow 1 from 1.0, graph 0 to 1.0, graph 1 nohead lc rgb "#d97700" dt 2 lw 2.5
set arrow 2 from graph 0, first {target_val} to graph 1, first {target_val} nohead lc rgb "#333333" dt 3 lw 2.0
set label 1 "{target_label}" at graph 0.03, first {target_val} offset 0, 0.7 font "MS Gothic, 12" tc rgb "#333333"
plot "-" binary record={n_rows} format="%4double" using 1:{col_idx} with points pt 7 ps 0.35 lc rgb "{color}" notitle
"""
    try:
        proc = subprocess.Popen([gnuplot_bin], stdin=subprocess.PIPE)
        proc.stdin.write(script.encode("utf-8"))
        proc.stdin.write(data.tobytes())
        proc.stdin.close()
        proc.wait()
    except Exception as e:
        print(f"なんかうまくいかんかったね: {e}")


def main():
    # 火星自転軸の目標値
    target_theta = 90.0 - OBL_DEG
    target_phi = SPIN_PHI_DEG
    target_costheta_phi = float(np.cos(np.radians(target_theta)) * SPIN_PHI_DEG)

    for label, j2_val, bin_str, color in J2_CASES:
        bin_path = Path(bin_str)
        if not bin_path.exists():
            print(f"[Skip] Not found: {bin_path}")
            continue

        arr = compute_series(bin_path, j2_val)
        plot_with_gnuplot(
            arr,
            2,
            "軌道法線ベクトル緯度 {/Symbol q} [deg]",
            "[60:90]",
            target_theta,
            " ",
            OUT_DIR / f"rL_vs_theta_J2-{label}.png",
            color,
        )
        plot_with_gnuplot(
            arr,
            3,
            "軌道法線ベクトル経度 {/Symbol f} [deg]",
            "[-90:90]",
            target_phi,
            " ",
            OUT_DIR / f"rL_vs_phi_J2-{label}.png",
            color,
        )
        plot_with_gnuplot(
            arr,
            4,
            "cos({/Symbol q}){/Symbol f} [deg]",
            "[-30:30]",
            target_costheta_phi,
            " ",
            OUT_DIR / f"rL_vs_costheta-phi_J2-{label}.png",
            color,
        )
        print(f"[Done] J2-{label} ({arr.shape[0]} records)")


if __name__ == "__main__":
    main()
