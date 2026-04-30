"""
WorldQuant Brain Alpha 回测框架 (多线程版)
- ThreadPoolExecutor 并发提交，Pre-Consultant 限制 5 个并发
- logging 框架输出到终端 + log/ 目录
- 每轮结果汇总保存到 CSV
- Checks 判断: SELF_CORRELATION 为 PENDING，其他全 PASS 即可提交
"""
import time
import json
import csv
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from login import login

# 并发数: Pre-Consultant 最多 5 个并发，TUTORIAL 账号限制为 1
MAX_WORKERS = 3


def setup_logging(run_name):
    """配置日志：同时输出到终端和 log/ 文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"log/backtest_{run_name}_{timestamp}.log"

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info(f"日志文件: {log_file}")
    return log_file, timestamp


def is_submittable(checks):
    """
    判断 alpha 是否可提交:
    SELF_CORRELATION 为 PENDING 或 PASS，其他字段全部为 PASS
    """
    for check in checks:
        name = check.get('name', '')
        result = check.get('result', '')
        if name == 'SELF_CORRELATION':
            if result not in ('PENDING', 'PASS'):
                return False
        else:
            if result != 'PASS':
                return False
    return True


def simulate(sess, expression, settings, label=""):
    """提交单个 alpha 回测并获取详细结果（线程安全）"""
    thread_name = threading.current_thread().name
    sim_data = {'type': 'REGULAR', 'settings': settings, 'regular': expression}
    start_time = time.time()

    logging.info(f"[{label}] 开始回测")
    logging.info(f"  表达式: {expression}")
    logging.info(f"  设置: decay={settings.get('decay')}, neutralization={settings.get('neutralization')}, "
                 f"truncation={settings.get('truncation')}, universe={settings.get('universe')}, "
                 f"region={settings.get('region')}, delay={settings.get('delay')}")

    # 提交模拟，失败自动重试
    while True:
        try:
            sim_resp = sess.post("https://api.worldquantbrain.com/simulations", json=sim_data)
            sim_url = sim_resp.headers['Location']
            logging.info(f"  [{label}] 模拟地址: {sim_url}")
            break
        except KeyError:
            # 可能是认证过期或限流
            try:
                resp_json = sim_resp.json()
                if 'credentials' in str(resp_json.get('detail', '')):
                    logging.error(f"  [{label}] 认证过期，跳过")
                    return None
                logging.warning(f"  [{label}] 提交异常: {resp_json}, 10s 后重试")
            except Exception:
                logging.warning(f"  [{label}] 提交异常: {sim_resp.content[:200]}, 10s 后重试")
            time.sleep(10)
        except Exception as e:
            logging.warning(f"  [{label}] 网络异常: {e}, 10s 后重试")
            time.sleep(10)

    # 轮询等待完成
    while True:
        try:
            r = sess.get(sim_url)
            data = r.json()
        except Exception as e:
            logging.warning(f"  [{label}] 轮询异常: {e}, 5s 后重试")
            time.sleep(5)
            continue

        if 'alpha' in data:
            alpha_id = data['alpha']
            logging.info(f"  [{label}] 回测完成, alpha_id={alpha_id}")
            break

        status = data.get('status', '')
        if status == 'ERROR':
            logging.error(f"  [{label}] 回测错误: {data.get('message', 'unknown')}")
            return None
        if status == 'FAIL':
            logging.error(f"  [{label}] 回测失败: {data.get('message', 'unknown')}")
            return None
        if status == 'COMPLETE':
            # COMPLETE 但没有 alpha 字段，说明表达式有问题
            logging.error(f"  [{label}] 回测异常完成但无 alpha_id: {data}")
            return None

        try:
            progress = int(100 * data.get('progress', 0))
            logging.info(f"  [{label}] 进度 {progress}%")
        except Exception:
            pass
        retry = float(r.headers.get("Retry-After", 0))
        if retry == 0:
            # 没有 Retry-After 且没有终态，说明已完成但响应异常
            logging.warning(f"  [{label}] 无 Retry-After 且无终态，响应: {data}")
            return None
        time.sleep(retry)

    # 获取 alpha 详情
    try:
        alpha_resp = sess.get(f"https://api.worldquantbrain.com/alphas/{alpha_id}")
        alpha_data = alpha_resp.json()
    except Exception as e:
        logging.error(f"  [{label}] 获取 alpha 详情失败: {e}")
        return None

    is_data = alpha_data.get('is', {})
    checks = is_data.get('checks', [])
    passed_count = sum(1 for c in checks if c.get('result') == 'PASS')
    pending_count = sum(1 for c in checks if c.get('result') == 'PENDING')
    total_count = len(checks)
    submittable = is_submittable(checks)

    result = {
        'label': label,
        'expression': expression,
        'alpha_id': alpha_id,
        'sharpe': is_data.get('sharpe', 'N/A'),
        'fitness': is_data.get('fitness', 'N/A'),
        'turnover': is_data.get('turnover', 'N/A'),
        'returns': is_data.get('returns', 'N/A'),
        'drawdown': is_data.get('drawdown', 'N/A'),
        'margin': is_data.get('margin', 'N/A'),
        'checks_passed': passed_count,
        'checks_pending': pending_count,
        'checks_total': total_count,
        'submittable': submittable,
        'elapsed': round(time.time() - start_time, 1),
        'link': f"https://platform.worldquantbrain.com/alpha/{alpha_id}",
        'decay': settings.get('decay'),
        'neutralization': settings.get('neutralization'),
        'truncation': settings.get('truncation'),
        'universe': settings.get('universe'),
    }

    logging.info(f"  [{label}] Sharpe={result['sharpe']}, Fitness={result['fitness']}, "
                 f"Turnover={result['turnover']}, Returns={result['returns']}")
    logging.info(f"  [{label}] Checks: {passed_count} PASS, {pending_count} PENDING / {total_count} total")
    for c in checks:
        logging.info(f"    {c.get('name')}: {c.get('result')}")
    logging.info(f"  [{label}] 可提交: {'是 ✓' if submittable else '否 ✗'}")
    logging.info(f"  [{label}] 链接: {result['link']}")
    elapsed = time.time() - start_time
    logging.info(f"  [{label}] 耗时: {elapsed:.1f}s")

    return result


def run_backtest(run_name, alphas, max_workers=MAX_WORKERS):
    """
    多线程执行一轮回测
    alphas: list of (label, expression, settings)
    max_workers: 并发线程数，Pre-Consultant 建议 ≤ 5
    """
    log_file, timestamp = setup_logging(run_name)
    sess = login()
    total_start = time.time()

    logging.info(f"{'='*70}")
    logging.info(f"回测任务: {run_name}, 共 {len(alphas)} 个变体, 并发数={max_workers}")
    logging.info(f"{'='*70}")

    results_map = {}  # label -> result，保持顺序

    total = len(alphas)
    completed = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="backtest") as executor:
        future_to_label = {
            executor.submit(simulate, sess, expr, settings, label): label
            for label, expr, settings in alphas
        }
        for future in as_completed(future_to_label):
            label = future_to_label[future]
            try:
                result = future.result()
                results_map[label] = result
            except Exception as e:
                logging.error(f"[{label}] 线程异常: {e}")
                results_map[label] = None
            with lock:
                completed += 1
                logging.info(f"进度: {completed}/{total} 完成")

    # 按原始顺序排列结果
    results = [results_map.get(label) for label, _, _ in alphas]

    # 汇总
    logging.info(f"\n{'='*70}")
    logging.info(f"回测结果汇总 - {run_name}")
    logging.info(f"{'='*70}")
    logging.info(f"{'变体':<25} {'Sharpe':>8} {'Fitness':>8} {'TO%':>8} {'Ret':>8} {'Checks':>12} {'耗时':>8} {'可提交':>6}")
    logging.info("-" * 88)

    submittable_list = []
    for r in results:
        if r:
            to = f"{round(100*r['turnover'],1)}%" if isinstance(r['turnover'], (int, float)) else 'N/A'
            checks_str = f"{r['checks_passed']}P+{r['checks_pending']}D/{r['checks_total']}"
            sub_mark = "✓" if r['submittable'] else "✗"
            elapsed_str = f"{r.get('elapsed', 'N/A')}s"
            logging.info(f"{r['label']:<25} {str(r['sharpe']):>8} {str(r['fitness']):>8} {to:>8} "
                         f"{str(r['returns']):>8} {checks_str:>12} {elapsed_str:>8} {sub_mark:>6}")
            if r['submittable']:
                submittable_list.append(r)
        else:
            logging.info(f"{'FAILED':<25}")

    # 可提交候选
    logging.info(f"\n{'='*70}")
    logging.info(f"可提交候选 (共 {len(submittable_list)} 个)")
    logging.info(f"{'='*70}")
    if submittable_list:
        for r in submittable_list:
            logging.info(f"  [{r['label']}] alpha_id={r['alpha_id']}")
            logging.info(f"    表达式: {r['expression']}")
            logging.info(f"    Sharpe={r['sharpe']}, Fitness={r['fitness']}, TO={r['turnover']}, Ret={r['returns']}")
            logging.info(f"    设置: decay={r['decay']}, neut={r['neutralization']}, trunc={r['truncation']}")
            logging.info(f"    链接: {r['link']}")
    else:
        logging.info("  暂无可提交候选")

    # 保存 CSV
    csv_file = f"file/backtest_{run_name}_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['label', 'alpha_id', 'sharpe', 'fitness', 'turnover', 'returns',
                      'drawdown', 'margin', 'checks_passed', 'checks_pending', 'checks_total',
                      'submittable', 'elapsed', 'decay', 'neutralization', 'truncation', 'universe',
                      'link', 'expression']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            if r:
                writer.writerow(r)

    logging.info(f"\nCSV 结果已保存: {csv_file}")
    logging.info(f"日志已保存: {log_file}")
    total_elapsed = time.time() - total_start
    logging.info(f"总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")

    return results, submittable_list
