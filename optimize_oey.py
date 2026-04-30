"""
Operating Earnings Yield Alpha 优化
使用 backtest.py 框架
"""
from backtest import run_backtest


def s(decay=5, neut='SUBINDUSTRY', trunc=0.01):
    return {
        'instrumentType': 'EQUITY', 'region': 'USA', 'universe': 'TOP3000',
        'delay': 1, 'decay': decay, 'neutralization': neut, 'truncation': trunc,
        'pasteurization': 'ON', 'unitHandling': 'VERIFY', 'nanHandling': 'ON',
        'language': 'FASTEXPR', 'visualization': False,
    }


alphas = [
    ("基础OEY", "ts_rank(operating_income/cap, 252)", s(decay=5)),
    ("OEY-126天", "ts_rank(operating_income/cap, 126)", s(decay=5)),
    ("OEY-500天", "ts_rank(operating_income/cap, 500)", s(decay=5)),
    ("OI/assets", "ts_rank(operating_income/assets, 252)", s(decay=5)),
    ("OI/equity", "ts_rank(operating_income/equity, 252)", s(decay=5)),
    ("group_zscore_OEY", "group_zscore(ts_rank(operating_income/cap, 252), subindustry)", s(decay=5)),
    ("group_rank_OEY", "group_rank(ts_rank(operating_income/cap, 252), subindustry)", s(decay=5)),
    ("ts_zscore_OEY", "ts_zscore(operating_income/cap, 252)", s(decay=5)),
    ("OEY-decay=0", "ts_rank(operating_income/cap, 252)", s(decay=0)),
    ("OEY-decay=10", "ts_rank(operating_income/cap, 252)", s(decay=10)),
    ("OEY+动量", "ts_rank(operating_income/cap, 252) * rank(-ts_delta(close, 5))", s(decay=5)),
    ("OEY+低波动", "ts_rank(operating_income/cap, 252) * rank(-ts_std_dev(returns, 22))", s(decay=5)),
]

if __name__ == '__main__':
    run_backtest("oey_optimize", alphas)
