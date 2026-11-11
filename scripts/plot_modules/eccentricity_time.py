# 離心率を計算

from pathlib import Path

# constants.hpp に基づく換算定数 (r_H / r_M)
RH_OVER_RM = 319.1632070652


def get_gnuplot_script(bin_path: Path, png_path: Path) -> str:
    bin_str = bin_path.as_posix()
    png_str = png_path.as_posix()
    title_label = f"{bin_path.parent.name}/{bin_path.stem}"

    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()

    return f"""\
load "{config_path}"
set terminal pngcairo size 900,600
set output "{png_str}"

set xrange [0:*]
set yrange [0:*]

# config.gp の設定に左右されないよう、明示的にラジアン基準へ統一
set angles radians

set xlabel "時間 t [yr]"
set ylabel "軌道離心率 e"

set arrow from 0, 0.0151 to 50, 0.0151 nohead lc rgb "#0000cc" dt 2 lw 3

scale_rM = {RH_OVER_RM}
r_norm_rM(x, y, z) = sqrt(x*x + y*y + z*z) * scale_rM

# 慣性系速度
vx_in(x, y, vx) = vx - y
vy_in(x, y, vy) = vy + x

# Hill座標系角運動量
hx(y, z, vy, vz) = y*vz - z*vy
hy(x, z, vx, vz) = z*vx - x*vz
hz(x, y, vx, vy) = x*vy - y*vx
h_norm(x, y, z, vx, vy, vz) = sqrt(hx(y,z,vy,vz)**2 + hy(x,z,vx,vz)**2 + hz(x,y,vx,vy)**2)

# 慣性系角運動量
hx_in(x, y, z, vx, vy, vz) = y*vz - z*vy_in(x, y, vy)
hy_in(x, y, z, vx, vy, vz) = z*vx_in(x, y, vx) - x*vz
hz_in(x, y, z, vx, vy, vz) = x*vy_in(x, y, vy) - y*vx_in(x, y, vx)
h_norm_in(x, y, z, vx, vy, vz) = sqrt(hx_in(x, y, z, vx, vy, vz)**2 + hy_in(x, y, z, vx, vy, vz)**2 + hz_in(x, y, z, vx, vy, vz)**2)
h_in_sq(x, y, z, vx, vy, vz) = hx_in(x, y, z, vx, vy, vz)**2 + hy_in(x, y, z, vx, vy, vz)**2 + hz_in(x, y, z, vx, vy, vz)**2

# 慣性系速度の2乗
v_in_sq(x, y, vx, vy, vz) = vx_in(x, y, vx)**2 + vy_in(x, y, vy)**2 + vz**2

# 軌道長半径の逆数 1/a
inv_a(x, y, z, vx, vy, vz) = (2.0 / r_O(x, y, z)) - (v_in_sq(x, y, vx, vy, vz) / 3.0)

clamp(v) = (v > 1.0) ? 1.0 : ((v < -1.0) ? -1.0 : v)
eccentricity(x, y, z, vx, vy, vz) = sqrt(clamp(1.0 - (h_in_sq(x, y, z, vx, vy, vz) * inv_a(x, y, z, vx, vy, vz) / 3.0)))

plot "{bin_str}" binary format="%7double" using ($1):(eccentricity($2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#0066CC" notitle
"""
