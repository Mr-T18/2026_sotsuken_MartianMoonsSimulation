load "config.gp"

set output "../plot/inclination.png"
set title "衛星-火星間距離と接触軌道傾斜角の関係"
set xlabel "distance from Mars [r_H]"
set ylabel "inclination [deg]"
set logscale x
set xrange [10:400]
set yrange [0:180]

plot "../result.dat" u (rH_to_rM(r_O($2, $3, $4))):(atan2($7, v($5, $6))) w p t "inclination"