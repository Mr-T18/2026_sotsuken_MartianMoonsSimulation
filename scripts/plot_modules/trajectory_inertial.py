from pathlib import Path


def get_gnuplot_script(bin_path: Path, png_path: Path) -> str:
    bin_str = bin_path.as_posix()
    png_str = png_path.as_posix()
    title_label = f"{bin_path.parent.name}/{bin_path.stem}"

    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()

    return f"""\
load "{config_path}"
set output "{png_str}"
set title "{title_label} trajectory(inertial)" noenhanced
set xlabel "x [r_H]"
set ylabel "y [r_H]"
set xrange [-1.5:1.5]
set yrange [-1.0:1.0]
set size ratio -1

set angles radians

# z軸周りにthetaだけ回転させたx,yそれぞれの座標を返す
rotateX(x, y, theta) = x * cos(theta) - y * sin(theta)
rotateY(x, y, theta) = x * sin(theta) + y * cos(theta)

# 太陽中心慣性座標系における火星の円公転上の角度
# = 慣性座標系に対するHill座標系の傾きと等しい
Martian_theta(t_yr) = omegaK * t_yr * SEC_PER_YEAR

plot "{bin_str}" binary format="%7double" \
    u ($1 <= 2.0 ? rotateX($2, $3, Martian_theta($1)) : 1/0):\
      ($1 <= 2.0 ? rotateY($2, $3, Martian_theta($1)) : 1/0) \
    w l lc rgb "#9400D3" lw 1.2 notitle
"""
