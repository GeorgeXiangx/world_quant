# WorldQuant Brain Operators 参考手册

> 数据来源：WorldQuant Brain API (`GET /operators`)，共 66 个算子

---

## Arithmetic（算术算子）

| 算子 | 定义 | 说明 | 等级 |
|------|------|------|------|
| `abs(x)` | `abs(x)` | 返回 x 的绝对值 | ALL |
| `add(x, y, filter=false)` | `x + y` | 逐元素相加（至少2个输入）。filter=true 时将 NaN 视为 0 | ALL |
| `subtract(x, y, filter=false)` | `x - y` | 逐元素相减（至少2个输入）。filter=true 时将 NaN 视为 0 | ALL |
| `multiply(x, y, ..., filter=false)` | `x * y` | 逐元素相乘（至少2个输入）。filter=true 时将 NaN 视为 0 | ALL |
| `divide(x, y)` | `x / y` | x 除以 y | ALL |
| `inverse(x)` | `inverse(x)` | 1 / x | ALL |
| `power(x, y)` | `power(x, y)` | x 的 y 次方 | ALL |
| `signed_power(x, y)` | `signed_power(x, y)` | x 的 y 次方，保留 x 的符号 | ALL |
| `sqrt(x)` | `sqrt(x)` | 非负平方根，等价于 power(x, 0.5) | ALL |
| `log(x)` | `log(x)` | 自然对数，适用于正值数据变换 | ALL |
| `sign(x)` | `sign(x)` | 返回符号：正数+1，负数-1，零为0，NaN 返回 NaN | ALL |
| `reverse(x)` | `reverse(x)` | 取反：-x | ALL |
| `min(x, y, ..)` | `min(x, y, ..)` | 所有输入的最小值（至少2个输入） | ALL |
| `max(x, y, ..)` | `max(x, y, ..)` | 所有输入的最大值（至少2个输入） | ALL |
| `densify(x)` | `densify(x)` | 将分组字段的多个桶压缩为较少的可用桶，提高计算效率 | ALL |

---

## Logical（逻辑算子）

| 算子 | 定义 | 说明 | 等级 |
|------|------|------|------|
| `and(input1, input2)` | `and(input1, input2)` | 两个输入都为1时返回1，否则返回0 | ALL |
| `or(input1, input2)` | `or(input1, input2)` | 任一输入为1时返回1，否则返回0 | ALL |
| `not(x)` | `not(x)` | 逻辑取反：x=1返回0，x=0返回1 | ALL |
| `if_else(cond, x, y)` | `if_else(input1, input2, input3)` | 条件为真返回 x，否则返回 y | ALL |
| `equal` | `input1 == input2` | 相等返回1，否则返回0 | ALL |
| `not_equal` | `input1 != input2` | 不等返回1，否则返回0 | ALL |
| `greater` | `input1 > input2` | 大于返回1，否则返回0 | ALL |
| `greater_equal` | `input1 >= input2` | 大于等于返回1，否则返回0 | ALL |
| `less` | `input1 < input2` | 小于返回1，否则返回0 | ALL |
| `less_equal` | `input1 <= input2` | 小于等于返回1，否则返回0 | ALL |
| `is_nan(input)` | `is_nan(input)` | 输入为 NaN 返回1，否则返回0 | ALL |

---

## Time Series（时间序列算子）

