#include <omp.h>

#include <atomic>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include "constants.hpp"
#include "integrator.hpp"
#include "parameter.hpp"
#include "simulation.hpp"

#define NUM_V0 1
#define NUM_CORES 8
#define PARAMETER_NUM 16
#define OUTPUT_DIR "result/ideal"

int main() {
  Parameter param;

  // 回すべきシミュレーションを精査する
  InitialAngle ideal_angle = {0, DEG_TO_RAD(180.0), DEG_TO_RAD(0.0)};

  // 出力用ディレクトリ作成
  std::ostringstream output_dirname;
  std::ostringstream output_filename;
  output_dirname << OUTPUT_DIR << "/Obl-" << std::setw(3) << std::setfill('0')
                 << static_cast<int>(param.obl_degree) << "_J2-" << J2_MAGNITUDE
                 << "_Gas-" << GAS_MAGNITUDE << "/out";
  std::filesystem::create_directories(output_dirname.str());

  // 理想実験におけるケース．v0は共回転半径によって固定（完全な円軌道）で，angleはy軸方向
  // 速度は正規化しなくてよい（そのまま）
  const double v0_50rM =
      std::sqrt(physics::G * physics::M_mars / (physics::r_M * 50.0));
  InitialCase ideal_case = {v0_50rM, ideal_angle};

  // 各v0ごとのサマリーcsvの設定
  std::ofstream parameter_summary_csv;
  std::ostringstream path;
  path << output_dirname.str() << "/Obl-" << std::setw(3) << std::setfill('0')
       << static_cast<int>(param.obl_degree) << "_J2-" << J2_MAGNITUDE
       << "_Gas-" << GAS_MAGNITUDE << "_ideal" << ".csv";
  parameter_summary_csv.open(path.str());
  parameter_summary_csv << "# "
                           "ID,v0,phi0,zeta0,N,year,result\n";

  std::cout << "Simulation Start\n"
            << "Parameter: \n"
            << "Obliquity = " << std::fixed << std::setprecision(2)
            << RAD_TO_DEG(param.obl) << "\n"
            << "J2 = " << std::scientific << std::setprecision(6) << param.J2
            << "\n"
            << "rho_neb = " << std::scientific << std::setprecision(6)
            << param.rho_neb << "\n";

  simulate_single(ideal_case, param, output_dirname.str(),
                  parameter_summary_csv);
}