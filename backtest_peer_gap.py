"""
5-Day Peer vs Stock Performance Gap 因子回测
假设: 如果同行业公司表现远超该股票，该股票可能是短期滞后者，有望均值回归反弹
数据源:
  - rel_ret_all: 同行群体相对收益 (peer group relative return)
  - returns: 个股原始收益 (stock raw return)
实现:
  - 计算5日累计相对收益: (1+ts_delay(rel_ret_all,4))*(1+ts_delay(rel_ret_all,3))*...*(1+ts_delay(rel_ret_all,1))
  - 计算5日累计收益: (1+ts_delay(returns,4))*(1+ts_delay(returns,3))*...*(1+ts_delay(returns,1))
  - Gap = cum_rel_return - cum_return
  - 当 Gap 显著时 (peer >> stock) → 做多股票 (均值回归)
提示: 使用 trade_when 仅在 Gap 显著时交易，避免 Gap 较小且波动时过度交易
"""
from backtest import run_backtest


def s(decay=0, neut='SECTOR', trunc=0.08):
    """默认设置: 参照截图 Simulation Settings"""
    return {
        'instrumentType': 'EQUITY', 'region': 'USA', 'universe': 'TOP3000',
        'delay': 1, 'decay': decay, 'neutralization': neut, 'truncation': trunc,
        'pasteurization': 'ON', 'unitHandling': 'VERIFY', 'nanHandling': 'ON',
        'language': 'FASTEXPR', 'visualization': False,
    }


# 基础累积收益表达式 (5日)
CUM_REL = "(1+ts_delay(rel_ret_all,4))*(1+ts_delay(rel_ret_all,3))*(1+ts_delay(rel_ret_all,2))*(1+ts_delay(rel_ret_all,1))"
CUM_RET = "(1+ts_delay(returns,4))*(1+ts_delay(returns,3))*(1+ts_delay(returns,2))*(1+ts_delay(returns,1))"
GAP = f"{CUM_REL} - {CUM_RET}"

