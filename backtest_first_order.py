"""
一阶 Alpha 回测 (First Order Backtest)
- 基于 machine_lib.py 的 first_order_factory 生成一阶 alpha 表达式
- 使用 backtest.py 的统一回测框架（超时控制 + DB 自动存储 + 去重）
- 默认数据集: analyst4，可配置

流程:
  1. 登录 WQ Brain API → 获取数据集字段
  2. process_datafields: winsorize + ts_backfill 预处理
  3. first_order_factory: 字段 × ts_ops 操作符 → 生成 alpha 表达式
  4. 随机采样 (控制数量) → 多个 decay 变体
  5. run_backtest() 统一回测 (自动去重 + 入库)
"""
import random
import logging
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest import run_backtest
from login import login as brain_login
from offical.user.machine_lib import (
    get_datafields,
    process_datafields,
    first_order_factory,
    ts_ops,
)

# ===== 可配置参数 =====
DATASET_ID = 'analyst4'       # 数据集 ID
MAX_SAMPLES = 900             # 随机采样上限 (超过则随机采样)
# DECAY_VALUES = [0, 3, 5]      # decay 参数变体
DECAY_VALUES = [4]      # decay 参数变体
NEUTRALIZATION = 'SUBINDUSTRY' # 中性化方式
UNIVERSE = 'TOP3000'
REGION = 'USA'
DELAY = 1


def build_settings(decay, neut=NEUTRALIZATION):
    """构建回测设置（与 machine_lib single_simulate 一致）"""
    return {
        'instrumentType': 'EQUITY',
        'region': REGION,
        'universe': UNIVERSE,
        'delay': DELAY,
        'decay': decay,
        'neutralization': neut,
        'truncation': 0.08,
        'pasteurization': 'ON',
        'unitHandling': 'VERIFY',
        'nanHandling': 'ON',
        'language': 'FASTEXPR',
        'visualization': False,
    }


def prepare_alphas(dataset_id=DATASET_ID, max_samples=MAX_SAMPLES):
    """
    从数据集获取字段 → 预处理 → 一阶工厂 → 转换为回测格式
    返回: list of (label, expression, settings)
    """
    logging.info(f"正在登录并获取数据集 [{dataset_id}] 字段...")
    sess = brain_login()

    try:
        # 1. 获取数据字段
        df = get_datafields(sess, dataset_id=dataset_id,
                            region=REGION, universe=UNIVERSE, delay=DELAY)
        logging.info(f"获取到 {len(df)} 个数据字段 (MATRIX + VECTOR)")

        # 2. 预处理: winsorize(ts_backfill(field, 120), std=4)
        pc_fields = process_datafields(df)
        logging.info(f"预处理后 {len(pc_fields)} 个字段")

        # 3. 一阶工厂: 字段 × ts_ops 操作符
        first_order = first_order_factory(pc_fields, ts_ops)
        logging.info(f"生成 {len(first_order)} 个一阶 alpha 表达式")

    finally:
        sess.close()

    # 4. 随机采样控制数量
    if max_samples and len(first_order) > max_samples:
        logging.info(f"随机采样 {max_samples} / {len(first_order)} 个表达式")
        first_order = random.sample(first_order, max_samples)

    # 5. 转换为 (label, expression, settings) 格式
    alphas = []
    for i, expr in enumerate(first_order):
        for decay in DECAY_VALUES:
            # 用序号做 label，表达式本身太长了
            label = f"fo_{i:04d}_d{decay}"
            settings = build_settings(decay)
            alphas.append((label, expr, settings))

    logging.info(f"共 {len(alphas)} 个回测任务 ({len(first_order)} 表达式 × {len(DECAY_VALUES)} decays)")

    return alphas


if __name__ == '__main__':
    # 基础日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    logging.info(f"{'='*70}")
    logging.info(f"一阶 Alpha 回测: dataset={DATASET_ID}, max_samples={MAX_SAMPLES}, "
                 f"decays={DECAY_VALUES}, neut={NEUTRALIZATION}")
    logging.info(f"{'='*70}")

    # 准备 alpha 列表
    try:
        alphas = prepare_alphas(DATASET_ID, MAX_SAMPLES)
    except Exception as e:
        logging.error(f"准备 alpha 失败: {e}")
        sys.exit(1)

    if not alphas:
        logging.error("未生成任何 alpha，退出")
        sys.exit(1)

    # 执行回测 (自动去重、超时控制、数据库入库)
    run_backtest(f"first_order_{DATASET_ID}", alphas)
