from pathlib import Path


def get_gnuplot_script(bin_path: Path, png_path: Path) -> str:
    bin_str = bin_path.as_posix()
    png_str = png_path.as_posix()
    title_label = f"Jacobi Energy {bin_path.parent.name}/{bin_path.stem}"

    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()

    return f"""\
# 火星の無次元化半径 (constants.hpp の r_M_norm と同一: 約 0.003133)
r_M_norm = 3396.2e3 / 1.0839e9

# Hill有効ポテンシャル
Ueff(x, y, z) = -1.5*(x**2) + 0.5 * (z**2) - 3.0 / r_O(x, y, z) + 4.5
# Jacobi エネルギー
Jacobi(x, y, z, vx, vy, vz) = 0.5 * v2(vx, vy, vz) + Ueff(x, y, z)

# 外れ値をフィルターする
filter_Jacobi(x, y, z, vx, vy, vz) = \
    (abs(Jacobi(x, y, z, vx, vy, vz)) > 1e4) \
    ? 1/0 : Jacobi(x, y, z, vx, vy, vz)

load "{config_path}"
set output "{png_str}"
set title "{title_label}" noenhanced
set xlabel "t [yr]"
set ylabel "Jacobi E [J / kg]"
set xrange [0:*]
set yrange [*:*]

plot "{bin_str}" binary format="%7double" u ($1):(filter_Jacobi($2, $3, $4, $5, $6, $7)) w p pt 7 ps 0.35 notitle
"""
