"""
Analyst4 数据集均值回归 Alpha 回测
- 从 analyst4 数据集获取前 N 个字段
- 按模板生成 alpha: 短期均值(22天)/长期均值(120天) → sector中性化 → 取反
- 多参数变体扫描

模板:
  Var_clear = winsorize(ts_backfill({field}, 120), std=4);
  ts_22 = ts_mean(Var_clear, 22);
  ts_120 = ts_mean(Var_clear, 120);
  ratio_22_120 = divide(ts_22, ts_120);
  final_alpha = group_neutralize(ratio_22_120, densify(sector));
  -final_alpha
"""
import json
import time
import logging
import requests

from backtest import run_backtest, setup_logging
from login import login

# ===== 配置 =====
DATASET_ID = 'analyst4'
FIELD_LIMIT = 100  # 取前N个字段
FIELD_BATCH_SIZE = 50  # 每次API查询数量
REGION = 'USA'
UNIVERSE = 'TOP3000'
DELAY = 1


def get_dataset_fields(sess, dataset_id=DATASET_ID, limit=FIELD_LIMIT,
                       instrument_type='EQUITY', region=REGION,
                       delay=DELAY, universe=UNIVERSE):
    """分页获取数据集下的数据字段，带重试"""
    fields = []
    url_template = (
        f"https://api.worldquantbrain.com/data-fields?"
        f"&instrumentType={instrument_type}"
        f"&region={region}&delay={delay}&universe={universe}"
        f"&dataset.id={dataset_id}&limit={FIELD_BATCH_SIZE}"
        f"&offset={{offset}}"
    )

    offset = 0
    while len(fields) < limit:
        url = url_template.format(offset=offset)
        logging.info(f"查询字段: offset={offset}")

        # 带重试的 API 请求
        for retry in range(3):
            try:
                resp = sess.get(url)
                data = resp.json()
                if 'results' in data:
                    batch = data['results']
                    if not batch:
                        # 没有更多字段
                        logging.info(f"数据集字段已全部获取, 共 {len(fields)} 个")
                        return fields[:limit]
                    for item in batch:
                        fields.append(item['id'])
                    offset += FIELD_BATCH_SIZE
                    break
                else:
                    logging.warning(f"查询异常: {data}, 重试 {retry+1}/3")
            except Exception as e:
                logging.warning(f"查询异常: {e}, 重试 {retry+1}/3")
            time.sleep(2)
        else:
            logging.error(f"字段查询失败, offset={offset}")
            break

    logging.info(f"共获取 {len(fields[:limit])} 个字段")
    return fields[:limit]


def build_alpha_expression(field):
    """根据模板生成 alpha 表达式"""
    return (
        f"Var_clear = winsorize(ts_backfill({field}, 120), std=4); "
        f"ts_22 = ts_mean(Var_clear, 22); "
        f"ts_120 = ts_mean(Var_clear, 120); "
        f"ratio_22_120 = divide(ts_22, ts_120); "
        f"final_alpha = group_neutralize(ratio_22_120, densify(sector)); "
        f"-final_alpha"
    )


def s(decay=0, neut='SUBINDUSTRY', trunc=0.08):
    """默认回测设置"""
    return {
        'instrumentType': 'EQUITY', 'region': 'USA', 'universe': 'TOP3000',
        'delay': 1, 'decay': decay, 'neutralization': neut, 'truncation': trunc,
        'pasteurization': 'ON', 'unitHandling': 'VERIFY', 'nanHandling': 'ON',
        'language': 'FASTEXPR', 'visualization': False,
    }


def generate_alphas(fields):
    """
    对每个字段生成多个参数变体的 alpha
    返回: list of (label, expression, settings)
    """
    alphas = []

    # 参数组合 (表达式已含 group_neutralize(sector), 外层用 MARKET)
    param_sets = [
        # (变体后缀, decay, neutralization)
        ("d0", 0, 'MARKET'),
        ("d3", 3, 'MARKET'),
        ("d5", 5, 'MARKET'),
    ]

    for i, field in enumerate(fields):
        for suffix, decay, neut in param_sets:
            label = f"{field}_{suffix}"
            expr = build_alpha_expression(field)
            settings = s(decay=decay, neut=neut)
            alphas.append((label, expr, settings))

        # 每个字段只打印一次进度
        if (i + 1) % 10 == 0:
            logging.info(f"已生成 {i+1}/{len(fields)} 字段的 alpha ({len(param_sets)} 变体/字段)")

    return alphas


if __name__ == '__main__':
    # 基础日志配置 (run_backtest 内部会重新配置完整日志)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # 先登录查询字段
    logging.info("正在登录并查询 analyst4 数据集字段...")
    query_sess = login()

    try:
        fields = get_dataset_fields(query_sess)
    finally:
        query_sess.close()

    if not fields:
        logging.error("未获取到任何字段，退出")
        exit(1)

    logging.info(f"获取到 {len(fields)} 个字段")
    for i, f in enumerate(fields):
        logging.info(f"  [{i+1:3d}] {f}")

    # 生成 alpha 表达式
    logging.info("\n正在生成 alpha 表达式...")
    alphas = generate_alphas(fields)
    logging.info(f"共生成 {len(alphas)} 个 alpha (每个字段3个参数变体)")

    # 运行回测
    run_backtest("analyst4", alphas)
