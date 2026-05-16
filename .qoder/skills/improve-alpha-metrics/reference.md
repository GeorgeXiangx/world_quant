# 详细技术说明

> 来源：WorldQuant Brain 官方支持文档

---

## Sharpe 优化

IR = Return / standard_deviation(Return)

两种方式提高 IR：
1. 提高 Alpha 收益（Return）
2. 降低波动率（Volatility），如使用 neutralization 设置和 group 算子

不要仅通过调整参数来提高 Sharpe，Alpha 应从数学和经济角度都合乎逻辑。达到最低 Sharpe 和 Fitness 阈值后应更关注 Returns。

---

## Returns 优化

BookSize 在 BRAIN 上假设为 $20 Mn。

- 提高换手率（Turnover）— 更高换手意味着更多交易，潜在收益更高
- 使用较低的 decay 值
- 选择流动性更好（更小）的 universe
- 保持收益和回撤不变时，提高 Alpha 波动率可能获得更高收益
- 尝试使用 news 和 analyst 数据集

---

## Turnover 优化

Turnover = Dollar trading volume / Booksize。好 Alpha 通常换手率较低（低交易成本）。

### 降低 Turnover

- 使用 Decay 设置：decay=N 天将信号 N 天平均化（可能显著改变性能）
- 对 Alpha 使用 `rank` 函数
- 使用 `trade_when` 算子
- 使用 `hump` 算子阈值控制

### 提高 Turnover

- 使用较低的 Decay 值
- 选择更小的 universe
- 在 ts/cs 算子中用更短周期（20d 替代 200d）
- 使用高更新频率数据集（news、sentiment）

---

## Correlation 降低

- 换数据字段：`high`、`low`、`open` 替代 `close`
- 换算子：`median` 替代 `mean`，`zscore` 替代 `rank`
- 换分组和中性化方式
- 跳出思维定式 — 创建真正独特的新 idea

---

## PnL 曲线平滑

### 跳变原因
1. Alpha 值频繁 NaN ↔ 非 NaN → 用 `backfill`
2. Alpha 值剧烈变化 → 用 decay 或取均值
3. 单票权重过大 → Truncation 设 < 0.1

### 性能下降（dips）原因
- 随机噪声或过拟合
- 太多研究员使用导致 Alpha 失效
- 重大事件（如 COVID-19）影响不够稳健的 Alpha

### 改善 dips 的方法
核心：消除与主要 Alpha 想法无关的风险。中性化这些风险可消除时段性差表现。

中性化手段：
- Settings: Neutralization（Market ~ Subindustry, Slow/Fast factors）
- 算子: `group_neutralize`、`group_rank`、`group_zscore`、`vector_neut`、`regression_neut`、`ts_vector_neut`

---

## Fitness 优化

Fitness = Sharpe × sqrt(abs(Returns) / Max(Turnover, 0.125))

提高方法：提 Returns + 提 Sharpe + 降 Turnover

---

## Margin 优化

Margin = PnL / 总交易金额

提高方法：提 Returns + 管理 Turnover

---

## Weight Test 与 Coverage

### Weight Test

衡量 Alpha 中单只股票的资金集中度，限制为总账面规模的 10%。防止股价波动带来的回撤风险。

### Coverage 问题

导致 weight test 失败的主要因素：模拟中任意时刻多/空头股票数 < 10，或总股票数 < 20。

### 处理低覆盖率

- 用可视化检测异常变化，移除覆盖率 < 60% 的初始期间
- `group_count(is_nan(a), market) > 40 ? a : nan` — 检测短期缺失
- `ts_backfill(a, 2)` — 补 1 天缺失
- `ts_backfill(a, 60)` — 补季度更新数据
- `is_nan()` + `last_diff_value()` + `days_from_last_change()` 自定义填充

### Alpha 幅度分布

另一主要因素：数据分布广泛、有异常值。减少方法：

- truncation 设置（对偶发异常值有帮助但不保证）
- `rank` 或 `group_rank` 改变分布为均匀分布
- `log`、`scale`、`zscore` 范围归一化

### 额外注意

- 不要过度使用大回溯天数的 backfill
- 用可视化工具选合适回溯天数
- rank 是 robust test 的一部分，有 rank 的 Alpha 更容易通过
- 修不好就放弃，换 idea
