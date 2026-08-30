# コンパイラとフラグ設定
CXX      := g++
CXXFLAGS := -O3 -std=c++17 -Wall -Wextra -MMD -MP

# ディレクトリ設定
SRC_DIR   := src
TOOLS_DIR := tools
BUILD_DIR := build
BIN_DIR   := bin
DATA_DIR  := data

# ターゲットバイナリ
TARGET     := $(BIN_DIR)/simulation
GEN_TARGET := $(BIN_DIR)/parameter4096_generator

# ソースファイル、オブジェクトファイル、依存関係ファイルの取得（シミュレーション本体）
SRCS := $(wildcard $(SRC_DIR)/*.cpp)
OBJS := $(patsubst $(SRC_DIR)/%.cpp, $(BUILD_DIR)/%.o, $(SRCS))
DEPS := $(OBJS:.o=.d)

# デフォルトターゲット
all: $(TARGET) $(GEN_TARGET)

# シミュレーション本体のリンク
$(TARGET): $(OBJS) | $(BIN_DIR)
	$(CXX) $(CXXFLAGS) -o $@ $^

# 各.cppのコンパイル（src/）
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -I$(SRC_DIR) -c $< -o $@

# パラメータ生成ツールのビルド（tools/）
$(GEN_TARGET): $(TOOLS_DIR)/parameter4096_generator.cpp | $(BIN_DIR)
	$(CXX) $(CXXFLAGS) -I$(SRC_DIR) $< -o $@

# サンプリング実行ターゲット（ビルド後に即実行）
sampling: $(GEN_TARGET) | $(DATA_DIR)
	./$(GEN_TARGET)

# 自動生成された依存関係ファイルを読み込む
-include $(DEPS)

# ディレクトリ作成
$(BUILD_DIR) $(BIN_DIR) $(DATA_DIR):
	mkdir -p $@

# 生成物の削除
clean:
	rm -rf $(BUILD_DIR) $(BIN_DIR)

# シミュレーション本体のビルドして実行
run: $(TARGET)
	./$(TARGET)

.PHONY: all clean run sampling