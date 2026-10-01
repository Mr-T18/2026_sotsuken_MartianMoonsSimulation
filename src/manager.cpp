#include <omp.h>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include "constants.hpp"
#include "integrator.hpp"
#include "parameter.hpp"
#include "simulation.hpp"

#define NUM_CORES 8
#define ANGLES_CSV_PATH "result/gas-drag_capture_complete.csv"
#define OUTPUT_DIR "result/parameter"

// gas-drag_capture.csv を読み込んで std::vector配列 に格納する関数
std::vector<std::vector<CaptureCase>> load_capture_cases(
    const std::string& filepath) {
  std::vector<std::vector<CaptureCase>> cases(8);

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
    CaptureCase entry{};

    // 1列目: v0
    if (!std::getline(ss, item, ',')) continue;
    entry.v0 = std::stod(item);

    // 2列目: id
    if (!std::getline(ss, item, ',')) continue;
    entry.angle.id = std::stoi(item);

    // 3列目: phi
    if (!std::getline(ss, item, ',')) continue;
    entry.angle.phi = std::stod(item);

    // 4列目: zeta
    if (!std::getline(ss, item, ',')) continue;
    entry.angle.zeta = std::stod(item);

    int v0_index = (entry.v0 / 20) - 1;

    if (v0_index >= 0 && v0_index < NUM_CORES) {
      cases[v0_index].push_back(entry);
    }
  }

  return cases;
}

int main() {
  const double v0_list[8] = {20.0,  40.0,  60.0,  80.0,
                             100.0, 120.0, 140.0, 160.0};

  Parameter param = {physics::obliquity_rad, physics::J2, physics::rho_neb};

  // 回すべきシミュレーションを精査する
  std::vector<std::vector<CaptureCase>> capture_cases(8);
  try {
    capture_cases = load_capture_cases(ANGLES_CSV_PATH);
    std::cout << "Successfully loaded " << capture_cases.size()
              << " angle configurations." << std::endl;
  } catch (const std::exception& e) {
    std::cerr << e.what() << std::endl;
    return 1;
  }

  // 出力用ディレクトリ作成
  std::ostringstream output_dirname;
  std::ostringstream output_filename;
  output_dirname << OUTPUT_DIR << "/Obl-" << std::setw(3) << std::setfill('0')
                 << static_cast<int>(RAD_TO_DEG(param.obl)) << "_J2-"
                 << "midium"
                 << "_Gas-" << "Large" << "/out";
  std::filesystem::create_directories(output_dirname.str());
// それぞれのv0に対し，コアを割り当てて並列に処理する
#pragma omp parallel for num_threads(NUM_CORES)
  for (const auto& cases : capture_cases) {
    if (cases.empty()) continue;
    int v0_int = static_cast<int>(cases[0].v0);
    std::ostringstream v0_summary_csv_path;  // v0ごとのサマリーcsvパス
    v0_summary_csv_path << output_dirname.str() << "/v" << std::setw(3)
                        << std::setfill('0') << v0_int << ".csv";
    std::ofstream v0_summary_csv(v0_summary_csv_path.str());

    // ヘッダ行の記述
    v0_summary_csv << "# "
                      "ID,v0,phi0,zeta0,N,year,Temporary/Direct-Capture/"
                      "Collision/Escape\n";
    simulate(cases, param, output_dirname, v0_summary_csv);
  }
}