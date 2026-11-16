load "scripts/config.gp"
set terminal pngcairo size 900, 900 font "MS Gothic, 14"
set output "stats/rL_vs_cos-phi/rL_vs_theta_J2-Small.png"
bin_path = "result/ideal/Obl-025_J2-Small_Gas-Large/out/Obl-025_J2-Small_Gas-Large_ideal.bin"

set angles radians
set xlabel "ラプラス半径で規格化した距離"
set ylabel "軌道法線ベクトル緯度 [deg]"
set xrange [0:5]
set yrange [*:*]
set grid ytics lc rgb "#dddddd" dt 2

# 物理パラメータ
J2_Medium = 0.001955
rL_Large = r_L(J2_Medium * 10.0)
rL_Medium = r_L(J2_Medium)
rL_Small = r_L(J2_Medium / 10.0)

scale_rM = rH / rM
r_norm_rM(x, y, z) = sqrt(x**2 + y**2 + z**2) * scale_rM

# 回転座標系における慣性角運動量ベクトル
hx(x, y, z, vx, vy, vz) = y * vz - z * (vy + x)
hy(x, y, z, vx, vy, vz) = z * (vx - y) - x * vz
hz(x, y, z, vx, vy, vz) = x * (vy + x) - y * (vx - y)
h_norm(x, y, z, vx, vy, vz) = sqrt(hx(x, y, z, vx, vy, vz)**2 + hy(x, y, z, vx, vy, vz)**2 + hz(x, y, z, vx, vy, vz)**2)

# 慣性空間固定基準軸への回転角 psi = +omegaK * t_sec
psi(t) = omegaK * (t*SEC_PER_YEAR)
hx_in(t, x, y, z, vx, vy, vz) = hx(x, y, z, vx, vy, vz) * cos(psi(t)) - hy(x, y, z, vx, vy, vz) * sin(psi(t))
hy_in(t, x, y, z, vx, vy, vz) = hx(x,y,z,vx,vy,vz) * sin(psi(t)) + hy(x,y,z,vx,vy,vz) * cos(psi(t))
hz_in(t, x, y, z, vx, vy, vz) = hz(x,y,z,vx,vy,vz)

clamp(v) = (v > 1.0) ? 1.0 : ((v < -1.0) ? -1.0 : v)

# 火星公転面法線を極とした天球上の緯度 theta [deg]と経度 phi [deg]
theta_deg(t, x, y, z, vx, vy, vz) = (h_norm(x, y, z, vx, vy, vz) > 1e-12) ? \
asin(clamp(hz_in(t, x, y, z, vx, vy, vz) / h_norm(x, y, z, vx, vy, vz))) * 180.0 / pi : 1/0

# h_norm > 1e-12 の重複計算を省き、hx_in と hy_in だけを評価
phi_deg(t, x, y, z, vx, vy, vz) = \
atan2(hy_in(t, x, y, z, vx, vy, vz), hx_in(t, x, y, z, vx, vy, vz)) * 180.0 / pi

plot bin_path binary format="%7double" every 15 \
     using (r_norm_rM($2,$3,$4) / rL_Small):(phi_deg($1,$2,$3,$4,$5,$6,$7)) with points pt 7 ps 0.35 lc rgb "#80cc0000" notitle