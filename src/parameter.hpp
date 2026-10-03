#ifndef PARAMETER_HPP
#define PARAMETER_HPP
#define _USE_MATH_DEFINES

struct Parameter {
  double obl;      // 自転軸傾斜角 [rad]
  double J2;       // 重力J2成分
  double rho_neb;  // ガス密度
};

#endif