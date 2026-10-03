#ifndef SIMULATION_HPP
#define SIMULATION_HPP

// 角度パラメータを保持する構造体
struct InitialAngle {
  int id;
  double phi;   // 方位角[rad]
  double zeta;  // 仰角[rad]
};

struct InitialCase {
  double v0;
  InitialAngle angle;
};

struct Record {
  double t;
  double x, y, z;
  double vx, vy, vz;
};

// Jacobiエネルギーの計算
// E_J = 0.5 * v^2 - 1.5*x^2 + 0.5*z^2 - 3/r + 4.5
inline double calc_jacobi_energy(const State& state) {
  double r = state.r.norm();
  double v2 = state.v.norm2();
  return 0.5 * v2 - 1.5 * (state.r.x * state.r.x) +
         0.5 * (state.r.z * state.r.z) - (3.0 / r) + 4.5;
}

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
                const double year,              // 最終時間
                const std::string& result_str   // 結果の分類
) {
  result_summary << std::fixed << std::setprecision(1) << std::setw(4)
                 << std::setfill('0') << id << "," << v0 << ","
                 << std::setprecision(15) << angle.phi << "," << angle.zeta
                 << "," << N << "," << std::scientific << std::setprecision(15)
                 << year << "," << result_str << "\n";
}

/*
void simulate(const std::vector<InitialCase>& initial_cases,
              const Parameter& param, std::ostringstream& output_dirname,
              std::ofstream& v0_summary_csv) {
  const double OUTPUT_INTERVAL = 1.0 / 128.0;  // 出力間隔[年]
  const double dt = physics::DT;               // 計算に用いるタイムステップ幅

  int terminated_num = 0;

  // 全通り試す
  for (size_t i = 0; i < initial_cases.size(); i++) {
    const auto& ic = initial_cases[i];
    int v0_int = static_cast<int>(ic.v0);
    int angle_id = ic.angle.id;

    // 出力ディレクトリパスの作成と存在確認（無ければ自動生成）
    int sub_dir = angle_id / 1024;
    std::ostringstream dir_path;
    dir_path << output_dirname.str() << "/v" << std::setw(3)
             << std::setfill('0') << v0_int << "/" << std::setw(2)
             << std::setfill('0') << sub_dir;
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
    State sat = init_state(ic.angle, ic.v0);
    double t = 0.0;
    bool terminated = false;  // 打ち切り判定

    // 初期位置，初速度の出力
    write_binary_output(ofs, t, sat);

    while (t < physics::MAX_YEARS - 1e-9) {
      // 次の出力時刻
      double next_output_time =
          std::min(t + OUTPUT_INTERVAL, physics::MAX_YEARS);

      // 最初に半ステップのガス抗力項RK4
      sat.v = rk4_step(sat, dt * 0.5, param);

      // 出力時刻が来るまで，全ステップ幅で計算する
      // 正確には，次の出力時刻の1ステップ前まで繰り返す
      while (t + physics::DT_YEARS < next_output_time - 1e-9) {
        // 全ステップ
        sat = leapfrog_step(sat, dt, t, param);
        sat.v = rk4_step(sat, dt, param);
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
      sat = leapfrog_step(sat, dt, t, param);
      sat.v = rk4_step(sat, dt * 0.5, param);
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
    record_csv(v0_summary_csv, angle_id, ic.angle, ic.v0, N, is_captured, t);
    // 明示的にディスクへ書き出す
    v0_summary_csv.flush();
  }
  return;
}

*/