alphas = [

    # ===== 基础 Gap =====

    # 1. 原始 Gap — peer 跑赢股票越多，股票越可能均值回归
    ("gap_raw",
     GAP,
     s(decay=3, neut='SECTOR')),

    # 2. Gap 排名 — 标准化信号
    ("gap_rank",
     f"rank({GAP})",
     s(decay=3, neut='SECTOR')),

    # 3. Gap zscore — 标准化后更稳定
    ("gap_zscore",
     f"ts_zscore({GAP}, 60)",
     s(decay=5, neut='SECTOR')),

    # ===== trade_when 条件过滤 (解决提示中的过度交易问题) =====

    # 4. Gap 显著为正时做多 (peer >> stock → 均值回归)
    ("gap_trade_when",
     f"trade_when({GAP} > 0.02, 1, 0)",
     s(decay=3, neut='SECTOR')),

    # 5. Gap 显著时用排名信号，不显著时持有现金
    ("gap_rank_trade_when",
     f"trade_when(abs({GAP}) > 0.02, rank({GAP}), 0)",
     s(decay=3, neut='SECTOR')),

    # 6. Gap 阈值自适应 — 使用 ts_rank 判断显著性
    ("gap_rank_threshold",
     f"trade_when(ts_rank(abs({GAP}), 60) > 0.7, rank({GAP}), 0)",
     s(decay=3, neut='SECTOR')),

    # ===== Gap 趋势 =====

    # 7. Gap 趋势斜率 — Gap 扩大中做多 (滞后期加深)
    ("gap_slope",
     f"slope = ts_regression({GAP}, ts_step(1), 20, rettype=2); rank(slope)",
     s(decay=3, neut='SECTOR')),

    # 8. Gap 动量 — 近期 Gap 相对长期 Gap 的变化
    ("gap_momentum",
     f"rank(ts_mean({GAP}, 5) - ts_mean({GAP}, 20))",
     s(decay=3, neut='SECTOR')),

    # ===== 加权累积收益 =====

    # 9. 衰减加权 — 近期权重更高
    ("gap_decay_weighted",
     f"weighted_rel = (1+ts_delay(rel_ret_all,1))*decay_linear(1,4) + "
     f"(1+ts_delay(rel_ret_all,2))*decay_linear(2,4) + "
     f"(1+ts_delay(rel_ret_all,3))*decay_linear(3,4) + "
     f"(1+ts_delay(rel_ret_all,4))*decay_linear(4,4); "
     f"weighted_ret = (1+ts_delay(returns,1))*decay_linear(1,4) + "
     f"(1+ts_delay(returns,2))*decay_linear(2,4) + "
     f"(1+ts_delay(returns,3))*decay_linear(3,4) + "
     f"(1+ts_delay(returns,4))*decay_linear(4,4); "
     f"rank(weighted_rel - weighted_ret)",
     s(decay=3, neut='SECTOR')),

    # ===== Gap 残差分析 =====

    # 10. Gap 与成交量的回归残差 — 剔除量能影响后的纯 Gap
    ("gap_vol_resid",
     f"gap = {GAP}; -ts_regression(gap, log(volume), 60, rettype=0)",
     s(decay=5, neut='SECTOR')),

    # 11. Gap 与波动率回归残差
    ("gap_volatility_resid",
     f"gap = {GAP}; -ts_regression(gap, ts_std_dev(returns, 20), 60, rettype=0)",
     s(decay=5, neut='SECTOR')),

    # ===== 行业中性化 =====

    # 12. Group zscore — 行业内相对 Gap
    ("gap_group_zscore",
     f"group_zscore({GAP}, sector)",
     s(decay=5, neut='MARKET')),

    # 13. 行业内排名
    ("gap_sector_rank",
     f"group_rank({GAP}, sector)",
     s(decay=3, neut='MARKET')),

    # ===== 反转/动量组合 =====

    # 14. 条件策略 — Gap 正时做多，负时做空
    ("gap_conditional",
     f"({GAP}) > 0 ? rank(-ts_delta(close, 2)) : rank(ts_delta(close, 2))",
     s(decay=3, neut='SECTOR')),

    # 15. Gap + 价格动量组合
    ("gap_price_momentum",
     f"rank({GAP}) * rank(-ts_delta(close, 5))",
     s(decay=5, neut='SECTOR')),

    # 16. 极端 Gap 反转 — Gap 过高意味着过度偏离，可能反转
    ("gap_extreme_reversion",
     f"high_gap = ts_rank({GAP}, 60) > 0.8; "
     f"trade_when(high_gap, -rank(ts_delta(close, 3)), -1)",
     s(decay=3, neut='SECTOR', trunc=0.01)),

    # ===== 不同时间窗口 =====

    # 17. 更短窗口 (3日)
    ("gap_3d",
     f"(1+ts_delay(rel_ret_all,2))*(1+ts_delay(rel_ret_all,1))"
     f" - (1+ts_delay(returns,2))*(1+ts_delay(returns,1))",
     s(decay=2, neut='SECTOR')),

    # 18. 更长窗口 (10日)
    ("gap_10d",
     f"(1+ts_delay(rel_ret_all,9))*(1+ts_delay(rel_ret_all,8))*"
     f"(1+ts_delay(rel_ret_all,7))*(1+ts_delay(rel_ret_all,6))*"
     f"(1+ts_delay(rel_ret_all,5))*(1+ts_delay(rel_ret_all,4))*"
     f"(1+ts_delay(rel_ret_all,3))*(1+ts_delay(rel_ret_all,2))*"
     f"(1+ts_delay(rel_ret_all,1))"
     f" - "
     f"(1+ts_delay(returns,9))*(1+ts_delay(returns,8))*"
     f"(1+ts_delay(returns,7))*(1+ts_delay(returns,6))*"
     f"(1+ts_delay(returns,5))*(1+ts_delay(returns,4))*"
     f"(1+ts_delay(returns,3))*(1+ts_delay(returns,2))*"
     f"(1+ts_delay(returns,1))",
     s(decay=5, neut='SECTOR')),

    # ===== 不同参数变体 =====

    # 19. 不同衰减系数
    ("gap_rank_d5",
     f"rank({GAP})",
     s(decay=5, neut='SECTOR')),

    # 20. 不同中性化
    ("gap_rank_subindustry",
     f"rank({GAP})",
     s(decay=3, neut='SUBINDUSTRY')),
]

if __name__ == '__main__':
    run_backtest("peer_gap", alphas)
