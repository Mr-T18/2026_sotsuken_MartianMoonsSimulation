import numpy as np

G = 6.67430e-11
M_SUN = 1.99e30
AU = 1.495978707e11
MARS_SEMI_MAJOR_AXIS = 1.52368 * AU

SEC_PER_YEAR = 365.25 * 86400
OMEGA_K = np.sqrt(G * M_SUN / np.power(MARS_SEMI_MAJOR_AXIS, 3))
PHI = 25.0 * np.pi / 180.0

RH_OVER_RM = 319.1632070652  # Hill半径 [火星半径]
R_COROT_RM = 6.015  # 共回転半径 [火星半径]
R_M = 3396.2e3  # 火星赤道半径 [m]


class State:
    def __init__(self, t, x, y, z, vx, vy, vz):
        self.t = t
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx
        self.vy = vy
        self.vz = vz

    def compute_semi_major_axis_rM(self):
        """位置と速度から軌道長半径[rM]を算出"""
        r = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        v_in_sq = (self.vx - self.y) ** 2 + (self.vy + self.x) ** 2 + self.vz**2

        inv_a = (2.0 / r) - (v_in_sq / 3.0)

        a_rH = np.where(inv_a > 0.0, 1.0 / inv_a, np.nan)
        return a_rH * RH_OVER_RM

    def compute_eccentricity(self):
        """位置と速度から離心率を算出"""
        r = np.sqrt(self.x**2 + self.y**2 + self.z**2)
        vx_in = self.vx - self.y
        vy_in = self.vy + self.x
        vz_in = self.vz
        v_in_sq = vx_in**2 + vy_in**2 + vz_in**2

        # 慣性系比角運動量ベクトル
        hx = self.y * vz_in - self.z * vy_in
        hy = self.z * vx_in - self.x * vz_in
        hz = self.x * vy_in - self.y * vx_in
        h_sq = hx**2 + hy**2 + hz**2

        # 比軌道エネルギー
        eps = 0.5 * v_in_sq - (3.0 / r)

        # e^2 = 1 + 2 * eps * h^2 / mu^2
        e_sq = 1.0 + (2.0 * eps * h_sq) / 9.0
        return np.sqrt(np.maximum(e_sq, 0.0))

    def compute_inclination_orb(self):
        """火星公転面に対する軌道傾斜角"""
        # 慣性系速度
        vx_in = self.vx - self.y
        vy_in = self.vy + self.x
        vz_in = self.vz

        # 角運動量ベクトル
        hx = self.y * vz_in - self.z * vy_in
        hy = self.z * vx_in - self.x * vz_in
        hz = self.x * vy_in - self.y * vx_in
        h_norm = np.sqrt(hx**2 + hy**2 + hz**2)
        if h_norm < 1e-12:
            return None
        cos_i = hz / h_norm
        cos_i = np.clip(cos_i, -1.0, 1.0)
        i_orb = np.degrees(np.arccos(cos_i))
        return i_orb

    def compute_inclination_eq(self):
        """火星赤道面に対する軌道傾斜角"""
        # 慣性系速度
        vx_in = self.vx - self.y
        vy_in = self.vy + self.x
        vz_in = self.vz

        # 角運動量ベクトル
        hx = self.y * vz_in - self.z * vy_in
        hy = self.z * vx_in - self.x * vz_in
        hz = self.x * vy_in - self.y * vx_in
        h_norm = np.sqrt(hx**2 + hy**2 + hz**2)
        if h_norm < 1e-12:
            return None

        # 火星自転軸ベクトル
        theta = -OMEGA_K * (self.t * SEC_PER_YEAR)
        sx = np.sin(PHI) * np.cos(theta)
        sy = np.sin(PHI) * np.sin(theta)
        sz = np.cos(PHI)

        # 赤道面に対する傾斜角
        cos_i = (hx * sx + hy * sy + hz * sz) / h_norm
        cos_i = np.clip(cos_i, -1.0, 1.0)
        i_eq = np.degrees(np.arccos(cos_i))
        return i_eq