// 1ケース分のシミュレーションを実行する関数
inline void simulate_single(const InitialCase& ic, const Parameter& param,
                            const std::string& output_dirname,
                            std::ofstream& v0_summary_csv,
                            std::mutex& v0_mutex) {
  const double OUTPUT_INTERVAL = 1.0 / 128.0;  // 出力間隔[年]
  const double dt = physics::DT;               // 計算に用いるタイムステップ幅

  int v0_int = static_cast<int>(ic.v0);
  int angle_id = ic.angle.id;

  // 出力ディレクトリパスの作成と存在確認（無ければ自動生成）
  int sub_dir = angle_id / 1024;
  std::ostringstream dir_path;
  dir_path << output_dirname << "/v" << std::setw(3) << std::setfill('0')
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
  if (!ofs.is_open()) {
    std::cerr << "Error: Cannot open " << out_file_path.str() << std::endl;
    return;
  }

  // 記録用の変数
  int N = 0;  // 周回数．火星中心距離の極小値でインクリメント．
  bool is_temporary_capture = false;
  bool checked_1year = false;
  bool is_under_ej = false;
  std::string result_str = "Unknown";

  // 周回数カウント用の極小値を求めるための距離保存用変数
  // 距離と言っているが，平方根を取る積極的理由が無いので，距離の2乗のまま比較
  double prev2_r2 = 0.0;  // 2ステップ前の微惑星の火星中心距離
  double prev1_r2 = 0.0;  // 2ステップ前の微惑星の火星中心距離

  // 初期条件の設定
  // サンプリングファイルから初期アングルを読んで，初速度を計算
  State sat = init_state(ic.angle, ic.v0);
  double t = 0.0;
  bool terminated = false;  // 打ち切り判定

  // 初期位置，初速度の出力
  write_binary_output(ofs, t, sat);

  while (t < physics::MAX_YEARS - 1e-9) {
    // 次の出力時刻
    double next_output_time = std::min(t + OUTPUT_INTERVAL, physics::MAX_YEARS);

    // 最初に半ステップのガス抗力項RK4
    sat.v = rk4_step(sat, dt * 0.5, param);

    // 出力時刻が来るまで，全ステップ幅で計算する
    // 正確には，次の出力時刻の1ステップ前まで繰り返す
    while (t + physics::DT_YEARS < next_output_time - 1e-9) {
      // 全ステップ
      sat = leapfrog_step(sat, dt, t, param);
      sat.v = rk4_step(sat, dt, param);
      t += physics::DT_YEARS;

      // Jacobi エネルギーが0を下回ったかどうかの判定
      if (!is_under_ej && calc_jacobi_energy(sat) <= 0.0) {
        is_under_ej = true;
      }

      // 一時捕獲を経由したかどうかの判定
      if (t >= 1.88 && !checked_1year) {
        checked_1year = true;
        if (!is_under_ej && calc_jacobi_energy(sat) > 0.0) {
          is_temporary_capture = true;
        }
      }

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
          result_str =
              is_temporary_capture ? "Temporary-Escape-L2" : "Direct-Escape-L2";
        } else {  // L1点からの脱出
          result_str =
              is_temporary_capture ? "Temporary-Escape-L1" : "Direct-Escape-L1";
        }
        write_binary_output(ofs, t, sat);
        break;
      } else if (r_sq < physics::r_M_norm_sq) {  // 火星表面に到達
        terminated = true;
        if (is_under_ej) {
          result_str =
              is_temporary_capture ? "Temporary-Capture" : "Direct-Capture";
        } else {
          result_str =
              is_temporary_capture ? "Temporary-Collision" : "Direct-Collision";
        }
        write_binary_output(ofs, t, sat);
        break;
      }
    }

    if (terminated) {
      break;
    }

    // 最終半ステップ
    sat = leapfrog_step(sat, dt, t, param);
    sat.v = rk4_step(sat, dt * 0.5, param);
    t += physics::DT_YEARS;

    // Jacobiエネルギーの判定
    if (!is_under_ej && calc_jacobi_energy(sat) <= 0.0) {
      is_under_ej = true;
    }

    // 一時捕獲判定
    if (t >= 1.88 && !checked_1year) {
      checked_1year = true;
      if (!is_under_ej && calc_jacobi_energy(sat) > 0.0) {
        is_temporary_capture = true;
      }
    }

    // 周回数チェック
    double current_r2 = sat.r.norm2();
    if (prev1_r2 < prev2_r2 && prev1_r2 < current_r2) {
      N++;
    }
    prev2_r2 = prev1_r2;
    prev1_r2 = current_r2;

    // 512ステップ目の打ち切り判定
    double r_sq = sat.r.norm2();
    if (r_sq > 4.0) {
      if (sat.r.x > 0) {  // L2点からの脱出
        result_str =
            is_temporary_capture ? "Temporary-Escape-L2" : "Direct-Escape-L2";
      } else {  // L1点からの脱出
        result_str =
            is_temporary_capture ? "Temporary-Escape-L1" : "Direct-Escape-L1";
      }
      write_binary_output(ofs, t, sat);
      break;
    } else if (r_sq < physics::r_M_norm_sq) {
      if (is_under_ej) {
        result_str =
            is_temporary_capture ? "Temporary-Capture" : "Direct-Capture";
      } else {
        result_str =
            is_temporary_capture ? "Temporary-Collision" : "Direct-Collision";
      }
      write_binary_output(ofs, t, sat);
      break;
    }

    // 上の半ステップ幅のRK4で時刻に正しい位置と速度になったので，出力
    write_binary_output(ofs, t, sat);
  }

  // MAX_YEARS に到達して脱出も衝突もしなかった場合
  if (!terminated && result_str == "Unknown") {
    result_str = is_temporary_capture ? "Temporary-Survive" : "Direct-Survive";
  }

  // サマリーCSVへの追記: 他スレッドとの衝突を防ぐためMutexを使って排他制御
  {
    std::lock_guard<std::mutex> lock(v0_mutex);
    record_csv(v0_summary_csv, angle_id, ic.angle, ic.v0, N, t, result_str);
    // 明示的にディスクへ書き出す
    v0_summary_csv.flush();
  }
}

#endif