"""
News Alpha: 基于 nws12_afterhsz_sl 的动量+反转策略
逻辑:
  1. vec_avg 聚合每日多值新闻情绪
  2. ts_sum/ts_mean 降噪
  3. rank > 0.5 识别多头优势股票
  4. 条件满足 -> 动量(做多=1)，不满足 -> 反转(-rank(价格变化))
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
    # 基础版: ts_sum(20天) + rank条件 + 动量/反转
    # 条件满足(正面新闻多) -> 做多(1)，不满足 -> 反转(-rank(close变化))
    ("news_mom_rev_20",
     "news = vec_avg(nws12_afterhsz_sl); "
     "signal = ts_sum(news, 20); "
     "rank(signal) > 0.5 ? 1 : -rank(ts_delta(close, 1))",
     s(decay=5, neut='SUBINDUSTRY')),

    # ts_mean 降噪版
    ("news_mom_rev_mean20",
     "news = vec_avg(nws12_afterhsz_sl); "
     "signal = ts_mean(news, 20); "
     "rank(signal) > 0.5 ? 1 : -rank(ts_delta(close, 1))",
     s(decay=5, neut='SUBINDUSTRY')),

    # 更长窗口 60天
    ("news_mom_rev_60",
     "news = vec_avg(nws12_afterhsz_sl); "
     "signal = ts_sum(news, 60); "
     "rank(signal) > 0.5 ? 1 : -rank(ts_delta(close, 1))",
     s(decay=5, neut='SUBINDUSTRY')),

    # 反转信号用 ts_delta(close, 2) 更稳定
    ("news_mom_rev_delta2",
     "news = vec_avg(nws12_afterhsz_sl); "
     "signal = ts_sum(news, 20); "
     "rank(signal) > 0.5 ? 1 : -rank(ts_delta(close, 2))",
     s(decay=5, neut='SUBINDUSTRY')),

    # 平衡多空规模: 动量用 rank(signal)，反转用 -rank(close变化)
    ("news_balanced",
     "news = vec_avg(nws12_afterhsz_sl); "
     "signal = ts_sum(news, 20); "
     "rank(signal) > 0.5 ? rank(signal) : -rank(ts_delta(close, 1))",
     s(decay=5, neut='SUBINDUSTRY')),

    # ts_backfill 处理缺失值后再降噪
    ("news_backfill_sum",
     "news = ts_backfill(vec_avg(nws12_afterhsz_sl), 5); "
     "signal = ts_sum(news, 20); "
     "rank(signal) > 0.5 ? 1 : -rank(ts_delta(close, 1))",
     s(decay=5, neut='SUBINDUSTRY')),

    # group_zscore 增强分组效果
    ("news_group_cond",
     "news = ts_backfill(vec_avg(nws12_afterhsz_sl), 5); "
     "signal = group_zscore(ts_sum(news, 20), subindustry); "
     "signal > 0 ? 1 : -rank(ts_delta(close, 1))",
     s(decay=5, neut='MARKET')),

    # 阈值调整为 0.7 (更严格的多头条件)
    ("news_strict_07",
     "news = vec_avg(nws12_afterhsz_sl); "
     "signal = ts_sum(news, 20); "
     "rank(signal) > 0.7 ? 1 : -rank(ts_delta(close, 1))",
     s(decay=5, neut='SUBINDUSTRY')),
]

if __name__ == '__main__':
    run_backtest("news_momentum_reversion", alphas)
