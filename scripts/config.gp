# このファイルを読み込め！！

# 定数だ
G = 6.67430e-11
MS = 1.99e30 # 太陽質量[kg]
MM = 6.42e23 # 火星質量[kg]
Ms = 1.06e16 # 衛星質量[kg]
AU = 1.495978707e11 # 天文単位[m]
rH = AU * (MM / (3 * MS))**(1.0/3.0) # Hill半径[m]
rM = 1.52368 * AU # 火星の軌道長半径[m]

# 関数だ
# Hill半径から火星半径の単位変換
rH_to_rM(x) = (x * rM) / rH

# 速度を求めるぞ
v(vx, vy) = sqrt(vx**2 + vy**2)

# 速度の2乗を求めるぞ
v2(vx, vy) = vx**2 + vy**2

# 2点間の距離を求めるぞ
r(x1, y1, z1, x2, y2, z2) = sqrt((x1 - x2)**2 + (y1 - y2)**2 + (z1 - z2)**2)
# 原点との距離
r_O(x, y, z) = sqrt(x**2 + y**2 + z**2)


set terminal pngcairo size 800,800 enhanced font 'MS Gothic,11'

set grid
set angle degrees