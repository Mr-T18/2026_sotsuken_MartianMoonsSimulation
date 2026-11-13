load "config.gp"
set terminal qt
set angle degrees
set mouse

# set output "../plot/inclination.png"
set title "trajectory - inclination"
set xlabel "x [r_H]"
set ylabel "y [r_H]"
set zlabel "z [r_H]"
set xrange [-1.0:1.0]
set yrange [-1.0:1.0]
set zrange [*:*]

splot "../result.dat" u 2:3:4 w l t "inclination"