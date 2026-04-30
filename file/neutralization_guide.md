# WorldQuant Brain 中性化设置指南

> 来源：https://platform.worldquantbrain.com/learn/documentation/advanced-topics/neut-cons

---

## I. 基础中性化

中性化是将原始 Alpha 值按组划分，然后在每个组内归一化（从每个值中减去组均值）的操作。分组可以是整个市场，也可以按行业、子行业等分类划分。

**目的：**
- 关注组内股票的相对回报
- 最小化对组整体回报的风险敞口
- 保护组合免受市场或行业冲击

**市场中性化：** 通过等量的多头和空头头寸实现，即多头投入金额 ≈ 空头投入金额。

### 数学原理

设置 `neutralization = market` 后，Alpha 向量经历如下变换：

```
Alpha = Alpha - mean(Alpha)
```

然后对新向量进行缩放以对应账户规模，形成的组合包含等金额的多头和空头头寸。

---

## II. group_neutralize 算子 vs 回测设置中的中性化

### 两者等价

`group_neutralize(x, group)` 与回测设置中的 Neutralization 使用**相同的操作**，可以互换使用。

**示例（等价写法）：**

```
# 写法 1: 在回测设置中设置中性化
alpha = -ts_delta(close, 5)
设置: neutralization=industry, decay=0, truncation=0

# 写法 2: 在表达式中使用 group_neutralize
alpha = group_neutralize(-ts_delta(close, 5), industry)
设置: neutralization=None, decay=0, truncation=0
```

### 何时使用 group_neutralize

需要在**不同的组值上更细化地应用中性化**时使用，例如在表达式中间步骤对某个子信号做中性化。

### 使用 group_neutralize 时的推荐设置

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| neutralization | None | 避免重复中性化 |
| decay | 0 | 在表达式内手动控制 |
| truncation | 0 | 在表达式内手动控制 |

---

## III. 使用建议

- **始终选择中性化**；仅当 Alpha 表达式中已有中性化算子时才将设置保留为 None
- 尝试流动性更好（股票数量较少）的股票池，确保每个组中有足够的股票
- 在流动性差的股票池中尝试更小的股票分组
- 对于 EUR、ASI 地区，手动使用"国家"和"交易所"中性化选项

---

## IV. 各数据集类别推荐中性化

| 数据集类别 | Market | Sector | Industry | Subindustry | 备注 |
|-----------|:------:|:------:|:--------:|:-----------:|------|
| Fundamental Datasets | | | ✓ | | 基本面对股价的影响因行业而异，推荐行业中性化 |
| Analysts Datasets | | | ✓ | | 分析师数据是对未来基本面的预测，同样推荐行业中性化 |
| Model Datasets | ✓ | ✓ | ✓ | ✓ | 模型数据因子数据集子类别差异极大，建议尝试各种中性化找最优 |
| News Datasets | | | | ✓ | 新闻对不同公司影响差异很大（如 CEO 变动对 Twitter 和 Apple 影响不同），推荐子行业中性化 |
| Option Datasets | ✓ | ✓ | | | 期权对股价的影响在较宽泛的行业内相似，推荐 Market 或 Sector |
| Price Volume Datasets | ✓ | ✓ | | | 通用想法在所有标的上表现良好，使用 Industry 或 Subindustry 可能降低表现 |
| Social Media Datasets | | | | ✓ | 社交媒体影响因子行业而异，推荐子行业中性化；也可尝试行业级别 |
| Institutions Datasets | | ✓ | ✓ | | 取决于机构数据集类型和提供方，测试 Sector 或 Industry |
| Short Interest Datasets | | | ✓ | | 推荐行业中性化，也可尝试其他 |
| Insider Datasets | | | ✓ | ✓ | 内部消息影响因行业/子行业而异，推荐这两个级别 |
| Sentiment Datasets | | | ✓ | ✓ | 与内部/社交媒体类似，情绪影响因行业/子行业而异 |
| Earnings Datasets | | | ✓ | | 推荐行业中性化，类似基本面数据集 |
| Macro Datasets | ✓ | ✓ | ✓ | | 宏观经济活动在 Sector/Market/Industry 层面最相关，子行业差异不大 |

---

## V. 快速参考

| 场景 | 推荐中性化 |
|------|-----------|
| 价格/成交量因子 | Market 或 Sector |
| 基本面/盈利/分析师 | Industry |
| 新闻/社交媒体/情绪/内部消息 | Subindustry |
| 期权 | Market 或 Sector |
| 宏观 | Market / Sector / Industry |
| 模型数据 | 尝试所有级别 |
| EUR/ASI 地区 | Country 或 Exchange |
