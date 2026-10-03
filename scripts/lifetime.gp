load "scripts/config.gp"
set datafile separator comma

binwidth = 2

bin(x,width) = width * (floor(x / width) + 0.5)

# ファイル名．引数を取ってv0の幅に対応
v0name = sprintf("v%03d", int(ARG1))
csvname = "result/gas-drag/out/" . v0name . ".csv"
outputname = "result/gas-drag/figures/lifetime/" . v0name . ".png"

# データ数の取得
stats csvname u (strcol(7) eq "C" ? $6 : 1/0) nooutput
N = STATS_records
print "N = ", N

set terminal pngcairo
set output outputname
set title "衛星生存時間のヒストグラム"
set xlabel "Lifetime [yr]"
set ylabel "Frequency(bin: 2 yr)"
set xrange [0:100]
set yrange [0:*]

set style fill solid 0.2
set boxwidth binwidth

plot csvname u (bin($6, binwidth)):(strcol(7) eq "C" ? 1.0/N : 0.0) skip 1 smooth frequency with boxes
