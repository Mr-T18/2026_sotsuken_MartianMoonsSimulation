load "config.gp"

Ueff(x, y, z) = -1.5*x**2 + 0.5 * z**2 - 3.0/r_O(x, y, z) + 4.5
J(x, y, z, vx, vy, vz) = 0.5 * (vx**2 + vy**2 + vz**2) + Ueff(x, y, z)

t_min = 0
t_max = 5

# 太陽中心慣性座標での火星と衛星の位置
set output "../figures/jacobi.png"
set title "衛星のJacobiエネルギー"
set xlabel "t [yr]"
set ylabel "質量あたりのJacobiエネルギー [J/kg]"
set xrange [*:*]
set yrange [*:*]
plot "../out/result.dat" u ($1 >=  t_min && $1 <= t_max ? $1 : 1/0):(J($2, $3, $4, $5, $6, $7)) w p t "Energy"