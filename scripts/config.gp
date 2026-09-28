# このファイルを読み込め！！

# 定数だ
G = 6.67430e-11
MS = 1.99e30 # 太陽質量[kg]
MM = 6.42e23 # 火星質量[kg]
Ms = 1.06e16 # 衛星質量[kg]
AU = 1.495978707e11 # 天文単位[m]
rM = 3396.2e3 # 火星赤道半径 [m]
MARS_SEMI_MAJOR_AXIS = 1.52368 * AU # 火星の軌道長半径[m]
rH = MARS_SEMI_MAJOR_AXIS * (MM / (3 * MS))**(1.0/3.0) # Hill半径[m]

# 関数だ
# Hill半径から火星半径の単位変換
rH_to_rM(x) = (x * rH) / rM

# 速度を求めるぞ
v(vx, vy, vz) = sqrt(vx**2 + vy**2 + vz**2)

# 速度の2乗を求めるぞ
v2(vx, vy, vz) = vx**2 + vy**2 + vz**2

# 2点間の距離を求めるぞ
r(x1, y1, z1, x2, y2, z2) = sqrt((x1 - x2)**2 + (y1 - y2)**2 + (z1 - z2)**2)
# 原点との距離
r_O(x, y, z) = sqrt(x**2 + y**2 + z**2)

DEG_TO_RAD(deg) = deg / 180.0 * pi
RAD_TO_DEG(rad) = rad * 180.0 / pi

dot(v11, v12, v13, v21, v22, v23) = v11 * v21 + v12 * v22 + v13 * v23

set terminal pngcairo size 800,800 enhanced font 'MS Gothic,11'

set grid
set angle degrees