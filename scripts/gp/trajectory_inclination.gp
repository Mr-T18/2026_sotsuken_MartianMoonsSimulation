load "config.gp"
set terminal qt
set angle degrees
set mouse

# set output "../plot/inclination.png"
set title "trajectory - inclination"
set xlabel "x [r_H]"
set ylabel "y [r_H]"
set zlabel "inclination [deg]"
set xrange [*:*]
set yrange [*:*]
set zrange [*:*]

splot "../result.dat" u 2:3:(atan2($7, v($5, $6))) w l t "inclination"
# splot "../result.dat" u 2:3:4 w l t "inclination"