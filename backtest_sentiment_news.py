"""
Sentiment & News Alpha 因子回测
数据源:
  - scl12_buzz: 社交媒体/新闻/博客/论坛情绪 buzz 指标 (vector)
  - nws12_afterhsz_sl: 盘后新闻情绪 (vector)
关键处理:
  - vector 数据需先用 vec_avg 转为 matrix
  - ts_backfill 处理缺失值
  - ts_regression 提取趋势斜率
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

    # ===== Sentiment: scl12_buzz =====

    # 1. 基础 buzz 均值 + 时间序列排名
    ("buzz_ts_rank",
     "rank(ts_sum(vec_avg(scl12_buzz), 60))",
     s(decay=5, neut='SUBINDUSTRY')),

    # 2. buzz 趋势斜率 (ts_regression rettype=2 返回斜率)
    ("buzz_slope",
     "slope = ts_regression(ts_backfill(vec_avg(scl12_buzz), 20), ts_step(1), 10, rettype=2); rank(slope)",
     s(decay=3, neut='SUBINDUSTRY')),

    # 3. buzz 相对于历史均值的偏离 (ts_av_diff)
    ("buzz_av_diff",
     "rank(ts_av_diff(ts_backfill(vec_avg(scl12_buzz), 20), 60))",
     s(decay=5, neut='SUBINDUSTRY')),

    # 4. buzz zscore — 标准化情绪信号
    ("buzz_zscore",
     "ts_zscore(ts_backfill(vec_avg(scl12_buzz), 20), 120)",
     s(decay=5, neut='SUBINDUSTRY')),

    # 5. buzz 与成交量的回归残差 — 剔除成交量影响后的纯情绪
    ("buzz_vol_resid",
     "buzz = ts_backfill(vec_avg(scl12_buzz), 20); -ts_regression(buzz, log(volume), 60, rettype=0)",
     s(decay=5, neut='SUBINDUSTRY')),

    # 6. buzz 条件策略 — buzz 高时做多，低时做空
    ("buzz_conditional",
     "buzz = ts_backfill(vec_avg(scl12_buzz), 20); (ts_rank(buzz, 60) > 0.5) ? rank(-ts_delta(close, 2)) : rank(ts_delta(close, 2))",
     s(decay=3, neut='SUBINDUSTRY')),

    # ===== News: nws12_afterhsz_sl =====

    # 7. 盘后新闻情绪均值 + 时间序列累积
    ("news_ts_sum",
     "rank(ts_sum(ts_backfill(vec_avg(nws12_afterhsz_sl), 20), 60))",
     s(decay=10, neut='SUBINDUSTRY')),

    # 8. 盘后新闻情绪斜率
    ("news_slope",
     "slope = ts_regression(ts_backfill(vec_avg(nws12_afterhsz_sl), 20), ts_step(1), 5, rettype=2); rank(slope)",
     s(decay=3, neut='SUBINDUSTRY')),

    # 9. 新闻情绪 zscore
    ("news_zscore",
     "ts_zscore(ts_backfill(vec_avg(nws12_afterhsz_sl), 20), 120)",
     s(decay=5, neut='SUBINDUSTRY')),

    # 10. 新闻情绪 + 价格动量组合
    ("news_momentum",
     "news = ts_backfill(vec_avg(nws12_afterhsz_sl), 20); rank(ts_sum(news, 60)) * rank(-ts_delta(close, 5))",
     s(decay=5, neut='SUBINDUSTRY')),

    # ===== Sentiment + News 组合 =====

    # 11. buzz + news 联合信号
    ("buzz_news_combined",
     "buzz = ts_backfill(vec_avg(scl12_buzz), 20); news = ts_backfill(vec_avg(nws12_afterhsz_sl), 20); rank(ts_sum(buzz, 30) + ts_sum(news, 30))",
     s(decay=5, neut='SUBINDUSTRY')),

    # 12. buzz 与 news 的相关性 — 两者一致时信号更强
    ("buzz_news_corr",
     "buzz = ts_backfill(vec_avg(scl12_buzz), 20); news = ts_backfill(vec_avg(nws12_afterhsz_sl), 20); rank(ts_corr(buzz, news, 20))",
     s(decay=5, neut='SUBINDUSTRY')),

    # 13. 情绪反转 — 高 buzz 后价格反转
    ("buzz_reversion",
     "buzz = ts_backfill(vec_avg(scl12_buzz), 20); high_buzz = ts_rank(buzz, 60) > 0.8; trade_when(high_buzz, -rank(ts_delta(close, 3)), -1)",
     s(decay=3, neut='SUBINDUSTRY', trunc=0.01)),

    # 14. 新闻情绪 + group_zscore 增强
    ("news_group_zscore",
     "news = ts_backfill(vec_avg(nws12_afterhsz_sl), 20); group_zscore(ts_sum(news, 60), subindustry)",
     s(decay=5, neut='MARKET')),

    # 15. buzz 动量 — 近期 buzz 相对长期 buzz 的变化
    ("buzz_momentum",
     "buzz = ts_backfill(vec_avg(scl12_buzz), 20); rank(ts_mean(buzz, 5) - ts_mean(buzz, 60))",
     s(decay=3, neut='SUBINDUSTRY')),
]

if __name__ == '__main__':
    run_backtest("sentiment_news", alphas)
