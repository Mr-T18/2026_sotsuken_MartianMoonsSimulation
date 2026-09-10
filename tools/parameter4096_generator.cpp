// 初期速度ベクトルに必要な方位角と天頂角(仰角)を生成するプログラム
// 3次元球面上における等方的な分布を保証するため，zetaはsin(zeta)が一様分布になるように計算
// 乱数生成方法はメルセンヌ・ツイスター法

#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numbers>
#include <random>
#include <string>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define RAD_TO_DEG(x) (x * 180.0 / M_PI)

int main() {
  const int NUM_SAMPLES = 4096;
  const unsigned int SEED = 42;
  const std::string OUTPUT_FILE = "data/angles_4096.csv";

  // 64bitメルセンヌ・ツイスター生成器
  std::mt19937_64 rng(SEED);

  // 方位角phi [0, pi] の乱数(ラジアンの出力)
  std::uniform_real_distribution<double> dist_phi(0.0, M_PI);

  // 仰角zeta [-1, 1] の乱数(u=sin(zeta)の出力)
  std::uniform_real_distribution<double> dist_u(-1.0, 1.0);

  // 出力ファイルの設定
  std::ofstream ofs(OUTPUT_FILE);
  if (!ofs) {
    std::cerr << "Error: Cannot open " << std::endl;
    return 1;
  }
  std::cout << "START 4096 PARAMETER genaration" << std::endl;

  ofs << "# id, phi[0/pi], zeta[-90/90]" << "\n";

  for (int id = 0; id < NUM_SAMPLES; id++) {
    double phi = dist_phi(rng);
    double u = dist_u(rng);
    double zeta = std::asin(u);

    // 桁数を明示的に書いた
    ofs << id << "," << std::fixed << std::setprecision(15) << phi << ","
        << zeta << "\n";
  }

  std::cout << "Successfully generated " << NUM_SAMPLES
            << " isotropic angles -> " << OUTPUT_FILE << std::endl;

  return 0;
}