| 算子 | 定义 | 说明 | 等级 |
|------|------|------|------|
| `ts_sum(x, d)` | `ts_sum(x, d)` | 过去 d 天 x 的累计和 | ALL |
| `ts_mean(x, d)` | `ts_mean(x, d)` | 过去 d 天 x 的简单平均值 | ALL |
| `ts_std_dev(x, d)` | `ts_std_dev(x, d)` | 过去 d 天 x 的标准差 | ALL |
| `ts_zscore(x, d)` | `ts_zscore(x, d)` | 时间序列 Z-score，当前值与近期均值的标准差距离 | ALL |
| `ts_rank(x, d, constant=0)` | `ts_rank(x, d, constant=0)` | 过去 d 天内当前值的排名，用于归一化时间序列 | ALL |
| `ts_scale(x, d, constant=0)` | `ts_scale(x, d, constant=0)` | 基于过去 d 天的最小/最大值将时间序列缩放到 0-1 范围 | ALL |
| `ts_quantile(x, d, driver="gaussian")` | `ts_quantile(x, d, driver="gaussian")` | 对 ts_rank 结果应用逆累积分布函数变换 | ALL |
| `ts_delta(x, d)` | `ts_delta(x, d)` | 当前值与 d 天前值的差，用于衡量变化/动量 | ALL |
| `ts_delay(x, d)` | `ts_delay(x, d)` | 返回 d 天前的 x 值 | ALL |
| `ts_sum(x, d)` | `ts_sum(x, d)` | 过去 d 天 x 值的累计和 | ALL |
| `ts_product(x, d)` | `ts_product(x, d)` | 过去 d 天 x 值的乘积，适用于几何均值和复合收益率 | ALL |
| `ts_corr(x, y, d)` | `ts_corr(x, y, d)` | 过去 d 天 x 和 y 的 Pearson 相关系数 | ALL |
| `ts_covariance(y, x, d)` | `ts_covariance(y, x, d)` | 过去 d 天 y 和 x 的协方差 | ALL |
| `ts_regression(y, x, d, lag=0, rettype=0)` | `ts_regression(y, x, d, lag=0, rettype=0)` | 时间序列回归，返回回归相关参数 | ALL |
| `ts_arg_min(x, d)` | `ts_arg_min(x, d)` | 过去 d 天内最小值距今的天数（今天=0，昨天=1） | ALL |
| `ts_arg_max(x, d)` | `ts_arg_max(x, d)` | 过去 d 天内最大值距今的天数（今天=0，昨天=1） | ALL |
| `ts_decay_linear(x, d, dense=false)` | `ts_decay_linear(x, d, dense=false)` | 线性衰减加权平均，平滑时间序列数据 | ALL |
| `ts_backfill(x, lookback=d, k=1)` | `ts_backfill(x, lookback=d, k=1)` | 用最近有效值填充 NaN，提高数据覆盖率 | ALL |
| `ts_av_diff(x, d)` | `ts_av_diff(x, d)` | x 与过去 d 天均值的差：x - ts_mean(x, d)，忽略 NaN | ALL |
| `ts_count_nans(x, d)` | `ts_count_nans(x, d)` | 过去 d 天内 NaN 值的数量 | ALL |
| `ts_step(1)` | `ts_step(1)` | 日计数器，每天递增1 | ALL |
| `hump(x, hump=0.01)` | `hump(x, hump=0.01)` | 限制输入变化的幅度和频率，降低换手率 | ALL |
| `last_diff_value(x, d)` | `last_diff_value(x, d)` | 过去 d 天内与当前值不同的最近值 | ALL |
| `days_from_last_change(x)` | `days_from_last_change(x)` | 距上次值变化的天数 | ALL |
| `kth_element(x, d, k, ignore="NaN")` | `kth_element(x, d, k, ignore="NaN")` | 回溯 d 天内的第 k 个值，可忽略特定值，常用于回填 | ALL |

---

## Cross Sectional（截面算子）

| 算子 | 定义 | 说明 | 等级 |
|------|------|------|------|
| `rank(x, rate=2)` | `rank(x, rate=2)` | 在所有标的中排名，返回 0.0-1.0 之间的值，减少异常值影响 | ALL |
| `zscore(x)` | `zscore(x)` | 截面 Z-score，衡量值与均值的标准差距离 | ALL |
| `scale(x, scale=1, longscale=1, shortscale=1)` | `scale(x, ...)` | 缩放使绝对值之和等于指定账面规模，支持多空分别缩放 | ALL |
| `normalize(x, useStd=false, limit=0.0)` | `normalize(x, ...)` | 减去市场均值居中；可选除以标准差并限幅 | ALL |
| `quantile(x, driver="gaussian", sigma=1.0)` | `quantile(x, ...)` | 排名后应用指定分布的逆 CDF 变换，减少异常值 | ALL |
| `winsorize(x, std=4)` | `winsorize(x, std=4)` | 将值限制在均值 ± 指定标准差范围内，减少极端异常值影响 | ALL |

---

## Vector（向量算子）

| 算子 | 定义 | 说明 | 等级 |
|------|------|------|------|
| `vec_sum(x)` | `vec_sum(x)` | 计算向量字段所有值的和 | ALL |
| `vec_avg(x)` | `vec_avg(x)` | 计算向量字段所有元素的均值，将向量数据转为单一矩阵值 | ALL |

---

## Transformational（变换算子）

| 算子 | 定义 | 说明 | 等级 |
|------|------|------|------|
| `bucket(rank(x), range/buckets, ...)` | `bucket(rank(x), ...)` | 按排名值将数据分桶，可与 group 算子配合使用 | ALL |
| `trade_when(x, y, z)` | `trade_when(x, y, z)` | 仅在条件满足时更新 Alpha 值，否则保持前值；可通过退出条件平仓。用于降低换手率 | ALL |

---

## Group（分组算子）

| 算子 | 定义 | 说明 | 等级 |
|------|------|------|------|
| `group_rank(x, group)` | `group_rank(x, group)` | 组内排名，返回 0.0-1.0，用于同组标的比较 | ALL |
| `group_zscore(x, group)` | `group_zscore(x, group)` | 组内 Z-score，衡量值与组均值的标准差距离 | ALL |
| `group_neutralize(x, group)` | `group_neutralize(x, group)` | 组内中性化：减去组均值。分组可为行业、板块等 | ALL |
| `group_mean(x, weight, group)` | `group_mean(x, weight, group)` | 组内调和均值 | ALL |
| `group_scale(x, group)` | `group_scale(x, group)` | 组内归一化到 0-1 范围 | ALL |
| `group_backfill(x, group, d, std=4.0)` | `group_backfill(x, group, d, std=4.0)` | 用组内过去 d 天非 NaN 值的 winsorized 均值填充缺失值 | ALL |
