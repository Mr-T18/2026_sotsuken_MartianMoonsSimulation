from pathlib import Path
from typing import cast
import matplotlib.animation as animation
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3D
import numpy as np
import argparse

# 物理定数
M_SUN = 1.99e30  # 太陽質量 [kg]
M_MARS = 6.42e23  # 火星質量 [kg]
AU = 1.495978707e11  # 天文単位 [m]
rM = 3396.2e3  # 火星赤道半径 [m]
MARS_SEMI_MAJOR_AXIS = 1.52368 * AU
rH = MARS_SEMI_MAJOR_AXIS * (M_MARS / (3.0 * M_SUN)) ** (1.0 / 3.0)  # Hill半径 [m]
G = 6.67430e-11

SEC_PER_YEAR = 365.25 * 86400.0
OMEGA_K = float(np.sqrt(G * M_SUN / (MARS_SEMI_MAJOR_AXIS**3)))
PHI = float(np.radians(25.0))

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


def rH_to_rM(x):
    """Hill半径から火星半径への単位変換"""
    return (x * rH) / rM


def load_vectors_inertial(bin_path: Path, step_stride: int = 10):
    """バイナリを読み込み、慣性座標系での軌道法線単位ベクトルを算出"""
    m = np.memmap(bin_path, dtype=RECORD_DTYPE, mode="r")
    data = m[::step_stride]

    t = data["t"]
    x, y, z = data["x"], data["y"], data["z"]
    vx, vy, vz = data["vx"], data["vy"], data["vz"]

    r = rH_to_rM(np.sqrt(x**2 + y**2 + z**2))

    # 1. Hill基底での慣性速度（無次元系なので Ω_K = 1）
    vx_in = vx - y
    vy_in = vy + x
    vz_in = vz

    # 2. Hill基底での比角運動量ベクトル
    hx_rot = y * vz_in - z * vy_in
    hy_rot = z * vx_in - x * vz_in
    hz_rot = x * vy_in - y * vx_in
    h_norm = np.maximum(np.sqrt(hx_rot**2 + hy_rot**2 + hz_rot**2), 1e-12)

    nx_rot = hx_rot / h_norm
    ny_rot = hy_rot / h_norm
    nz_rot = hz_rot / h_norm

    # 3. 回転角 psi = +OMEGA_K * t_sec だけ回転して慣性座標系へ変換
    psi = OMEGA_K * (t * SEC_PER_YEAR)
    cos_psi = np.cos(psi)
    sin_psi = np.sin(psi)

    nx = nx_rot * cos_psi - ny_rot * sin_psi
    ny = nx_rot * sin_psi + ny_rot * cos_psi
    nz = nz_rot

    return t, nx, ny, nz, r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--Obl", type=int, default=25)
    parser.add_argument("--J2", type=str, default="Midium")
    parser.add_argument("--Gas", type=str, default="Large")
    args = parser.parse_args()

    bin_path = Path(
        f"result/ideal/Obl-{args.Obl:03d}_J2-{args.J2}_Gas-{args.Gas}/out/Obl-{args.Obl:03d}_J2-{args.J2}_Gas-{args.Gas}_ideal.bin"
    )

    if not bin_path.is_file():
        print(
            f"[Error] Obl-{args.Obl:03d}_J2-{args.J2}_Gas-{args.Gas} のファイルが存在しません"
        )
        return

    t, nx, ny, nz, r = load_vectors_inertial(bin_path, step_stride=10)
    n_frames = len(t)

    fig = plt.figure(figsize=(9, 8))
    ax = cast(Axes3D, fig.add_subplot(111, projection="3d"))
    plt.subplots_adjust(bottom=0.2)

    # 単位球面ワイヤーフレーム
    u = np.linspace(0, np.pi, 20)
    v = np.linspace(0, 2 * np.pi, 40)
    xs = np.outer(np.sin(u), np.cos(v))
    ys = np.outer(np.sin(u), np.sin(v))
    zs = np.outer(np.cos(u), np.ones_like(v))
    ax.plot_wireframe(xs, ys, zs, color="#e0e0e0", linewidth=0.5)

    # 慣性系における固定の火星自転軸ベクトル
    sx_fix = float(np.sin(PHI))
    sy_fix = 0.0
    sz_fix = float(np.cos(PHI))
    ax.quiver(
        0.0,
        0.0,
        0.0,
        sx_fix,
        sy_fix,
        sz_fix,
        color="#cc0000",
        lw=2.5,
        length=1,
        normalize=True,
        label="Mars Spin Axis (Fixed)",
    )

    # 参考基準として火星赤道面の大円を描画
    alpha = np.linspace(0, 2 * np.pi, 100)
    ax.plot(
        np.cos(PHI) * np.cos(alpha),
        np.sin(alpha),
        -np.sin(PHI) * np.cos(alpha),
        color="#ff9999",
        linestyle="--",
        linewidth=1.0,
        label="Mars Equatorial Plane",
    )

    # 軌道法線ベクトルの軌跡と矢印
    line_traj = cast(Line3D, ax.plot([], [], [], color="#0066cc", lw=1.2, alpha=0.6)[0])
    quiver_orb = ax.quiver(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, color="#0044ff", lw=2.5)

    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.0, 1.0)
    ax.set_zlim(-1.0, 1.0)
    ax.set_box_aspect((1.0, 1.0, 1.0))
    ax.set_xlabel("X (Inertial)")
    ax.set_ylabel("Y (Inertial)")
    ax.set_zlabel("Z (Inertial)")
    ax.legend(loc="upper right")

    ax_slider = plt.axes((0.2, 0.08, 0.65, 0.03))
    slider = Slider(
        ax_slider, "Frame", 0, n_frames - 1, valinit=0, valstep=1, valfmt="%d"
    )

    ax_btn = plt.axes((0.05, 0.08, 0.1, 0.04))
    btn_play = Button(ax_btn, "Play")

    is_playing = [False]

    def update_frame(idx: float):
        nonlocal quiver_orb
        i = int(idx)

        line_traj.set_data_3d(nx[: i + 1], ny[: i + 1], nz[: i + 1])

        quiver_orb.remove()
        quiver_orb = ax.quiver(
            0.0,
            0.0,
            0.0,
            nx[i],
            ny[i],
            nz[i],
            color="#0044ff",
            lw=2.5,
            length=1,
            normalize=True,
        )

        ax.set_title(
            f"Time: {t[i]:.2f} yr (Frame: {i}/{n_frames - 1}), r = {r[i]:.2f} [r_M]"
        )
        fig.canvas.draw_idle()

    def on_slider_change(val: float):
        update_frame(val)

    slider.on_changed(on_slider_change)

    def toggle_play(event):
        is_playing[0] = not is_playing[0]
        btn_play.label.set_text("Pause" if is_playing[0] else "Play")

    btn_play.on_clicked(toggle_play)

    def advance(frame):
        if is_playing[0]:
            curr = int(slider.val)
            next_idx = (curr + 1) if curr + 1 < n_frames else 0
            slider.set_val(next_idx)
        return []

    _ = animation.FuncAnimation(
        fig, advance, interval=30, blit=False, cache_frame_data=False
    )

    update_frame(0)
    plt.show()


if __name__ == "__main__":
    main()
