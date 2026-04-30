"""
优化指定 Alpha 表达式
使用 backtest.py 框架
"""
from backtest import run_backtest


def s(decay=0, neut='MARKET', trunc=0.08):
    return {
        'instrumentType': 'EQUITY', 'region': 'USA', 'universe': 'TOP3000',
        'delay': 1, 'decay': decay, 'neutralization': neut, 'truncation': trunc,
        'pasteurization': 'ON', 'unitHandling': 'VERIFY', 'nanHandling': 'ON',
        'language': 'FASTEXPR', 'visualization': False,
    }


# 原始表达式优化
original = ("slope = ts_regression(ts_backfill(news_pct_1min,60), ts_step(1), 5, rettype=2);"
            "winsorize(-ts_backfill(news_max_up_ret,60) * abs(slope), std=4)")

alphas = [
    ("基线", original, s()),
    ("decay=3", original, s(decay=3)),
    ("neut=SUBINDUSTRY", original, s(neut='SUBINDUSTRY')),
    ("SUBIND+decay=3", original, s(decay=3, neut='SUBINDUSTRY')),
    ("group_neutralize",
     "slope = ts_regression(ts_backfill(news_pct_1min,60), ts_step(1), 5, rettype=2);"
     "group_neutralize(winsorize(-ts_backfill(news_max_up_ret,60) * abs(slope), std=4), subindustry)",
     s()),
    ("group_zscore",
     "slope = ts_regression(ts_backfill(news_pct_1min,60), ts_step(1), 5, rettype=2);"
     "group_zscore(winsorize(-ts_backfill(news_max_up_ret,60) * abs(slope), std=4), subindustry)",
     s()),
]

if __name__ == '__main__':
    run_backtest("news_alpha_optimize", alphas)
