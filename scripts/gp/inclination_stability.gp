load "scripts/config.gp"
set terminal pngcairo size 800, 800 font "MS Gothic,14"
set output "stats/inclination_stability/figures/inclination_stability_J2-Small_Obl-025_Gas-Large_v0-20.png"
set datafile separator ","

csv_file = "stats/inclination_stability/data/inclination_stability_J2-Small_Obl-025_Gas-Large_v0-20.csv"

# 2列目(x)と3列目(y)の統計量・線形回帰パラメータを算出（ヘッダー行をスキップ）
stats csv_file using 2:3 every ::1 name "ST" nooutput

a = ST_slope
b = ST_intercept
r = ST_correlation

# コンソールに値を出力
print sprintf("a = %.4f, b = %.4f, r = %.4f", a, b, r)

set title "40 r_M 公転傾斜角 vs r_C 赤道面傾斜角: J2 = Small" noenhanced
set xlabel "Inclination of Orbital Plane at 40 r_M [degree]"
set ylabel "Inclination of Equatorial Plane at r_c [degree]"
set xrange [0:60]
set yrange [0:60]
set size square
set grid ytics lc rgb "#cccccc" dt 2

# グラフ左上に回帰式と相関係数を表示（%+.3f で切片の符号を自動調整）
set label 1 sprintf("y = %.3fx %+.3f\nr = %.3f", a, b, r) at graph 0.05, 0.92 font "MS Gothic,14"

f(x) = a * x + b

plot csv_file using 2:3 every ::1 with points pt 7 ps 0.7 lc rgb "#0066CC" title "Data", \
     f(x) with lines lw 2 lc rgb "#CC0000" title "線形回帰"