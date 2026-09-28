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
set terminal pngcairo size 900,600 font 'Arial,10'
set output "{png_str}"

set xrange [0:50]
set yrange [0:35]

# config.gp の設定に左右されないよう、明示的にラジアン基準へ統一
set angles radians

set xlabel "Distance from Mars center r [r_M]"
set ylabel "Orbital Inclination i [deg]"
set title "{title_label}" noenhanced
set key outside right top

set arrow from 1.0, 0 to 1.0, 180 nohead lc rgb "#cc0000" dt 2 lw 1
set arrow from 0, 90 to 50, 90 nohead lc rgb "#888888" dt 2 lw 1

scale_rM = {RH_OVER_RM}
r_norm_rM(x, y, z) = sqrt(x*x + y*y + z*z) * scale_rM

hx(y, z, vy, vz) = y*vz - z*vy
hy(x, z, vx, vz) = z*vx - x*vz
hz(x, y, vx, vy) = x*vy - y*vx
h_norm(x, y, z, vx, vy, vz) = sqrt(hx(y,z,vy,vz)**2 + hy(x,z,vx,vz)**2 + hz(x,y,vx,vy)**2)

phi = 25.0 * pi / 180.0
SEC_PER_YEAR = 365.25 * 24.0 * 3600.0
omegaK = sqrt(G * MS / (MARS_SEMI_MAJOR_AXIS ** 3))
theta(t) = - omegaK * (t * SEC_PER_YEAR)

sx(t) = sin(phi) * cos(theta(t))
sy(t) = sin(phi) * sin(theta(t))
sz = cos(phi)

clamp(v) = (v > 1.0) ? 1.0 : ((v < -1.0) ? -1.0 : v)
cos_i(t, x, y, z, vx, vy, vz) = (h_norm(x,y,z,vx,vy,vz) > 1e-12) ? \
    clamp(dot(hx(y,z,vy,vz), hy(x,z,vx,vz), hz(x,y,vx,vy), sx(t), sy(t), sz) / h_norm(x,y,z,vx,vy,vz)) : 1/0
inc_deg(t, x, y, z, vx, vy, vz) = acos(cos_i(t, x, y, z, vx, vy, vz)) * 180.0 / pi

plot "{bin_str}" binary format="%7double" using (r_norm_rM($2,$3,$4)):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#0066CC" title "Points"
"""
