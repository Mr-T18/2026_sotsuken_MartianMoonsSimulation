from pathlib import Path


def get_gnuplot_script(bin_path: Path, png_path: Path) -> str:
    bin_str = bin_path.as_posix()
    png_str = png_path.as_posix()
    title_label = f"inclination {bin_path.parent.name}/{bin_path.stem}"

    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()

    return f"""\
load "{config_path}"
set output "{png_str}"
set title "{title_label}"
set xlabel "distance from Mars [r_H]"
set ylabel "inclination [deg]"
set logscale x
set xrange [10:400]
set yrange [0:180]

hx(y, z, vy, vz) = y * vz - vy * z
hy(z, x, vz, vx) = z * vx - vz * x
hz(x, y, vx, vy) = x * vy - vx * y
h_norm(x, y, z, vx, vy, vz) = sqrt(hx(y, z, vy, vz)**2 + hy(z, x, vz, vx)**2 + hz(x, y, vx, vz)**2)

clamp(v) = (v > 1.0) ? 1.0 : ((v < -1.0) ? -1.0 : v)
cos_i(x, y, z, vx, vy, vz) = (h_norm(x,y,z,vx,vy,vz) > 1e-12) ? clamp(hz(x,y,vx,vy) / h_norm(x,y,z,vx,vy,vz)) : 1/0
inc_deg(x, y, z, vx, vy, vz) = acos(cos_i(x,y,z,vx,vy,vz))

plot "{bin_str}" binary format="%7double" u (rH_to_rM(r_O($2, $3, $4))):(inc_deg($2, $3, $4, $5, $6, $7)) w p pt 7 ps 0.35
"""
