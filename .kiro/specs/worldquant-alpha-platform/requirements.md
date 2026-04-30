# 需求文档

## 简介

本功能为 WorldQuant Brain Alpha 研究工程平台，面向量化研究员，提供三大核心能力：

1. **Alpha 回测**：将 alpha 表达式提交至 Brain API，轮询并获取回测结果
2. **Alpha 模板提取**：从已有 alpha 表达式中识别并提取可复用的结构模板
3. **Alpha Idea 生成**：基于数据字段与算子的组合规则，自动生成新的 alpha 表达式候选

目标市场：美国股票（TOP3000），延迟 1 天，采用系统化组合表达式方式进行 alpha 发现。

---

## 词汇表

- **Alpha 表达式**：由数据字段与算子组合而成的因子公式，例如 `group_mean(ts_rank(field, 63), sector)`
- **Brain API**：WorldQuant Brain 平台提供的 REST API，基础 URL 为 `https://api.worldquantbrain.com`
- **Session**：通过 HTTP Basic Auth 认证后建立的 `requests.Session` 对象，携带认证凭据
- **数据字段（Data Field）**：Brain 平台提供的原始数据列，如价格、成交量、基本面指标等
- **算子（Operator）**：对数据字段进行变换的函数，分为时间序列算子（ts_*）和截面分组算子（group_*）
- **回测（Simulation）**：将 alpha 表达式提交至 Brain API 的 `/simulations` 端点，获取历史绩效评估结果
- **模板（Template）**：从 alpha 表达式中抽象出的结构模式，字段部分用占位符替换，例如 `group_mean(ts_rank({field}, {day}), {group})`
- **Backtest_Engine**：负责提交 alpha 并轮询回测结果的模块
- **Template_Extractor**：负责从 alpha 表达式中提取结构模板的模块
- **Idea_Generator**：负责基于字段与算子组合生成 alpha 表达式候选的模块
- **Data_Fetcher**：负责从 Brain API 分页获取数据字段的模块
- **Authenticator**：负责建立并返回认证 Session 的模块

---

## 需求

### 需求 1：用户认证

**用户故事：** 作为量化研究员，我希望系统能自动完成 Brain API 认证，以便后续所有 API 调用都携带有效凭据。

#### 验收标准

1. THE Authenticator SHALL 从 `brain_credentials.txt` 文件中读取用户名和密码（JSON 数组格式 `[username, password]`）
2. IF `brain_credentials.txt` 文件不存在，THEN THE Authenticator SHALL 从环境变量 `BRAIN_USERNAME` 和 `BRAIN_PASSWORD` 中读取凭据
3. IF 环境变量和凭据文件均不存在，THEN THE Authenticator SHALL 抛出包含明确说明的异常，提示用户配置凭据
4. WHEN 凭据加载成功，THE Authenticator SHALL 向 `POST /authentication` 发送请求并建立认证 Session
5. IF 认证请求返回非 200 状态码，THEN THE Authenticator SHALL 抛出异常并输出响应状态码与响应体

---

### 需求 2：数据字段获取

**用户故事：** 作为量化研究员，我希望能按条件查询 Brain 平台的数据字段列表，以便为 alpha 生成提供原料。

#### 验收标准

1. WHEN 调用数据字段获取接口，THE Data_Fetcher SHALL 支持按 `instrument_type`、`region`、`delay`、`universe`、`dataset_id`、`data_type`、`search` 参数过滤
2. THE Data_Fetcher SHALL 以每页 50 条的步长对 `GET /data-fields` 进行分页请求，直至获取全部结果
3. WHEN 某页返回结果数量少于 50 条，THE Data_Fetcher SHALL 停止分页并返回已累积的全部数据
4. IF API 响应中不包含 `results` 字段，THEN THE Data_Fetcher SHALL 输出异常响应内容并终止本次请求
5. THE Data_Fetcher SHALL 将所有分页结果合并后以 `pandas.DataFrame` 格式返回
6. WHERE 用户需要持久化数据字段，THE Data_Fetcher SHALL 支持将 DataFrame 导出为 CSV 文件至 `file/` 目录

---

