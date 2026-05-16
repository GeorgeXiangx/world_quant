---
name: improve-alpha-metrics
description: Diagnose and fix WorldQuant Brain Alpha factor performance issues. Use when a factor's metrics (Sharpe, Returns, Turnover, Fitness, Margin, Weight Test, Coverage, PnL, Correlation) need improvement, or when the user reports failed checks or asks how to optimize alpha factors.
---

# 因子指标优化

## 工作流程

当用户给出一个因子回测结果或询问如何优化时，按以下步骤处理：

### Step 1: 诊断问题

根据用户提供的信息定位问题指标：

| 症状 | 诊断方向 |
|------|---------|
| Sharpe < 阈值 | 收益过低或波动过大 |
| Returns 太低 | 换手不够、decay 太高、universe 太大 |
| Turnover > 40% | 信号变化过快，需平滑 |
| Turnover 太低 | 信号变化太慢，需提速 |
| Fitness 不达标 | Sharpe × sqrt(Returns/Turnover) — 三项综合问题 |
| Weight Test FAIL | 权重集中 > 10% — 分布或覆盖率问题 |
| Coverage 低 | 数据缺失、多空不平衡 |
| PnL 剧烈跳变 | NaN 切换、极端值、单票权重过大 |
| Correlation 太高 | 与已有因子雷同 |
| Margin 低 | PnL/交易量比低 — 收益或换手率问题 |

### Step 2: 针对性优化

根据诊断结果，参考下方速查表给出具体修改建议（表达式中改算子 / settings 中改参数）。

### Step 3: 输出修改后的完整因子

给出修改后的表达式 + settings JSON，确保用户可直接提交。

---

## 速查表

### Sharpe 优化

| 手段 | 操作 |
|------|------|
| 提收益 | 降 decay、缩小 universe、提高换手（见 Returns 优化） |
| 降波动 | 加 `group_neutralize`、`group_rank`、`group_zscore`；设置中性化为 SUBINDUSTRY |
| 核心原则 | 不做纯参数调优，确保信号有经济学逻辑 |

### Returns 优化

| 手段 | 操作 |
|------|------|
| 提高换手 | 降 decay（0~2），用更短时间窗口的算子（20d 替代 200d） |
| 缩小 universe | TOP3000 → TOP500 或更小 |
| 换数据集 | 改用 news、sentiment、analyst 类高频数据集 |

### Turnover 优化

**降低换手（目标 < 40%）：**

| 手段 | 操作 |
|------|------|
| 提高 decay | 设 decay = 3~10，对信号做 N 日均化 |
| 加 rank | 表达式外层包 `rank` 或 `group_rank`，均匀化分布减缓变化 |
| 阈值控制 | 用 `hump` 或 `trade_when` 过滤弱信号 |
| 加 backfill | `ts_backfill(a, N)` 避免 NaN 导致持仓突然翻转 |

**提高换手：**

| 手段 | 操作 |
|------|------|
| 降 decay | 设 decay = 0~1 |
| 缩小 universe | TOP500 → TOP200 |
| 缩短周期 | ts_ops 用 10d/20d 替代 120d |

### Weight Test 修复

| 根因 | 解法 |
|------|------|
| 因子分布太宽（有极端值） | `winsorize(expr, std=4)` 截尾；外层包 `group_rank` 使分布均匀 |
| 覆盖率低 | `ts_backfill(expr, 60)` 填补季度数据；`ts_backfill(expr, 2)` 填补日度缺失 |
| 多空不平衡 | `group_rank` 天然平衡多空数量 |
| 特定日期缺失 > 40% | `group_count(is_nan(expr), market) > 40 ? expr : nan` 过滤 |
| 仍无法通过 | 降 truncation 到 0.05；若仍失败，换 idea |

**黄金法则**：`rank`/`group_rank` 是修复 Weight Test 的最强工具。

### Coverage 修复

| 手段 | 操作 |
|------|------|
| 短期缺失（1天） | `ts_backfill(expr, 2)` |
| 季度更新数据 | `ts_backfill(expr, 60)` |
| 检测异常缺失 | `group_count(is_nan(expr), market) > 40 ? expr : nan` |
| 自定义填充 | `is_nan()` + `last_diff_value()` + `days_from_last_change()` |

### PnL 平滑

| 问题 | 解法 |
|------|------|
| NaN 频繁切换 | `ts_backfill(expr, N)` |
| 值剧烈变化 | 设 decay > 0；对表达式取均值 |
| 单票权重过大 → PnL 跳 | truncation 设 < 0.1（如 0.05~0.08） |
| IS 期间持续下降 | 中性化：加 `group_neutralize` 或设 neutralization=SUBINDUSTRY |
| Turnover 尖峰 | 用 `ts_backfill` 避免低覆盖率数据字段引发持仓翻转 |

### Fitness 优化

公式：`Fitness = Sharpe × sqrt(abs(Returns) / max(Turnover, 0.125))`

因此提高 Fitness 就是：提高 Sharpe + 提高 Returns + 降低 Turnover（至少 > 12.5%）。

### Correlation 降低

| 手段 | 操作 |
|------|------|
| 换数据字段 | `close` → `high`/`low`/`open`/`vwap` |
| 换算子 | `mean`→`median`，`rank`→`zscore`，`sum`→`ewma` |
| 换分组/中性化 | 改 neutralization 或 group 参数（market → sector → industry） |
| 根本方法 | 想一个真正不同的 idea，而非微调现有表达式 |

---

## 通用原则

1. **先归一化再操作**：处理数据前用 `winsorize` 或 `rank` 控制范围
2. **不过度 backfill**：大回溯天数损害性能，用可视化工具选合适天数
3. **rank 三赢**：同时改善 Turnover + Weight Test + Robust Test
4. **达标后关注 Returns**：Sharpe/Fitness 过阈值后，模拟收益是最终考核
5. **修不好就放弃**：好的 idea 不一定能用通过 weight test 的方式表达，换一个

## 参考

详细技术说明见 [reference.md](reference.md)
