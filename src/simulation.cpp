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

#define ANGLES_CSV_PATH "result/gas-drag_capture.csv"
#define RESULT_CSV_PATH "result/bulge/out/result_summary.csv"

// 角度パラメータを保持する構造体
struct InitialAngle {
  int id;
  double phi;   // 方位角[rad]
  double zeta;  // 仰角[rad]
};

struct CaptureCase {
  double v0;
  InitialAngle angle;
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

// gas-drag_capture.csv を読み込んで std::vector に格納する関数
std::vector<CaptureCase> load_capture_cases(const std::string& filepath) {
  std::vector<CaptureCase> cases;

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

    cases.push_back(entry);
  }

  return cases;
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
void record_csv(std::ofstream& result_summary,  // サマリーCSV
                const int id,                   // id
                const InitialAngle& angle,      // 初期条件
                const double v0,                // 初速度
                const int N,                    // 周回数
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

  result_summary << std::fixed << std::setprecision(1) << std::setw(4)
                 << std::setfill('0') << id << "," << v0 << ","
                 << std::setprecision(15) << angle.phi << "," << angle.zeta
                 << "," << N << "," << std::scientific << std::setprecision(15)
                 << year << "," << is_captured_str << "\n";
}

int main() {
  const double OUTPUT_INTERVAL = 1.0 / 128.0;  // 出力間隔[年]
  const double dt = physics::DT;               // 計算に用いるタイムステップ幅

  std::vector<CaptureCase> capture_cases;
  try {
    capture_cases = load_capture_cases(ANGLES_CSV_PATH);
    std::cout << "Successfully loaded " << capture_cases.size()
              << " angle configurations." << std::endl;
  } catch (const std::exception& e) {
    std::cerr << e.what() << std::endl;
    return 1;
  }

  std::cout << "Start Hill Simulation" << std::endl;

  std::filesystem::create_directories("result/bulge/out");
  std::ofstream result_summary(RESULT_CSV_PATH);
  if (!result_summary) {
    std::cerr << "Error: Cannot open " << RESULT_CSV_PATH << std::endl;
    return 1;
  }
  // ヘッダ行の記述
  result_summary << "# ID,v0,phi0,zeta0,N,year,Capture/Escape/Survive\n";

  int terminated_num = 0;

  // 全通り試す
  for (size_t i = 0; i < capture_cases.size(); i++) {
    const auto& cc = capture_cases[i];
    int v0_int = static_cast<int>(cc.v0);
    int angle_id = cc.angle.id;

    // 出力ディレクトリパスの作成と存在確認（無ければ自動生成）
    int sub_dir = angle_id / 1024;
    std::ostringstream dir_path;
    dir_path << "result/bulge/out/v" << std::setw(3) << std::setfill('0')
             << v0_int << "/" << std::setw(2) << std::setfill('0') << sub_dir;
    if (!std::filesystem::exists(dir_path.str())) {
      std::filesystem::create_directories(dir_path.str());
    }

    // 出力ファイルパスの作成
    std::ostringstream out_file_path;
    out_file_path << dir_path.str() << "/v" << std::setw(3) << std::setfill('0')
                  << v0_int << "_" << std::setw(4) << std::setfill('0')
                  << angle_id << ".bin";
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
    State sat = init_state(cc.angle, cc.v0);
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
        sat = leapfrog_step(sat, dt, t, physics::obliquity);
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
        double r_sq = sat.r.norm2();
        if (r_sq > 4.0) {  // 脱出
          terminated = true;
          if (sat.r.x > 0) {  // L2点からの脱出
            is_captured = 2;
          } else {  // L1点からの脱出
            is_captured = 1;
          }
          write_binary_output(ofs, t, sat);
          break;
        } else if (r_sq < physics::r_M_norm_sq) {  // 捕獲
          terminated = true;
          is_captured = 0;
          write_binary_output(ofs, t, sat);
          break;
        }
      }

      if (terminated) {
        terminated_num++;
        break;
      }

      // 最終半ステップ
      sat = leapfrog_step(sat, dt, t, physics::obliquity);
      sat.v = rk4_step(sat, dt * 0.5);
      t += physics::DT_YEARS;

      // 512ステップ目の周回数チェック
      double current_r2 = sat.r.norm2();
      if (prev1_r2 < prev2_r2 && prev1_r2 < current_r2) {
        N++;
      }
      prev2_r2 = prev1_r2;
      prev1_r2 = current_r2;

      // 512ステップ目の打ち切り判定
      double r_sq = sat.r.norm2();
      if (r_sq > 4.0) {
        is_captured = (sat.r.x > 0) ? 2 : 1;
        write_binary_output(ofs, t, sat);
        break;
      } else if (r_sq < physics::r_M_norm_sq) {
        is_captured = 0;
        write_binary_output(ofs, t, sat);
        break;
      }

      // 上の半ステップ幅のRK4で時刻に正しい位置と速度になったので，出力
      write_binary_output(ofs, t, sat);
    }
    record_csv(result_summary, angle_id, cc.angle, cc.v0, N, is_captured, t);
    // 明示的にディスクへ書き出す
    result_summary.flush();

    // 1件終わるたびに行頭（または進捗部分）を上書き更新
    std::cout << "\rRunning v0 = " << std::setw(3) << v0_int
              << " m/s, ID=" << std::setw(4) << std::setfill('0') << angle_id
              << ", COMPLETE: " << terminated_num << std::flush;
  }
  std::cout << " -> Done!" << std::endl;

  std::cout << "Simulation Finish!" << std::endl;
  return 0;
}