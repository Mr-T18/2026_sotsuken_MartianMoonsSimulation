load "scripts/config.gp"
set terminal pngcairo size 900, 600 font "MS Gothic,18"

set angles radians
set xrange [0:5]
set yrange [0:35]
set grid ytics lc rgb "#dddddd" dt 2

J2_Medium = 0.001955
rL_Large  = r_L(J2_Medium * 10.0)
rL_Medium = r_L(J2_Medium)
rL_Small  = r_L(J2_Medium / 10.0)
rL_Quarter1 = r_L(J2_Medium* 10.0**(-0.25))
rL_Quarter2 = r_L(J2_Medium* 10.0**(-0.5))
rL_Quarter3 = r_L(J2_Medium * 10.0**(-0.75))

scale_rM = rH / rM
r_norm_rM(x, y, z) = sqrt(x*x + y*y + z*z) * scale_rM
hx(y, z, vy, vz) = y*vz - z*vy
hy(x, z, vx, vz) = z*vx - x*vz
hz(x, y, vx, vy) = x*vy - y*vx
h_norm(x, y, z, vx, vy, vz) = sqrt(hx(y,z,vy,vz)**2 + hy(x,z,vx,vz)**2 + hz(x,y,vx,vy)**2)

phi = 25.0 * pi / 180.0
theta(t) = - omegaK * (t * SEC_PER_YEAR)
sx(t) = sin(phi) * cos(theta(t))
sy(t) = sin(phi) * sin(theta(t))
sz = cos(phi)
clamp(v) = (v > 1.0) ? 1.0 : ((v < -1.0) ? -1.0 : v)
cos_i(t, x, y, z, vx, vy, vz) = (h_norm(x,y,z,vx,vy,vz) > 1e-12) ? \
    clamp(dot(hx(y,z,vy,vz), hy(x,z,vx,vz), hz(x,y,vx,vy), sx(t), sy(t), sz) / h_norm(x,y,z,vx,vy,vz)) : 1/0
inc_deg(t, x, y, z, vx, vy, vz) = acos(cos_i(t, x, y, z, vx, vy, vz)) * 180.0 / pi

# --- J2 = Large ---
set output "stats/inclination_eq_laplace/inclination_eq_laplace_J2-Large.png"
set xlabel "火星からの距離 r [r_L]"
set ylabel "傾斜角 i [deg]"
set arrow 1 from 1.0, 0 to 1.0, 35 nohead lc rgb "#cccc00" dt 2 lw 2.5
set label 1 "J2 = 0.01955 (Large)" at graph 0.03, 0.88 font "MS Gothic,13"
plot "result/ideal/Obl-025_J2-Large_Gas-Large/out/Obl-025_J2-Large_Gas-Large_ideal.bin" binary format="%7double" every 5 \
     using (r_norm_rM($2,$3,$4) / rL_Large):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#cc0000" notitle

# --- J2 = Medium ---
set output "stats/inclination_eq_laplace/inclination_eq_laplace_J2-Medium.png"
set xlabel "火星からの距離 r [r_L]"
set ylabel "傾斜角 i [deg]"
set label 1 "J2 = 0.001955 (Medium)" at graph 0.03, 0.88 font "MS Gothic,13"
plot "result/ideal/Obl-025_J2-Medium_Gas-Large/out/Obl-025_J2-Medium_Gas-Large_ideal.bin" binary format="%7double" every 5 \
     using (r_norm_rM($2,$3,$4) / rL_Medium):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#00aa00" notitle

# --- J2 = Small ---
set output "stats/inclination_eq_laplace/inclination_eq_laplace_J2-Small.png"
set xlabel "火星からの距離 r [r_L]"
set ylabel "傾斜角 i [deg]"
set label 1 "J2 = 0.0001955 (Small)" at graph 0.03, 0.88 font "MS Gothic,13"
plot "result/ideal/Obl-025_J2-Small_Gas-Large/out/Obl-025_J2-Small_Gas-Large_ideal.bin" binary format="%7double" every 5 \
     using (r_norm_rM($2,$3,$4) / rL_Small):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#0000cc" notitle


# --- J2 = Quarter1 ---
set output "stats/inclination_eq_laplace/inclination_eq_laplace_J2-Quarter1.png"
set xlabel "火星からの距離 r [r_L]"
set ylabel "傾斜角 i [deg]"
set label 1 "J2 = 0.001955 * 10^{1/4} (Quarter1)" at graph 0.03, 0.88 font "MS Gothic,13"
plot "result/ideal/Obl-025_J2-Quarter1_Gas-Large/out/Obl-025_J2-Quarter1_Gas-Large_ideal.bin" binary format="%7double" every 5 \
     using (r_norm_rM($2,$3,$4) / rL_Quarter1):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#aa00aa" notitle


# --- J2 = Quarter2 ---
set output "stats/inclination_eq_laplace/inclination_eq_laplace_J2-Quarter2.png"
set xlabel "火星からの距離 r [r_L]"
set ylabel "傾斜角 i [deg]"
set label 1 "J2 = 0.001955 * 10^{2/4} (Quarter2)" at graph 0.03, 0.88 font "MS Gothic,13"
plot "result/ideal/Obl-025_J2-Quarter2_Gas-Large/out/Obl-025_J2-Quarter2_Gas-Large_ideal.bin" binary format="%7double" every 5 \
     using (r_norm_rM($2,$3,$4) / rL_Quarter2):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#00aaaa" notitle



# --- J2 = Quarter3 ---
set output "stats/inclination_eq_laplace/inclination_eq_laplace_J2-Quarter3.png"
set xlabel "火星からの距離 r [r_L]"
set ylabel "傾斜角 i [deg]"
set label 1 "J2 = 0.001955 * 10^{3/4} (Quarter3)" at graph 0.03, 0.88 font "MS Gothic,13"
plot "result/ideal/Obl-025_J2-Quarter3_Gas-Large/out/Obl-025_J2-Quarter3_Gas-Large_ideal.bin" binary format="%7double" every 5 \
     using (r_norm_rM($2,$3,$4) / rL_Quarter3):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#f87800" notitle