load "scripts/config.gp"
set terminal pngcairo size 1200, 1200 font "MS Gothic,13"
set output "stats/inclination_eq_laplace/inclination_eq_laplace_multi.png"

set angles radians
set xrange [0:5]
set yrange [0:35]
set grid ytics lc rgb "#dddddd" dt 2

J2_Midium = 0.001955
rL_Large  = r_L(J2_Midium * 10.0)
rL_Midium = r_L(J2_Midium)
rL_Small  = r_L(J2_Midium / 10.0)

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

set multiplot layout 3, 1 title "ラプラス半径で規格化した距離 vs 軌道傾斜角"
set lmargin 10
set rmargin 4

# --- 上段: J2 = Large ---
set tmargin 1.5
set bmargin 1.5
set format x ""
unset xlabel
set ylabel "傾斜角 i [deg]"
set arrow 1 from 1.0, 0 to 1.0, 35 nohead lc rgb "#cccc00" dt 2 lw 2.5
set label 1 "J2 = 0.01955 (Large)" at graph 0.03, 0.88 font "MS Gothic,13"
plot "result/parameter/Obl-025_J2-Large_Gas-Large/out/v020/00/v020_0001.bin" binary format="%7double" every 5 \
     using (r_norm_rM($2,$3,$4) / rL_Large):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#80cc0000" notitle

# --- 中段: J2 = Midium ---
set ylabel "傾斜角 i [deg]"
set label 1 "J2 = 0.001955 (Midium)" at graph 0.03, 0.88 font "MS Gothic,13"
plot "result/parameter/Obl-025_J2-Midium_Gas-Large/out/v020/00/v020_0001.bin" binary format="%7double" every 5 \
     using (r_norm_rM($2,$3,$4) / rL_Midium):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#8000aa00" notitle

# --- 下段: J2 = Small ---
set bmargin 4.0
set format x "%g"
set xlabel "ラプラス半径距離 r [r_L]"
set ylabel "傾斜角 i [deg]"
set label 1 "J2 = 0.0001955 (Small)" at graph 0.03, 0.88 font "MS Gothic,13"
plot "result/parameter/Obl-025_J2-Small_Gas-Large/out/v020/00/v020_0001.bin" binary format="%7double" every 5 \
     using (r_norm_rM($2,$3,$4) / rL_Small):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#800000cc" notitle

unset multiplot

# 描画順を Small -> Midium -> Large に変更し、every 15 で間引く
plot \
  "result/parameter/Obl-025_J2-Small_Gas-Large/out/v020/00/v020_0001.bin" binary format="%7double" every 15 \
    using (r_norm_rM($2,$3,$4) / rL_Small):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.3 lc rgb "#c00000cc" notitle, \
  "result/parameter/Obl-025_J2-Midium_Gas-Large/out/v020/00/v020_0001.bin" binary format="%7double" every 15 \
    using (r_norm_rM($2,$3,$4) / rL_Midium):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.3 lc rgb "#c000aa00" notitle, \
  "result/parameter/Obl-025_J2-Large_Gas-Large/out/v020/00/v020_0001.bin" binary format="%7double" every 15 \
    using (r_norm_rM($2,$3,$4) / rL_Large):(inc_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.3 lc rgb "#b0cc0000" notitle, \
  1/0 with points pt 7 ps 1.5 lc rgb "#cc0000" title "J2=0.01955", \
  1/0 with points pt 7 ps 1.5 lc rgb "#00aa00" title "J2=0.001955", \
  1/0 with points pt 7 ps 1.5 lc rgb "#0000cc" title "J2=0.0001955"