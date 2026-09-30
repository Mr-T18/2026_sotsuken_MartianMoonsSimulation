from pathlib import Path


def get_gnuplot_script(bin_path: Path, png_path: Path) -> str:
    bin_str = bin_path.as_posix()
    png_str = png_path.as_posix()
    title_label = f"{bin_path.parent.name}/{bin_path.stem}"

    config_path = (Path.cwd() / "scripts/config.gp").resolve().as_posix()

    return f"""\
load "{config_path}"
set output "{png_str}"
set title "{title_label} trajectory" noenhanced
set xlabel "x [r_H]"
set ylabel "y [r_H]"
set xrange [-1.5:1.5]
set yrange [-1.0:1.0]
set size ratio -1

plot "{bin_str}" binary format="%7double" u ($2):($1 < 2.0 ? $3 : 1/0) w l lc rgb "#9400D3" lw 1.2 notitle
"""
