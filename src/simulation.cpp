#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "constants.hpp"
#include "integrator.hpp"

#define NUM_SAMPLES 4096
#define ANGLES_CSV_PATH "data/angles_4096.csv"

// 角度パラメータを保持する構造体
struct InitialAngle {
  int id;
  double phi;   // 方位角[rad]
  double zeta;  // 仰角[rad]
};

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

// angles_4096.csv を読み込んで std::vector に格納する関数
std::vector<InitialAngle> load_initial_angles(const std::string& filepath) {
  std::vector<InitialAngle> angles;
  angles.reserve(NUM_SAMPLES);  // メモリ再確保を防ぐため事前に予約

  std::ifstream ifs(filepath);
  if (!ifs.is_open()) {
    throw std::runtime_error("Error: Could not open file: " + filepath);
  }

  std::string line;
  while (std::getline(ifs, line)) {
    // 空行やコメント行のスキップ
    if (line.empty() || line[0] == '#') {
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

State init_state(const InitialAngle& angle, const double v0) {
  State sat;
  sat.r.x = 1.0;
  sat.r.y = 0.0;
  sat.r.z = 0.0;
  double v_norm = v0 / physics::v_scale;
  sat.v.x = -v_norm * std::cos(angle.zeta) * std::sin(angle.phi);
  sat.v.y = -v_norm * std::cos(angle.zeta) * std::cos(angle.phi);
  sat.v.z = v_norm * std::sin(angle.zeta);
  return sat;
}

int main() {
  const double OUTPUT_INTERVAL = 1.0 / 128.0;  // 出力間隔[年]
  const double dt = physics::DT;               // 計算に用いるタイムステップ幅

  // 初期アングルのcsvファイル -> 初期アングル構造体のリスト
  std::vector<InitialAngle> angles;
  try {
    angles = load_initial_angles(ANGLES_CSV_PATH);
    std::cout << "Successfully loaded " << angles.size()
              << " angle configurations." << std::endl;
  } catch (const std::exception& e) {
    std::cerr << e.what() << std::endl;
    return 1;
  }

  std::vector<double> v0_list = {20.0,  40.0,  60.0,  80.0,
                                 100.0, 120.0, 140.0, 160.0};

  std::cout << "Start Hill Simulation" << std::endl;

  for (size_t v0_id = 0; v0_id < v0_list.size(); v0_id++) {
    double v0 = v0_list[v0_id];
    int v0_int = static_cast<int>(v0);
    // 4096通り試す
    for (int angle_id = 0; angle_id < NUM_SAMPLES; angle_id++) {
      // 出力ディレクトリパスの作成と存在確認（無ければ自動生成）
      int sub_dir = angle_id / 1024;
      std::ostringstream dir_path;
      dir_path << "out/v" << std::setw(3) << std::setfill('0') << v0_int << "/"
               << std::setw(2) << std::setfill('0') << sub_dir;
      // 新しいサブディレクトリの作成．1024の倍数のときのみ．
      if (angle_id % 1024 == 0) {
        std::filesystem::create_directories(dir_path.str());
      }

      // 出力ファイルパスの作成
      std::ostringstream out_file_path;
      out_file_path << dir_path.str() << "/v" << std::setw(3)
                    << std::setfill('0') << v0_int << "_" << std::setw(4)
                    << std::setfill('0') << angle_id << ".bin";
      std::ofstream ofs(out_file_path.str(), std::ios::binary);
      if (!ofs) {
        std::cerr << "Error: Cannot open " << out_file_path.str() << std::endl;
        continue;
      }

      // 初期条件の設定
      // サンプリングファイルから初期アングルを読んで，初速度を計算
      State sat = init_state(angles[angle_id], v0);
      double t = 0.0;
      bool terminated = false;  // 打ち切り判定

      // 初期位置，初速度の出力
      write_binary_output(ofs, t, sat);

      while (t < physics::MAX_YEARS - 1e-9) {
        // 次の出力時刻
        double next_output_time =
            std::min(t + OUTPUT_INTERVAL, physics::MAX_YEARS);

        // 最初に半ステップのガス抗力項RK4
        sat.v = rk4_step(sat, dt * 0.5);

        // 出力時刻が来るまで，全ステップ幅で計算する
        // 正確には，次の出力時刻の1ステップ前まで繰り返す
        while (t + physics::DT_YEARS < next_output_time - 1e-9) {
          // 全ステップ
          sat = leapfrog_step(sat, dt);
          sat.v = rk4_step(sat, dt);
          t += physics::DT_YEARS;

          // 脱出判定． r > 2.0 r_H で脱出，もしくは火星に衝突したら打ち切り
          double r_sq =
              sat.r.x * sat.r.x + sat.r.y * sat.r.y + sat.r.z * sat.r.z;
          if (r_sq > 4.0 || r_sq < physics::r_M_norm_sq) {
            terminated = true;
            break;
          }
        }

        if (terminated) {
          break;
        }

        // 最終半ステップ
        sat = leapfrog_step(sat, dt);
        sat.v = rk4_step(sat, dt * 0.5);
        t += physics::DT_YEARS;

        // 上の半ステップ幅のRK4で時刻に正しい位置と速度になったので，出力
        write_binary_output(ofs, t, sat);
      }
    }
  }

  std::cout << "Simulation Finish!" << std::endl;
  return 0;
}