#ifndef PARAMETER_HPP
#define PARAMETER_HPP
#define _USE_MATH_DEFINES

#define J2_MAGNITUDE "Midium"
#define GAS_MAGNITUDE "Large"

struct Parameter {
  double obl_degree = 25.0;
  double obl = DEG_TO_RAD(obl_degree);  // 自転軸傾斜角 [rad]
  double J2 = 0.001955;                 // 重力J2成分
  double rho_neb = 4.7e-7;              // ガス密度
};

#endif