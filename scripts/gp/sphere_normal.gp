load "scripts/config.gp"

set terminal wxt size 900, 850 font "MS Gothic,14" title "火星自転軸と衛星軌道法線ベクトルの時間発展"
set angles radians
set macros

phi = 25.0 * pi / 180.0

hx(y, z, vy, vz) = y*vz - z*vy
hy(x, z, vx, vz) = z*vx - x*vz
hz(x, y, vx, vy) = x*vy - y*vx
h_norm(x, y, z, vx, vy, vz) = sqrt(hx(y,z,vy,vz)**2 + hy(x,z,vx,vz)**2 + hz(x,y,vx,vy)**2)

nx(x, y, z, vx, vy, vz) = hx(y,z,vy,vz) / h_norm(x,y,z,vx,vy,vz)
ny(x, y, z, vx, vy, vz) = hy(x,z,vx,vz) / h_norm(x,y,z,vx,vy,vz)
nz(x, y, z, vx, vy, vz) = hz(x,y,vx,vy) / h_norm(x,y,z,vx,vy,vz)

theta(t) = - omegaK * (t * SEC_PER_YEAR)
sx(t) = sin(phi) * cos(theta(t))
sy(t) = sin(phi) * sin(theta(t))
sz = cos(phi)

set view equal xyz
set view 60, 45, 1.2, 1.0
set xrange [-1:1]
set yrange [-1:1]
set zrange [-1:1]
set xlabel "X (Hill)"
set ylabel "Y (Hill)"
set zlabel "Z (Hill)"
set grid

set parametric
set urange [0:pi]
set vrange [0:2*pi]
set isosamples 15, 30

bin_file = (ARGC > 0) ? ARG1 : "result/ideal/Obl-025_J2-Small_Gas-Large/out/Obl-025_J2-Small_Gas-Large_ideal.bin"

# 再生制御パラメータ
step = 0
delta = 50

# [->/d]進む [<-/a]戻る [^/w]加速 [v/s]減速 [r]先頭

# 描画マクロ（原点から球面にベクトルを描画）
draw_frame = '\
    set title sprintf("Step: %d (送り幅: %d)", step, delta) noenhanced; \
    splot \
        cos(u)*cos(v), cos(u)*sin(v), sin(u) with lines lc rgb "#e8e8e8" notitle, \
        sin(phi)*cos(v), sin(phi)*sin(v), cos(phi) with lines lc rgb "#ffcccc" dt 2 lw 1.5 title "Spin Precession Circle", \
        bin_file binary format="%7double" every ::0::step \
        using (nx($2,$3,$4,$5,$6,$7)):(ny($2,$3,$4,$5,$6,$7)):(nz($2,$3,$4,$5,$6,$7)) \
        with lines lc rgb "#0066cc" lw 1.5 title "Normal Trajectory", \
        bin_file binary format="%7double" every ::step::step \
        using (0):(0):(0):(nx($2,$3,$4,$5,$6,$7)):(ny($2,$3,$4,$5,$6,$7)):(nz($2,$3,$4,$5,$6,$7)) \
        with vectors head filled size 0.08, 15 lw 3 lc rgb "#0044ff" title "Normal Vector (Now)", \
        bin_file binary format="%7double" every ::step::step \
        using (0):(0):(0):(sx($1)):(sy($1)):(sz) \
        with vectors head filled size 0.08, 15 lw 3 lc rgb "#cc0000" title "Spin Vector (Now)"'

# 初回描画
@draw_frame

# キー操作の割り当て
bind "Right" "step = step + delta; @draw_frame"
bind "d"     "step = step + delta; @draw_frame"

bind "Left"  "step = (step >= delta) ? step - delta : 0; @draw_frame"
bind "a"     "step = (step >= delta) ? step - delta : 0; @draw_frame"

bind "Up"    "delta = delta * 2; @draw_frame"
bind "w"     "delta = delta * 2; @draw_frame"

bind "Down"  "delta = (delta > 2) ? int(delta / 2) : 1; @draw_frame"
bind "s"     "delta = (delta > 2) ? int(delta / 2) : 1; @draw_frame"

bind "r"     "step = 0; @draw_frame"

# ウィンドウが閉じられるまで対話状態を維持
pause mouse close