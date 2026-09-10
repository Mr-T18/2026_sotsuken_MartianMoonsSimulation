from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import numpy as np


def load_binary_data(filepath: Path):
    """シミュレーション結果のbinファイル．(t, x, y, z, vx, vy, vz)を読み込み，pd.DataFrameに格納"""
    data = np.fromfile(filepath, dtype=np.float64).reshape(-1, 7)
    cols = ["t", "x", "y", "z", "vx", "vy", "vz"]
    df = pd.DataFrame(data, columns=cols)
    return df


def load_data(filepath: Path):
    """7列のdatファイル．(t, x, y, z, vx, vy, vz)"""
    cols = ["t", "x", "y", "z", "vx", "vy", "vz"]
    df = pd.read_csv(filepath, sep=r"\s+", comment="#", names=cols)
    return df


def plot_orbit(
    df: pd.DataFrame,
    output_path: Path,
    t_start: float = 0,
    t_end: float = 5,
    title_suffix: str = "",
):
    # 指定された時間範囲でデータを抽出
    sub_df = df
    if t_start is not None:
        sub_df = sub_df[sub_df["t"] >= t_start]
    if t_end is not None:
        sub_df = sub_df[sub_df["t"] <= t_end]

    if sub_df.empty:
        print(
            f"Warning: 指定された期間({t_start} ~ {t_end} yr)にデータが存在しません．"
        )
        return

    fig, ax = plt.subplots(figsize=(6, 6))

    # 火星（中心）とHill球境界（r = 1.0）
    hill_circle = patches.Circle(
        (0, 0), 1.0, color="gray", fill=False, linestyle="--", lw=0.8, alpha=0.7
    )
    ax.add_patch(hill_circle)
    ax.plot(0, 0, marker="o", markersize=4, color="tab:red", label="Mars")

    # 軌道のプロット
    ax.plot(
        sub_df["x"],
        sub_df["y"],
        color="darkviolet",
        lw=0.6,
        alpha=0.8,
        label="Trajectory",
    )

    # 進入開始点
    ax.scatter(
        sub_df["x"].iloc[0],
        sub_df["y"].iloc[0],
        color="forestgreen",
        s=15,
        zorder=5,
        label="Start",
    )

    # 軸・表示設定
    ax.set_xlabel("$x$ [$r_H$]", fontsize=11)
    ax.set_ylabel("$y$ [$r_H$]", fontsize=11)
    ax.set_xlim(-2.1, 2.1)
    ax.set_ylim(-2.1, 2.1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(f"Trajectory {title_suffix}", fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", framealpha=0.85, fontsize=9)

    plt.tight_layout()

    # 保存先ディレクトリの作成
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    # print(f"Plot saved: {output_path}")


def main():
    out_dir = Path("out")
    figures_dir = Path("figures")

    # out配下のすべての.binファイルを再帰的に格納
    bin_files = sorted(out_dir.rglob("*.bin"))
    total_files = len(bin_files)
    print(f"Found {total_files} binary files in {out_dir}.")

    for i, bin_path in enumerate(bin_files, start=1):
        # outディレクトリからの相対パスを取得
        rel_path = bin_path.relative_to(out_dir)

        # figures側の出力先パスを決定
        png_path = (figures_dir / rel_path).with_suffix(".png")

        try:
            # 空ファイルチェック
            if bin_path.stat().st_size == 0:
                continue
            df = load_binary_data(bin_path)
            plot_orbit(
                df,
                output_path=png_path,
                title_suffix=f"{rel_path.parent}/{bin_path.stem}",
            )

        except Exception as e:
            print(f"Error processing {bin_path}: {e}")

        if i % 100 == 0 or i == total_files:
            print(f"[{i}/{total_files}] Processed -> {png_path}")

    print("All plots generated successfully.")


if __name__ == "__main__":
    main()
