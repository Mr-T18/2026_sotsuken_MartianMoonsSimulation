load "scripts/config.gp"
set terminal pngcairo size 900, 550 font "MS Gothic,14"
set output "stats/capture_fall_time/figures/capture_fall_time_Obl-025_J2-Medium_Gas-Large_v160.png"
set datafile separator ","
set title "Decay Time: v0 = 160 m/s" noenhanced
set xlabel "Decay Timescale [yr]"
set ylabel "Probability"
set xrange [0:*]
set yrange [0:*]
set grid ytics lc rgb "#cccccc" dt 2
set style fill solid 0.7 border -1
set boxwidth 100.0
plot "stats/capture_fall_time/data/capture_fall_time_prob_Obl-025_J2-Medium_Gas-Large.csv" using ($1 + 100.0 / 2.0):($11) every ::1 with boxes lc rgb "#0066CC" notitle