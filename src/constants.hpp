#ifndef CONSTANTS_HPP
#define CONSTANTS_HPP
#define _USE_MATH_DEFINES

#include <cmath>
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define DEG_TO_RAD(x) (x * M_PI / 180.0)
#define RAD_TO_DEG(x) (x * 180.0 / M_PI)

namespace physics {
// 基本的な定数
const double G = 6.67430e-11;      // 万有引力定数 [m^3 kg^-1 s^-2]
const double M_sun = 1.99e30;      // 太陽質量 [kg]
const double M_mars = 6.42e23;     // 火星質量 [kg]
const double M_sat = 1.06e16;      // 衛星質量 [kg]
const double AU = 1.495978707e11;  // 天文単位 [m]
const double r_M = 3396.2e3;       // 火星赤道半径 [m]

// 火星の軌道長半径（約1.524 AU）[m]
const double MARS_SEMI_MAJOR_AXIS = 1.52368 * AU;

// 衛星の定数
const double a_b = 10.0 * 1000.0;  // 半径[m]
const double rho_b = 1850.0;       // 密度[kg m^-3]

// ガス密度
const double rho_neb = 4.7e-7;  // 密度[kg m^-3]
const double c_s = 840.4;       // 等温音速[m s^-1]
const double H =
    G * M_mars /
    (c_s *
     c_s);  // 大気のスケールハイト. 17.8[火星半径] -> [m]の単位への変換済み

// Hill座標系の定数
// Hill半径
const double r_H =
    MARS_SEMI_MAJOR_AXIS * std::pow(M_mars / (3.0 * M_sun), 1.0 / 3.0);
// 火星のケプラー角速度 omega_K
const double omega_K = std::sqrt(G * M_sun / std::pow(MARS_SEMI_MAJOR_AXIS, 3));
// 速度のスケール係数
const double v_scale = r_H * omega_K;

// タイムスケール
const double SEC_PER_YEAR = 365.25 * 24.0 * 3600.0;  // 1年（秒）
// omega_K(火星のケプラー角速度)で正規化した年の単位．
const double omega_K_yr = omega_K * SEC_PER_YEAR;

// シミュレーションの初期条件
const double v0_m_s = 20.0;
const double phi0_deg = 12.65817;
const double zeta0_deg = 75.84470;
// ラジアンに変換
const double phi0 = DEG_TO_RAD(phi0_deg);
const double zeta0 = DEG_TO_RAD(zeta0_deg);

// 速度を正規化
const double v_norm = v0_m_s / v_scale;

// 初期速度(単位 [m/s])
const double vx0 = -v_norm * std::cos(zeta0) * std::sin(phi0);
const double vy0 = -v_norm * std::cos(zeta0) * std::cos(phi0);
const double vz0 = v_norm * std::sin(zeta0);

// 初期位置(単位 [r_H])
const double x0 = 1.0;
const double y0 = 0.0;
const double z0 = 0.0;

// 積分のパラメータ
const double DT_YEARS =
    1.0 / 65536.0;  // [年] (正規化してない方程式では年のままで使う)
// 2^-nのタイムステップ幅を管理してみたらどうか
const double DT =
    DT_YEARS * omega_K_yr;  // [無次元] (正規化した方程式での積分につかう) (DT =
                            // d\tilde{t})
const double MAX_YEARS = 1000.0;

// 無次元化した火星半径とその2乗．衝突判定に用いる
const double r_M_norm = r_M / r_H;
const double r_M_norm_sq = r_M_norm * r_M_norm;

}  // namespace physics

#endif