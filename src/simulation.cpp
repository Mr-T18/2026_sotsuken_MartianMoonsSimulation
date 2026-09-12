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

#define NUM_SAMPLES 10
#define ANGLES_CSV_PATH "data/angles_4096.csv"
#define RESULT_CSV_PATH "out/result_summary.csv"

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

// 1つのシミュレーションの結果(周回数，捕獲衝突or脱出)
void record_csv(std::ofstream& ofs_all_summary,  // すべてのサマリーCSV
                std::ofstream& ofs_v0_summary,   // それぞれのv0のサマリーCSV
                const int id,                    // id
                const InitialAngle& angle,       // 初期条件
                const double v0,                 // 初速度
                const int N,                     // 周回数
                const int is_captured,  // 捕獲：0, L1から脱出：1, L2から脱出：2
                const double year       // 最終時間
) {
  std::string_view is_captured_str;
  if (is_captured == 0) {
    is_captured_str = "C";
  } else if (is_captured == 1) {
    is_captured_str = "E1";
  } else if (is_captured == 2) {
    is_captured_str = "E2";
  } else if (is_captured == -1) {
    is_captured_str = "S";
  } else {
    is_captured_str = "null";
  }

  ofs_all_summary << std::fixed << std::setprecision(1) << std::setw(4)
                  << std::setfill('0') << id << "," << v0 << ","
                  << std::setprecision(15) << angle.phi << "," << angle.zeta
                  << "," << N << "," << std::scientific << std::setprecision(15)
                  << year << "," << is_captured_str << "\n";

  ofs_v0_summary << std::fixed << std::setprecision(1) << std::setw(4)
                 << std::setfill('0') << id << "," << v0 << ","
                 << std::setprecision(15) << angle.phi << "," << angle.zeta
                 << "," << N << "," << std::scientific << std::setprecision(15)
                 << year << "," << is_captured_str << "\n";
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

  // すべての結果のサマリーCSVの作成
  std::ofstream ofs_all_summary(RESULT_CSV_PATH);
  if (!ofs_all_summary) {
    std::cerr << "Error: Cannot open " << RESULT_CSV_PATH << std::endl;
    return 1;
  }
  // ヘッダ行の記述
  ofs_all_summary << "# ID,v0,phi0,zeta0,N,year,Capture/Escape/Survive" << "\n";

  std::vector<double> v0_list = {20.0,  40.0,  60.0,  80.0,
                                 100.0, 120.0, 140.0, 160.0};

  std::cout << "Start Hill Simulation" << std::endl;

  for (size_t v0_id = 0; v0_id < v0_list.size(); v0_id++) {
    double v0 = v0_list[v0_id];
    int v0_int = static_cast<int>(v0);

    // それぞれの初速度のサマリーcsvを作成
    std::ostringstream v0summary_csv_path;
    v0summary_csv_path << "out/v" << std::setw(3) << std::setfill('0') << v0_int
                       << ".csv";
    std::ofstream ofs_v0_summary(v0summary_csv_path.str());
    if (!ofs_v0_summary) {
      std::cerr << "Error: Cannot open " << v0summary_csv_path.str()
                << std::endl;
      continue;
    }
    // ヘッダ行の記述
    ofs_v0_summary << "# ID,v0,phi0,zeta0,N,year,Capture/Escape/Survive"
                   << "\n";

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

      // 記録用の変数
      int N = 0;             // 周回数．火星中心距離の極小値でインクリメント．
      int is_captured = -1;  // 捕獲(0) or 脱出(1,2)

      // 周回数カウント用の極小値を求めるための距離保存用変数
      // 距離と言っているが，平方根を取る積極的理由が無いので，距離の2乗のまま比較
      double prev2_r2 = 0.0;  // 2ステップ前の微惑星の火星中心距離
      double prev1_r2 = 0.0;  // 2ステップ前の微惑星の火星中心距離

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

          // 周回数のカウント
          double current_r2 = sat.r.norm2();
          // 極小のチェック
          if (prev1_r2 < prev2_r2 && prev1_r2 < current_r2) {
            N++;  // 1つ前の距離が極小値を取ったので，周回数をカウント
          }
          prev2_r2 = prev1_r2;
          prev1_r2 = current_r2;

          // 脱出判定． r > 2.0 r_H で脱出，もしくは火星に衝突したら打ち切り
          double r_sq =
              sat.r.x * sat.r.x + sat.r.y * sat.r.y + sat.r.z * sat.r.z;
          if (r_sq > 4.0) {  // 脱出
            terminated = true;
            if (sat.r.x > 0) {  // L2点からの脱出
              is_captured = 2;
            } else {  // L1点からの脱出
              is_captured = 1;
            }
            break;
          } else if (r_sq < physics::r_M_norm_sq) {  // 捕獲
            terminated = true;
            is_captured = 0;
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
      record_csv(ofs_all_summary, ofs_v0_summary, angle_id, angles[angle_id],
                 v0, N, is_captured, t);
      // 明示的にディスクへ書き出す
      ofs_all_summary.flush();
      ofs_v0_summary.flush();
    }
  }

  std::cout << "Simulation Finish!" << std::endl;
  return 0;
}