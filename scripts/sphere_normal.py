from pathlib import Path
from typing import cast
import matplotlib.animation as animation
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3D
import numpy as np

# 定数だ
MS = 1.99e30  # 太陽質量[kg]
MM = 6.42e23  # 火星質量[kg]
AU = 1.495978707e11  # 天文単位[m]
rM = 3396.2e3  # 火星赤道半径 [m]
MARS_SEMI_MAJOR_AXIS = 1.52368 * AU  # 火星の軌道長半径[m]
rH = MARS_SEMI_MAJOR_AXIS * (MM / (3 * MS)) ** (1.0 / 3.0)  # Hill半径[m]


# Hill半径から火星半径の単位変換
def rH_to_rM(x):
    return (x * rH) / rM


SEC_PER_YEAR = 365.25 * 86400.0
OMEGA_K = 1.0590e-7
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


def load_vectors(bin_path: Path, step_stride: int = 5):
    m = np.memmap(bin_path, dtype=RECORD_DTYPE, mode="r")
    data = m[::step_stride]

    t = data["t"]
    x, y, z = data["x"], data["y"], data["z"]
    vx, vy, vz = data["vx"], data["vy"], data["vz"]

    r = rH_to_rM(np.sqrt(x**2 + y**2 + z**2))

    hx = y * vz - z * vy
    hy = z * vx - x * vz
    hz = x * vy - y * vx
    h_norm = np.sqrt(hx**2 + hy**2 + hz**2)
    h_norm = np.maximum(h_norm, 1e-12)
    nx, ny, nz = hx / h_norm, hy / h_norm, hz / h_norm

    theta = -OMEGA_K * (t * SEC_PER_YEAR)
    sx = np.sin(PHI) * np.cos(theta)
    sy = np.sin(PHI) * np.sin(theta)
    sz = np.full_like(t, np.cos(PHI))

    return t, nx, ny, nz, sx, sy, sz, r


def main():
    bin_path = Path(
        "result/ideal/Obl-025_J2-Small_Gas-Large/out/Obl-025_J2-Small_Gas-Large_ideal.bin"
    )
    t, nx, ny, nz, sx, sy, sz, r = load_vectors(bin_path, step_stride=10)
    n_frames = len(t)

    fig = plt.figure(figsize=(9, 8))
    ax = cast(Axes3D, fig.add_subplot(111, projection="3d"))
    plt.subplots_adjust(bottom=0.2)

    u = np.linspace(0, np.pi, 20)
    v = np.linspace(0, 2 * np.pi, 40)
    xs = np.outer(np.sin(u), np.cos(v))
    ys = np.outer(np.sin(u), np.sin(v))
    zs = np.outer(np.cos(u), np.ones_like(v))
    ax.plot_wireframe(xs, ys, zs, color="#e0e0e0", linewidth=0.5)

    v_circle = np.linspace(0, 2 * np.pi, 100)
    ax.plot(
        np.sin(PHI) * np.cos(v_circle),
        np.sin(PHI) * np.sin(v_circle),
        np.full_like(v_circle, np.cos(PHI)),
        color="#ff9999",
        linestyle="--",
        label="Spin Circle (25 deg)",
    )

    line_traj = cast(Line3D, ax.plot([], [], [], color="#0066cc", lw=1.2, alpha=0.6)[0])
    quiver_orb = ax.quiver(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, color="blue", lw=2.5)
    quiver_spin = ax.quiver(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, color="red", lw=2.5)

    ax.set_xlim(-1.0, 1.0)
    ax.set_ylim(-1.0, 1.0)
    ax.set_zlim(-1.0, 1.0)
    ax.set_box_aspect((1.0, 1.0, 1.0))
    ax.set_xlabel("X (Hill)")
    ax.set_ylabel("Y (Hill)")
    ax.set_zlabel("Z (Hill)")

    ax_slider = plt.axes((0.2, 0.08, 0.65, 0.03))
    slider = Slider(
        ax_slider, "Frame", 0, n_frames - 1, valinit=0, valstep=1, valfmt="%d"
    )

    ax_btn = plt.axes((0.05, 0.08, 0.1, 0.04))
    btn_play = Button(ax_btn, "Play")

    is_playing = [False]

    def update_frame(idx: float):
        nonlocal quiver_orb, quiver_spin
        i = int(idx)

        line_traj.set_data(nx[: i + 1], ny[: i + 1])
        line_traj.set_3d_properties(nz[: i + 1])

        quiver_orb.remove()
        quiver_spin.remove()
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
        quiver_spin = ax.quiver(
            0.0,
            0.0,
            0.0,
            sx[i],
            sy[i],
            sz[i],
            color="#cc0000",
            lw=2.5,
            length=1,
            normalize=True,
        )

        ax.set_title(
            f"Time: {t[i]:.2f} yr (Frame: {i}/{n_frames - 1}), r = {r[i]} [r_H]"
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
