"""
优化 -rank(equity/assets) 降低 Self-Correlation
原始: Self-correlation=0.9213, 需降至 < 0.7
策略:
1. 替换数据字段 (equity->book_value, assets->cap 等)
2. 替换算子 (rank->zscore, rank->group_rank, rank->ts_rank 等)
3. 改变分组/中性化
4. 增加时间序列维度
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
    # 0. 基线
    ("基线", "-rank(equity/assets)", s()),

    # === 策略1: 替换算子 (rank -> 其他) ===
    ("zscore替换rank", "-zscore(equity/assets)", s()),
    ("group_zscore", "-group_zscore(equity/assets, subindustry)", s(neut='MARKET')),
    ("group_rank", "-group_rank(equity/assets, subindustry)", s(neut='MARKET')),
    ("ts_zscore", "-ts_zscore(equity/assets, 252)", s()),
    ("ts_rank", "-ts_rank(equity/assets, 252)", s()),

    # === 策略2: 替换数据字段 ===
    ("book_value/assets", "-rank(book_value/assets)", s()),
    ("equity/cap", "-rank(equity/cap)", s()),
    ("equity/revenue", "-rank(equity/revenue)", s()),
    ("book_value/cap", "-rank(book_value/cap)", s()),

    # === 策略3: 增加时间序列维度 ===
    ("ts_delta变化", "-rank(ts_delta(equity/assets, 63))", s()),
    ("ts_rank+ratio", "-ts_rank(equity/assets, 126)", s()),
    ("ts_av_diff", "-rank(ts_av_diff(equity/assets, 252))", s()),

    # === 策略4: 改变中性化/分组 ===
    ("neut=INDUSTRY", "-rank(equity/assets)", s(neut='INDUSTRY')),
    ("neut=MARKET", "-rank(equity/assets)", s(neut='MARKET')),

    # === 策略5: 组合策略 ===
    ("group_zscore+ts", "-group_zscore(ts_rank(equity/assets, 252), subindustry)", s(neut='MARKET')),
    ("zscore+decay5", "-zscore(equity/assets)", s(decay=5)),
    ("ts_rank+group_rank", "-group_rank(ts_rank(equity/assets, 126), subindustry)", s(neut='MARKET')),

    # === 策略6: 用 high/low/open 替代 (思路: 加入价格维度降低相关性) ===
    ("equity/assets*价格", "-rank(equity/assets) * rank(close/open)", s()),
    ("ratio+动量", "-rank(equity/assets) * rank(-ts_delta(close, 5))", s()),
]

if __name__ == '__main__':
    run_backtest("equity_assets_decorr", alphas)
