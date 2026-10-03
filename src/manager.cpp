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

#define NUM_V0 8
#define NUM_CORES 8
#define ANGLES_CSV_PATH "data/angles_4096.csv"
#define OUTPUT_DIR "result/gas-drag"

// 初期条件アングルcsv を読み込んで std::vector配列 に格納する関数
std::vector<InitialAngle> load_initial_angles(const std::string& filepath) {
  std::vector<InitialAngle> angles;

  std::ifstream ifs(filepath);
  if (!ifs.is_open()) {
    throw std::runtime_error("Error: Could not open file: " + filepath);
  }

  std::string line;
  while (std::getline(ifs, line)) {
    // 空行やコメント行，ヘッダ行のスキップ
    if (line.empty() || line[0] == '#' ||
        line.find("v0") != std::string::npos) {
      continue;
    }

    std::stringstream ss(line);
    std::string item;
    InitialAngle entry{};

    // 1列目: id
    if (!std::getline(ss, item, ',')) continue;
    entry.id = std::stoi(item);

    // 2列目: phi
    if (!std::getline(ss, item, ',')) continue;
    entry.phi = std::stod(item);

    // 3列目: zeta
    if (!std::getline(ss, item, ',')) continue;
    entry.zeta = std::stod(item);

    angles.push_back(entry);
  }

  return angles;
}

int main() {
  const double v0_list[8] = {20.0,  40.0,  60.0,  80.0,
                             100.0, 120.0, 140.0, 160.0};

  Parameter param = {physics::obliquity_rad, physics::J2, physics::rho_neb};

  // 回すべきシミュレーションを精査する
  std::vector<InitialAngle> angles;
  try {
    angles = load_initial_angles(ANGLES_CSV_PATH);
    std::cout << "Successfully loaded " << angles.size()
              << " angle configurations." << std::endl;
  } catch (const std::exception& e) {
    std::cerr << e.what() << std::endl;
    return 1;
  }

  // 出力用ディレクトリ作成
  std::ostringstream output_dirname;
  std::ostringstream output_filename;
  // output_dirname << OUTPUT_DIR << "/Obl-" << std::setw(3) <<
  // std::setfill('0')
  //                << static_cast<int>(RAD_TO_DEG(param.obl)) << "_J2-"
  //                << "midium"
  //                << "_Gas-" << "Large" << "/out";
  output_dirname << OUTPUT_DIR << "/out";
  std::filesystem::create_directories(output_dirname.str());

  // 8通りのv0ごとに全アングルを組み合わせたアンサンブルを構成; 計32768通り
  std::vector<InitialCase> all_cases;
  for (double v0 : v0_list) {
    for (const auto& ang : angles) {
      all_cases.push_back({v0, ang});
    }
  }

  std::cout << "Total simulation cases: " << all_cases.size() << std::endl;

  // 各v0ごとのサマリーcsvの設定
  std::ofstream v0_summary_csvs[NUM_V0];
  std::mutex v0_mutexes[NUM_V0];
  for (size_t i = 0; i < 8; i++) {
    int v0_int = static_cast<int>(v0_list[i]);
    std::ostringstream path;
    path << output_dirname.str() << "/v" << std::setw(3) << std::setfill('0')
         << v0_int << ".csv";
    v0_summary_csvs[i].open(path.str());
    v0_summary_csvs[i] << "# "
                          "ID,v0,phi0,zeta0,N,year,result\n";
  }

  // 進捗管理用変数
  std::atomic<int> completed_cases(0);
  std::mutex display_mutex;
  const size_t total_cases = all_cases.size();

  std::cout << "Simulation Start\n"
            << "Parameter: \n"
            << "Obliquity = " << std::fixed << std::setprecision(2)
            << RAD_TO_DEG(param.obl) << "\n"
            << "J2 = " << std::scientific << std::setprecision(6) << param.J2
            << "\n"
            << "rho_neb = " << std::scientific << std::setprecision(6)
            << param.rho_neb << "\n";

// それぞれのv0に対し，コアを割り当てて並列に処理する
#pragma omp parallel for num_threads(NUM_CORES) schedule(dynamic, 1)
  for (size_t i = 0; i < all_cases.size(); i++) {
    const auto& initial_case = all_cases[i];
    int v0_index = static_cast<int>(initial_case.v0 / 20.0) - 1;

    simulate_single(initial_case, param, output_dirname.str(),
                    v0_summary_csvs[v0_index], v0_mutexes[v0_index]);

    // カウントアップと進捗表示
    int done = ++completed_cases;
    // 画面表示（他スレッドとの衝突を防ぐためロックして \r で上書き）
    {
      std::lock_guard<std::mutex> lock(display_mutex);
      double percent = (100.0 * done) / total_cases;
      std::cout << "\rProgress: [" << std::setw(5) << done << " / "
                << total_cases << "] (" << std::fixed << std::setprecision(2)
                << percent << "%) | Last: v0=" << std::setw(3)
                << static_cast<int>(initial_case.v0)
                << " m/s, ID=" << std::setw(4) << std::setfill('0')
                << initial_case.angle.id << "    " << std::flush;
    }
  }

  // for (const auto& cases : capture_cases) {
  //   if (cases.empty()) continue;
  //   int v0_int = static_cast<int>(cases[0].v0);
  //   std::ostringstream v0_summary_csv_path;  // v0ごとのサマリーcsvパス
  //   v0_summary_csv_path << output_dirname.str() << "/v" << std::setw(3)
  //                       << std::setfill('0') << v0_int << ".csv";
  //   std::ofstream v0_summary_csv(v0_summary_csv_path.str());

  //   // ヘッダ行の記述
  //   v0_summary_csv << "# "
  //                     "ID,v0,phi0,zeta0,N,year,Temporary/Direct-Capture/"
  //                     "Collision/Escape\n";
  //   simulate(cases, param, output_dirname, v0_summary_csv);
  // }
}