# WorldQuant Brain 指标优化指南

> 来源：https://support.worldquantbrain.com

---

## How to improve Sharpe

IR = Return / standard_deviation(Return)

基于此公式，有两种方式提高 IR：

1. 提高 Alpha 收益（Return）
2. 降低波动率（Volatility），例如使用 neutralization 设置和 group 算子

### 要点

- 不要仅通过调整参数来提高 Sharpe，Alpha 应从数学和经济角度都合乎逻辑
- 达到最低 Sharpe 和 Fitness 阈值后，应更关注收益（Returns）。Sharpe 和 Fitness 阈值的存在是为了区分 alpha 信号与噪声，达标后应将模拟收益作为重点
- 在 BRAIN 上投入越多，掌握的信号优化技巧就越多。建议初学者多花时间在 Learn 板块和 Community 论坛上，从其他有经验的研究员那里获取洞见

---

## How to improve Returns

BookSize 在 BRAIN 上假设为 $20 Mn。

### 提高 Alpha 收益的方法

- 提高换手率（Turnover）— 更高的换手率意味着更多交易，潜在收益更高
- 在 Alpha 设置中使用较低的 decay 值
- 在 Alpha 设置中选择流动性更好（更小）的 universe
- 在保持收益和回撤水平不变的情况下，提高 Alpha 的波动率可能获得更高收益
- 尝试使用 news 和 analyst 数据集，它们可能有潜力生成高收益的 Alpha

---

## How to improve Turnover

### 什么是 Turnover？

Turnover 表示 Alpha 模拟交易的频率。定义为交易价值与账面规模的比率：

Daily Turnover = Dollar trading volume / Booksize

好的 Alpha 通常换手率较低，因为低换手率意味着更低的交易成本。

### Turnover 必须低于 40% 才能被评估吗？

不是必须的，但建议如此。高换手率的 Alpha 在真实交易中可能难以执行（交易成本高）。建议关注 Sharpe > 2.5 且 Turnover < 40% 的 Alpha，同时持续尝试新想法。

### 降低 Turnover 的方法

- 使用 Decay 设置 — 如果 Alpha 变化很快，设置 decay = N 天会将 Alpha 在 N 天内平均化，降低日换手率（但性能可能显著变化）
- 对 Alpha 使用 `rank` 函数
- 使用 `trade_when` 算子
- 使用 `hump` 算子实现阈值控制

### 提高 Turnover 的方法

- 使用较低的 Decay 设置值
- 在 Alpha 设置中选择流动性更好（更小）的 universe
- 在时间序列和截面算子中使用较短的时间周期（如用 20 天代替 200 天）
- 使用更新频率较高的数据集类别（如 news、sentiment），这也有助于创建具有高 value score 的独特 Alpha

---

## How to reduce Correlation

这是许多研究员在 alpha 研究中面临的常见问题。可以通过以下方式测试 Alpha 表达式的不同变体：

- 使用不同的数据字段 — 尝试用等价字段替换，如用 `high`、`low`、`open` 替代 `close`
- 使用不同的算子 — 从实践中相似的算子开始，建立自己的相似性库以进一步降低最大相关性。例如用 `median` 替代 `mean`，用 `zscore` 替代 `rank` 等
- 使用不同的分组和中性化 — 这是一种强大的方法，但不要仅为降低相关性而创建任意分组
- 跳出思维定式（Think outside of the box）— 这是最好的方式，也是真正的研究

---

## How to smooth the PnL curve

### PnL 突然跳变的原因

1. Alpha 值频繁在 NaN 和非 NaN 之间切换 — 使用 `backfill` 函数处理
2. Alpha 值时不时剧烈变化 — 使用 decay 或在 Alpha 公式中取平均值使曲线更平滑
3. 单只股票权重过大，股价跳变导致 PnL 跳变 — 在 sim 设置中将 Truncation（股票权重）设为 0 到 1 之间的非零值，建议小于 0.1

### 为什么会出现性能下降（dips）？

- Alpha 频繁表现不佳时，未来风险可能更大
- PnL 图表在某几年持续下降是 Alpha 稳健性和 OS 表现的警告信号
- 下降原因可能是：
  - 随机噪声或过拟合
  - Alpha 被太多量化研究员使用，导致失效
  - 重大事件（如 2020 年 COVID-19 崩盘）影响不够稳健的 Alpha
- 如果 Alpha 在样本内（IS）期间表现不佳，通常不建议使用。这也是 IS-ladder test 作为 consultant 提交测试之一的原因

