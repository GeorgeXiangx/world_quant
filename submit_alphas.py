"""
基于官方文档示例和 WQ-Brain 项目，生成并回测可提交的 Alpha
使用 backtest.py 框架
"""
from backtest import run_backtest


def s(decay=0, neut='SUBINDUSTRY', trunc=0.08):
    return {
        'instrumentType': 'EQUITY', 'region': 'USA', 'universe': 'TOP3000',
        'delay': 1, 'decay': decay, 'neutralization': neut, 'truncation': trunc,
        'pasteurization': 'ON', 'unitHandling': 'VERIFY', 'nanHandling': 'ON',
        'language': 'FASTEXPR', 'visualization': False,
    }


alphas = [
    # 价格反转
    ("VWAP反转", "group_zscore(ts_zscore(vwap/close, 250), subindustry)", s(decay=5, trunc=0.01)),
    ("K线反转", "group_zscore(-(close - open) / (high - low + 0.001), subindustry)", s(decay=3)),
    ("均值回归5日", "-(close - ts_mean(close, 5))", s(decay=5)),

    # 成交量
    ("量价背离", "-ts_corr(ts_rank(volume, 10), ts_rank(vwap, 10), 20)", s(decay=3, trunc=0.1)),

    # 回归
    ("波动率条件回归", "when = ts_rank(ts_std_dev(returns, 22), 252) > 0.55; trade_when(when, -ts_regression(returns, ts_delay(returns,1), 252), -1)", s(decay=3, trunc=0.01)),

    # 基本面
    ("ROE排名", "ts_rank(operating_income/cap, 252)", s(decay=5, trunc=0.01)),
    ("group_rank_OEY", "group_rank(ts_rank(operating_income/cap, 252), subindustry)", s(decay=5, trunc=0.01)),
    ("EV/EBITDA反转", "-ts_zscore(enterprise_value / ebitda, 63)", s(decay=5, neut='INDUSTRY', trunc=0.01)),

    # 复合策略
    ("动量+量确认", "(ts_mean(volume,20) < volume) ? (-1 * ts_rank(abs(ts_delta(close, 7)), 60) * sign(ts_delta(close, 7))) : -1", s(decay=3)),
    ("多因子收益量", "rank(scale(ts_sum(-returns, 5)) + scale(ts_decay_linear(volume/(ts_sum(volume,20)/20), 5)))", s(decay=5)),
    ("布林带", "avg = (high + low + close + open) / 4; ma = ts_mean(avg, 20); bolu = ma + ts_std_dev(avg, 20); bold = ma - ts_std_dev(avg, 20); signal = ts_sum(close < bold, 20) - ts_sum(close > bolu, 20); ts_zscore(signal, 240)", s(decay=3)),
    ("OEY+动量", "ts_rank(operating_income/cap, 252) * rank(-ts_delta(close, 5))", s(decay=5, trunc=0.01)),

    # 协方差/回归
    ("协方差", "rank(ts_covariance(ts_std_dev(-returns, 22), (vwap - close), 22))", s(decay=5)),
    ("衰减中性化", "group_neutralize(ts_decay_linear(ts_delta(close, 5), 10), subindustry)", s(decay=3, neut='MARKET')),
]

if __name__ == '__main__':
    run_backtest("alpha_candidates", alphas)
