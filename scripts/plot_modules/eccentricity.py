from pathlib import Path


def get_gnuplot_script(bin_path: Path, png_path: Path) -> str:
    bin_str = bin_path.as_posix()
    png_str = png_path.as_posix()
    title_label = f"{bin_path.parent.name}/{bin_path.stem}"

    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()

    return f"""\
load "{config_path}"
set terminal pngcairo size 800,600 enhanced font 'MS Gothic,18'
set output "{png_str}"
set title " " noenhanced
set xlabel "時間 [yr]"
set ylabel "離心率"
set xrange [0:*]
set yrange [-0.2:0.2]

# 軌道離心率を求める
mu = 3.0
ex(x,y,z,vx,vy,vz) = ((v2(vx,vy,vz) - mu / r_O(x,y,z))*x - dot(x,y,z,vx,vy,vz)*vx) / mu
ey(x,y,z,vx,vy,vz) = ((v2(vx,vy,vz) - mu / r_O(x,y,z))*y - dot(x,y,z,vx,vy,vz)*vy) / mu
ez(x,y,z,vx,vy,vz) = ((v2(vx,vy,vz) - mu / r_O(x,y,z))*z - dot(x,y,z,vx,vy,vz)*vz) / mu
eccentricity(x,y,z,vx,vy,vz) = sqrt(ex(x,y,z,vx,vy,vz)**2 + ey(x,y,z,vx,vy,vz)**2 + ez(x,y,z,vx,vy,vz)**2)

# 慣性系速度への変換
vx_in(x, y, vx) = vx - y
vy_in(x, y, vy) = vy + x


plot "{bin_str}" binary format="%7double" u ($1 < 1.0 ? $1 : 1/0):(eccentricity($2,$3,$4,vx_in($2, $3, $5),vy_in($2, $3, $6),$7)) w l lc rgb "#9400D3" lw 1.2 notitle
"""
