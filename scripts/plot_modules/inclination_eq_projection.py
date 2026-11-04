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
set yrange [-180:180]

# config.gp の設定に左右されないよう、明示的にラジアン基準へ統一
set angles radians

set xlabel "Time t [yr]"
set ylabel "Phase Lag [deg]"
set title "{title_label}" noenhanced


scale_rM = {RH_OVER_RM}
r_norm_rM(x, y, z) = sqrt(x*x + y*y + z*z) * scale_rM

# 角運動量ベクトル
hx(y, z, vy, vz) = y*vz - z*vy
hy(x, z, vx, vz) = z*vx - x*vz
hz(x, y, vx, vy) = x*vy - y*vx
h_norm(x, y, z, vx, vy, vz) = sqrt(hx(y,z,vy,vz)**2 + hy(x,z,vx,vz)**2 + hz(x,y,vx,vy)**2)

phi = 25.0 * pi / 180.0
# Hill座標系における火星の自転軸傾斜角
theta(t) = - omegaK * (t * SEC_PER_YEAR) 

sx(t) = sin(phi) * cos(theta(t))
sy(t) = sin(phi) * sin(theta(t))
sz = cos(phi)

# 軌道法線ベクトルのxy平面方位角 (-pi ~ pi)
phi_orb(y, z, x_pos, vx, vy, vz) = atan2(hy(x_pos, z, vx, vz), hx(y, z, vy, vz))

# 自転軸方位角に対する軌道法線方位角の位相差 (-180度 ~ 180度)
d_phi(t, x, y, z, vx, vy, vz) = RAD_TO_DEG(atan2(sin(phi_orb(y, z, x, vx, vy, vz) - theta(t)), cos(phi_orb(y, z, x, vx, vy, vz) - theta(t))))

clamp(v) = (v > 1.0) ? 1.0 : ((v < -1.0) ? -1.0 : v)
cos_i(t, x, y, z, vx, vy, vz) = (h_norm(x,y,z,vx,vy,vz) > 1e-12) ? \
    clamp(dot(hx(y,z,vy,vz), hy(x,z,vx,vz), hz(x,y,vx,vy), sx(t), sy(t), sz) / h_norm(x,y,z,vx,vy,vz)) : 1/0
inc_deg(t, x, y, z, vx, vy, vz) = acos(cos_i(t, x, y, z, vx, vy, vz)) * 180.0 / pi

wrap360(x) = x - 360.0 * floor(x / 360.0)

# 完全同期（位相差0度）の基準線
set arrow from graph 0, first 0 to graph 1, first 0 nohead lc rgb "#888888" dt 2 lw 1

plot "{bin_str}" binary format="%7double" u 1:(d_phi($1,$2,$3,$4,$5,$6,$7)) \
     w l lc rgb "#0066CC" lw 1.5 title "Phase Lag (Orbital Normal - Spin Axis)"
"""