### 如何改善样本内期间的 dips？

核心思路：消除与主要 Alpha 想法无关的风险。

例如：如果你想给高 ROE 的股票更高权重，但 ROE 因行业而异（互联网公司 ROE 可能高于制造业），那么互联网行业下跌可能严重影响你的 Alpha。中性化这些风险可以消除时段性的差表现。

### 中性化方法

- 设置中的 Neutralization 选项
  - 除了 Market 到 Subindustry 中性化，还可尝试 Slow factors 和 Fast factors
- 中性化算子
  - `group_neutralize`、`group_rank`、`group_zscore`
  - `vector_neut`
  - `regression_neut`
  - `ts_vector_neut`

### 其他 dips/spikes 问题

- 如果 turnover 图表出现短期尖峰，可能是使用了低覆盖率的数据字段
- 低覆盖率数据字段在某些时间戳缺少数据时，Alpha 会改变所有持仓，导致覆盖率大幅下降，可能无法通过 concentrated weight test
- 解决方法：使用填充算子如 `ts_backfill` 或 `group_backfill` 来降低 turnover 尖峰并防止低覆盖率

---

## How to increase Fitness

Fitness = Sharpe × sqrt(abs(Returns) / Max(Turnover, 0.125))

因此，提高 Fitness 的方法：

- 提高 Returns（参见 Returns 章节）
- 提高 Sharpe（参见 Sharpe 章节）
- 降低 Turnover（参见 Turnover 章节）

### 相关资源

- 提高收益：使用 trade_when 处理事件型 Alpha 和低换手率 Alpha
- 提高 Alpha 容量（capacity）
- 合理使用 Decay 设置

---

## How to improve Margin

Margin 是每交易一美元的利润，计算方式为：Margin = PnL / 总交易金额（给定期间）。

提高 Margin 的方法：

- 提高收益（Returns）
- 管理换手率（Turnover）

---

## Weight Coverage 常见问题与建议

### Weight Test

Weight test 衡量 Alpha 中单只股票的资金集中度。BRAIN 中限制为总账面规模的 10%。该测试对于限制股价波动（尤其是 Out-of-Sample）带来的回撤风险非常重要。

- 在设置中使用较低的 truncation 值。BRAIN 提供 truncation 来控制 Alpha 模拟中的股票权重集中度，值 0.1 表示截断限制为账面规模的 10%

### Coverage

导致 weight test 失败的主要因素之一是覆盖率。例如，如果模拟中任意时刻多头或空头的股票数量少于 10，或总股票数少于 20。低覆盖率和/或多空数量不平衡的 Alpha 通常会无法通过 weight test。

### 处理低覆盖率的方法

- 使用可视化工具检测覆盖率的异常变化。注意模拟开始时的低覆盖率，最好移除覆盖率低于最终股票数 60% 的初始期间
- `group_count(is_nan(a), market) > 40 ? a : nan` — 检测因短期数据缺失导致的异常计数下降
- `ts_backfill(a, 2)` — 处理缺失一天的数据，适用于不频繁更新的数据（如基本面数据）
- `ts_backfill(a, 60)` — 处理按季度更新的基本面数据
- 也可以用 `is_nan()`、`last_diff_value()`、`days_from_last_change()` 检测 NaN 值并自行回填
- 发挥创造力，合理的填充技巧可能产生新的 Alpha

### Alpha 幅度分布

并非所有 weight test 失败都源于覆盖率问题。另一个主要因素是 Alpha 想法严重依赖数据分布。当数据分布广泛、存在异常值或数据错误时，会出现权重问题。

减少异常值的方法：

- truncation 设置通常对偶发异常值有帮助，但不保证有效
- 使用 `rank`（或 `group_rank`）函数改变数据分布
- 范围归一化函数如 `rank`、`log`、`scale`、`zscore` 也有帮助
- `rank` 旨在平衡多空数量，使数据分布呈均匀分布。确保理解并控制数据范围，在处理数据前先归一化是好习惯

### 额外注意事项

- 不要过度使用大回溯天数的 backfill 函数，可能损害性能
- 使用可视化工具理解数据，选择合适的回溯天数
- `rank` 是 robust test（rank test）的一部分，使用 rank 函数的 Alpha 更容易通过 rank test
- 如果尝试了所有方法仍无法通过 weight test，建议转向新的想法。虽然想法可能不错，但不一定能以通过 weight test 的方式表达，而创建能通过 weight test 的新 Alpha 的机会始终存在
