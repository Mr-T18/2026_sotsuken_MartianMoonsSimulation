load "scripts/config.gp"
set terminal pngcairo size 800, 800 font "MS Gothic,14"
set output "stats/inclination_stability/figures/inclination_stability_J2-No_Obl-025_Gas-Large_v0-20.png"
set datafile separator ","
set title "40 r_M 公転傾斜角 vs r_C 赤道面傾斜角: J2 = {j2_name}" noenhanced
set xlabel "Inclination of Orbital Plane at 40 r_M [degree]"
set ylabel "Inclination of Equatorial Plane at r_c [degree]"
set xrange [0:60]
set yrange [0:60]
set size square
set grid ytics lc rgb "#cccccc" dt 2
plot "stats/inclination_stability/data/inclination_stability_J2-No_Obl-025_Gas-Large_v0-20.csv" using 2:3 every ::1 with points pt 7 ps 0.7 lc rgb "#0066CC" notitle