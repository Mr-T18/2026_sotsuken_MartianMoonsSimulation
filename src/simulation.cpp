#include <fstream>
#include <iomanip>
#include <iostream>

#include "constants.hpp"
#include "integrator.hpp"

struct Record {
  double t;
  double x, y, z;
  double vx, vy, vz;
};

// バイナリ出力関数
inline void write_binary_output(std::ofstream& ofs, double t,
                                const State& sat) {
  Record rec = {t, sat.r.x, sat.r.y, sat.r.z, sat.v.x, sat.v.y, sat.v.z};
  ofs.write(reinterpret_cast<const char*>(&rec), sizeof(Record));
}

void output_state(std::ofstream& ofs, double t, const State& sat) {
  ofs << std::scientific << std::setprecision(15) << t << " " << sat.r.x << " "
      << sat.r.y << " " << sat.r.z << " " << sat.v.x << " " << sat.v.y << " "
      << sat.v.z << "\n";
}

int main() {
  // 初期条件の設定
  State sat = {{physics::x0, physics::y0, physics::z0},
               {physics::vx0, physics::vy0, physics::vz0}};

  std::ofstream ofs("out/result.bin", std::ios::binary);
  if (!ofs) {
    std::cerr << "Error: Cannot open resulut.dat" << std::endl;
  }
  std::cout << "Start Hill Simulation" << std::endl;

  double t = 0.0;
  const double OUTPUT_INTERVAL = 1e-3;  // 出力間隔[年]
  // 2のn乗のタイムステップ幅を
  double next_output_time = 0.0;
  const double dt = physics::DT;  // 計算に用いるタイムステップ幅

  // 初期位置，初速度の出力
  // output_state(ofs, t, sat);
  write_binary_output(ofs, t, sat);

  while (t < physics::MAX_YEARS - 1e-9) {
    // 次の出力時刻
    double next_output_time = std::min(t + OUTPUT_INTERVAL, physics::MAX_YEARS);

    // 最初に半ステップのガス抗力項RK4
    sat.v = rk4_step(sat, dt * 0.5);

    // 出力時刻が来るまで，全ステップ幅で計算する
    // 正確には，次の出力時刻の1ステップ前まで繰り返す
    while (t + physics::DT_YEARS < next_output_time - 1e-9) {
      sat = leapfrog_step(sat, dt);
      sat.v = rk4_step(sat, dt);
      t += physics::DT_YEARS;
    }

    // 出力時刻になったので，リープフロッグの後，半ステップのRK4で進めて，位置と速度を出力する
    sat = leapfrog_step(sat, dt);
    sat.v = rk4_step(sat, dt * 0.5);
    t += physics::DT_YEARS;

    // 上の半ステップ幅のRK4で時刻に正しい位置と速度になったので，出力
    write_binary_output(ofs, t, sat);
  }

  std::cout << "Simulation Finish!" << std::endl;
  return 0;
}