load "config.gp"

# z方向
set output "../plot/orbit_lf_z.png"
set title "Hill座標系のシミュレーション z方向"
set xlabel "t"
set ylabel "z [r_H]"
set xrange [0:1.0]
set yrange [*:*]
plot "../result_lf.dat" u 1:4 w l t "z",\
"../result_lf.dat" u 1:2 w l t "x"