### 需求 3：Alpha 回测提交与结果获取

**用户故事：** 作为量化研究员，我希望能将 alpha 表达式提交至 Brain API 并获取回测结果，以便评估 alpha 的历史绩效。

#### 验收标准

1. WHEN 提交 alpha 表达式，THE Backtest_Engine SHALL 向 `POST /simulations` 发送包含表达式和回测配置的请求
2. THE Backtest_Engine SHALL 在回测配置中支持以下参数：`instrumentType`、`region`、`universe`、`delay`、`decay`、`neutralization`、`truncation`、`pasteurization`、`unitHandling`、`nanHandling`、`language`
3. WHEN 提交成功，THE Backtest_Engine SHALL 从响应头 `Location` 中获取轮询 URL
4. WHILE 回测进行中，THE Backtest_Engine SHALL 按响应头 `Retry-After` 指定的秒数等待后重新轮询进度
5. WHEN 轮询响应中 `Retry-After` 为 0 或不存在，THE Backtest_Engine SHALL 判定回测完成并停止轮询
6. IF 回测状态为 `ERROR`，THEN THE Backtest_Engine SHALL 输出错误信息并跳过该 alpha，继续处理下一个
7. WHEN 回测成功完成，THE Backtest_Engine SHALL 提取并返回 alpha ID
8. IF 提交响应中不包含 `Location` 响应头，THEN THE Backtest_Engine SHALL 等待 10 秒后继续处理下一个 alpha

---

### 需求 4：Alpha 模板提取

**用户故事：** 作为量化研究员，我希望能从已有的 alpha 表达式中提取可复用的结构模板，以便系统化地扩展 alpha 搜索空间。

#### 验收标准

1. WHEN 输入一组 alpha 表达式，THE Template_Extractor SHALL 识别其中的算子结构，并将数据字段名替换为占位符（如 `{field}`），生成模板字符串
2. THE Template_Extractor SHALL 识别并提取时间序列算子（`ts_*`）和截面分组算子（`group_*`）的嵌套结构
3. THE Template_Extractor SHALL 对提取出的模板进行去重，相同结构的模板只保留一份
4. WHEN 提取完成，THE Template_Extractor SHALL 返回包含模板字符串及其出现频次的结构化结果
5. IF 输入的 alpha 表达式列表为空，THEN THE Template_Extractor SHALL 返回空列表而非抛出异常

---

### 需求 5：Alpha Idea 生成

**用户故事：** 作为量化研究员，我希望系统能基于数据字段和算子的组合规则自动生成 alpha 表达式候选，以便提升 alpha 发现效率。

#### 验收标准

1. WHEN 提供数据字段列表、时间序列算子列表、分组算子列表、时间窗口列表和分组维度列表，THE Idea_Generator SHALL 生成所有合法的组合表达式
2. THE Idea_Generator SHALL 按照 `group_op(ts_op(field, day), group)` 的模板结构生成表达式
3. THE Idea_Generator SHALL 支持扩展：允许传入自定义模板结构以生成不同形式的 alpha 表达式
4. WHEN 生成完成，THE Idea_Generator SHALL 返回包含表达式字符串及对应回测配置的结构化列表
5. IF 任意输入参数列表为空，THEN THE Idea_Generator SHALL 返回空列表而非抛出异常
6. THE Idea_Generator SHALL 确保生成的表达式列表中不包含重复项

---

### 需求 6：端到端流程编排

**用户故事：** 作为量化研究员，我希望有一个统一的入口将认证、数据获取、Idea 生成和回测串联起来，以便一键运行完整的 alpha 研究流程。

#### 验收标准

1. THE Orchestrator SHALL 按照以下顺序执行：认证 → 数据字段获取 → Alpha Idea 生成 → 批量回测提交
2. WHEN 任意阶段发生不可恢复的错误，THE Orchestrator SHALL 终止流程并输出明确的错误阶段和错误信息
3. THE Orchestrator SHALL 不包含业务逻辑，仅负责模块间的调用与数据传递
4. WHEN 回测全部完成，THE Orchestrator SHALL 汇总并输出成功提交的 alpha 数量与失败数量
