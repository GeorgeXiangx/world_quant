"""
101 Formulaic Alphas #1-#10 回测
将论文公式转换为 Brain 平台 FASTEXPR 语法
"""
from backtest import run_backtest


def s(decay=6, neut='SUBINDUSTRY', trunc=0.08):
    return {
        'instrumentType': 'EQUITY', 'region': 'USA', 'universe': 'TOP3000',
        'delay': 1, 'decay': decay, 'neutralization': neut, 'truncation': trunc,
        'pasteurization': 'ON', 'unitHandling': 'VERIFY', 'nanHandling': 'ON',
        'language': 'FASTEXPR', 'visualization': False,
    }


# 论文 -> Brain 算子映射:
# correlation -> ts_corr, covariance -> ts_covariance, delay -> ts_delay
# delta -> ts_delta, sum -> ts_sum, stddev -> ts_std_dev
# product -> ts_product, decay_linear -> ts_decay_linear
# SignedPower -> signed_power, Ts_ArgMax -> ts_arg_max
# adv20 -> ts_mean(volume, 20)
# ts_min/ts_max 论文中有时写作 min/max(x,d)

alphas = [
    # Alpha#1: 波动率 vs 价格的 argmax 排名
    # 原始: (rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)
    ("Alpha#1",
     "(rank(ts_arg_max(signed_power(((returns < 0) ? ts_std_dev(returns, 20) : close), 2), 5)) - 0.5)",
     s(decay=6)),

    # Alpha#2: 成交量变化与价格变化的相关性
    # 原始: (-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6))
    ("Alpha#2",
     "(-1 * ts_corr(rank(ts_delta(log(volume), 2)), rank(((close - open) / open)), 6))",
     s(decay=6)),

    # Alpha#3: 开盘价与成交量排名的相关性
    # 原始: (-1 * correlation(rank(open), rank(volume), 10))
    ("Alpha#3",
     "(-1 * ts_corr(rank(open), rank(volume), 10))",
     s(decay=6)),

    # Alpha#4: 低价排名的时间序列排名
    # 原始: (-1 * Ts_Rank(rank(low), 9))
    ("Alpha#4",
     "(-1 * ts_rank(rank(low), 9))",
     s(decay=6)),

    # Alpha#5: 开盘偏离VWAP均值 * 收盘偏离VWAP
    # 原始: (rank((open - (sum(vwap, 10) / 10))) * (-1 * abs(rank((close - vwap)))))
    ("Alpha#5",
     "(rank((open - (ts_sum(vwap, 10) / 10))) * (-1 * abs(rank((close - vwap)))))",
     s(decay=6)),

    # Alpha#6: 开盘价与成交量的相关性
    # 原始: (-1 * correlation(open, volume, 10))
    ("Alpha#6",
     "(-1 * ts_corr(open, volume, 10))",
     s(decay=6)),

    # Alpha#7: 成交量放大时的价格动量
    # 原始: ((adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : (-1 * 1))
    ("Alpha#7",
     "((ts_mean(volume, 20) < volume) ? ((-1 * ts_rank(abs(ts_delta(close, 7)), 60)) * sign(ts_delta(close, 7))) : (-1 * 1))",
     s(decay=6)),

    # Alpha#8: 开盘*收益的动量变化
    # 原始: (-1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10))))
    ("Alpha#8",
     "(-1 * rank(((ts_sum(open, 5) * ts_sum(returns, 5)) - ts_delay((ts_sum(open, 5) * ts_sum(returns, 5)), 10))))",
     s(decay=6)),

    # Alpha#9: 价格变化方向的条件反转
    # 原始: ((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))
    ("Alpha#9",
     "((0 < ts_min(ts_delta(close, 1), 5)) ? ts_delta(close, 1) : ((ts_max(ts_delta(close, 1), 5) < 0) ? ts_delta(close, 1) : (-1 * ts_delta(close, 1))))",
     s(decay=6)),

    # Alpha#10: Alpha#9 的排名版本
    # 原始: rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))))
    ("Alpha#10",
     "rank(((0 < ts_min(ts_delta(close, 1), 4)) ? ts_delta(close, 1) : ((ts_max(ts_delta(close, 1), 4) < 0) ? ts_delta(close, 1) : (-1 * ts_delta(close, 1)))))",
     s(decay=6)),
]

if __name__ == '__main__':
    run_backtest("101alphas_1to10", alphas)
