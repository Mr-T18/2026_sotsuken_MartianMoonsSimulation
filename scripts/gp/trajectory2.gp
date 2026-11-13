load "config.gp"

t_min = 316
t_max = 321

# 太陽中心慣性座標での火星と衛星の位置
set output "../figures/orbit.png"
set title "Hill座標系のシミュレーション"
set xlabel "x [r_H]"
set ylabel "y [r_H]"
set xrange [-2.0:2.0]
set yrange [-2.0:2.0]
plot "../out/result.dat" u ($1 >=  t_min && $1 <= t_max ? $2 : 1/0):3 w l t "衛星軌道"