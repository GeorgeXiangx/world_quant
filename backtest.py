"""
WorldQuant Brain Alpha 回测框架 (多线程版)
- ThreadPoolExecutor 并发提交，Pre-Consultant 限制 5 个并发
- logging 框架输出到终端 + log/ 目录
- 每轮结果汇总保存到 CSV
- Checks 判断: SELF_CORRELATION 为 PENDING，其他全 PASS 即可提交
- 超时控制: 单任务超 5 分钟自动取消并重试，最多 3 次，仍超时则延后回测
"""
import time
import json
import csv
import logging
import threading
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from login import login
from alpha_db import save_result as db_save, is_already_tested as db_exists


class RateLimitExceeded(Exception):
    """API 调用次数已用完，需退出程序"""
    pass

# 并发数: Pre-Consultant 最多 5 个并发，TUTORIAL 账号限制为 1
MAX_WORKERS = 3

# 超时控制: 单次回测最大等待时间 (秒)
SIMULATE_TIMEOUT = 300  # 5 分钟
MAX_RETRIES = 3  # 单因子最大重试次数

# 共享 session 刷新（多线程安全）
_sess_refresh_lock = threading.Lock()


def _refresh_session(sess_ref):
    """重新登录，刷新共享 session（线程安全，只有一个线程真正执行登录）"""
    with _sess_refresh_lock:
        old = sess_ref[0]
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        sess_ref[0] = login()
        logging.info("Session 已刷新（认证过期自动重新登录）")


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


def cancel_simulation(sess_ref, sim_url, label=""):
    """取消正在进行的回测任务"""
    try:
        resp = sess_ref[0].delete(sim_url)
        logging.info(f"  [{label}] 取消请求已发送, 状态码: {resp.status_code}")
        return True
    except Exception as e:
        logging.error(f"  [{label}] 取消失败: {e}")
        return False


def simulate(sess_ref, expression, settings, label=""):
    """提交单个 alpha 回测并获取详细结果（线程安全）
    超时自动取消并重试，最多 MAX_RETRIES 次；全部超时则返回超时标记
    认证过期自动刷新共享 session 并重试
    """
    thread_name = threading.current_thread().name
    sim_data = {'type': 'REGULAR', 'settings': settings, 'regular': expression}
    overall_start = time.time()

    logging.info(f"[{label}] 开始回测")
    logging.info(f"  表达式: {expression}")
    logging.info(f"  设置: decay={settings.get('decay')}, neutralization={settings.get('neutralization')}, "
                 f"truncation={settings.get('truncation')}, universe={settings.get('universe')}, "
                 f"region={settings.get('region')}, delay={settings.get('delay')}")

    alpha_id = None  # 外层作用域声明
    got_result = False

    for attempt in range(1, MAX_RETRIES + 1):
        attempt_start = time.time()

        if attempt > 1:
            logging.info(f"[{label}] === 第 {attempt}/{MAX_RETRIES} 次重试 ===")

        # === 提交模拟，失败自动重试 ===
        sim_url = None
        while True:
            try:
                sim_resp = sess_ref[0].post("https://api.worldquantbrain.com/simulations", json=sim_data)
                sim_url = sim_resp.headers['Location']
                sim_id = sim_url.rstrip('/').split('/')[-1]
                logging.info(f"  [{label}] 模拟地址: {sim_url} (第{attempt}次)")
                break
            except KeyError:
                try:
                    resp_json = sim_resp.json()
                    if 'rate limit' in str(resp_json.get('message', '')).lower():
                        logging.error(f"  [{label}] API 调用次数已用完: {resp_json}")
                        raise RateLimitExceeded()
                    if 'credentials' in str(resp_json.get('detail', '')):
                        logging.warning(f"  [{label}] 认证过期，正在刷新 session...")
                        _refresh_session(sess_ref)
                        continue  # 用新 session 重新提交
                    logging.warning(f"  [{label}] 提交异常: {resp_json}, 10s 后重试")
                except Exception:
                    logging.warning(f"  [{label}] 提交异常: {sim_resp.content[:200]}, 10s 后重试")
                time.sleep(10)
            except Exception as e:
                logging.warning(f"  [{label}] 网络异常: {e}, 10s 后重试")
                time.sleep(10)

        # === 轮询等待完成 (带超时) ===
        poll_start = time.time()
        while True:
            elapsed = time.time() - poll_start
            if elapsed > SIMULATE_TIMEOUT:
                logging.warning(f"[{label}] 第{attempt}次回测超时 ({SIMULATE_TIMEOUT}s), "
                                f"正在取消 sim_id={sim_url.rstrip('/').split('/')[-1] if sim_url else '?'}...")
                if sim_url:
                    cancel_simulation(sess_ref, sim_url, label)
                break  # 跳出轮询，进入下一次重试

            try:
                r = sess_ref[0].get(sim_url)
                data = r.json()
            except Exception as e:
                logging.warning(f"  [{label}] 轮询异常: {e}, 5s 后重试")
                time.sleep(5)
                continue

            if 'rate limit' in str(data.get('message', '')).lower():
                logging.error(f"  [{label}] API 调用次数已用完: {data}")
                raise RateLimitExceeded()

            if 'alpha' in data:
                alpha_id = data['alpha']
                got_result = True
                logging.info(f"  [{label}] 回测完成, alpha_id={alpha_id} (第{attempt}次)")
                break

            status = data.get('status', '')
            if status == 'ERROR':
                logging.error(f"  [{label}] 回测错误: {data.get('message', 'unknown')}")
                return None
            if status == 'FAIL':
                logging.error(f"  [{label}] 回测失败: {data.get('message', 'unknown')}")
                return None
            if status == 'COMPLETE':
                logging.error(f"  [{label}] 回测异常完成但无 alpha_id: {data}")
                return None

            try:
                progress = int(100 * data.get('progress', 0))
                logging.info(f"  [{label}] 进度 {progress}% (第{attempt}次)")
            except Exception:
                pass
            retry = float(r.headers.get("Retry-After", 0))
            if retry == 0:
                logging.warning(f"  [{label}] 无 Retry-After 且无终态，响应: {data}")
                return None
            time.sleep(retry)

        # 如果成功获取到 alpha_id，跳出重试循环
        if got_result:
            break

        # 超时后的下一次重试
        if attempt < MAX_RETRIES:
            logging.info(f"[{label}] 第{attempt}次超时，准备 {attempt+1}/{MAX_RETRIES} 次重试")

    if not got_result:
        # 所有重试均超时
        logging.warning(f"[{label}] 全部 {MAX_RETRIES} 次尝试均超时，标记为待延迟回测")
        return {
            'label': label,
            'expression': expression,
            'settings': settings,
            'timed_out': True,
            'elapsed': round(time.time() - overall_start, 1),
        }

    # === 获取 alpha 详情 ===
    try:
        alpha_resp = sess_ref[0].get(f"https://api.worldquantbrain.com/alphas/{alpha_id}")
        alpha_data = alpha_resp.json()
        if 'rate limit' in str(alpha_data.get('message', '')).lower():
            logging.error(f"  [{label}] API 调用次数已用完: {alpha_data}")
            raise RateLimitExceeded()
    except RateLimitExceeded:
        raise
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
        'elapsed': round(time.time() - overall_start, 1),
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
    logging.info(f"  [{label}] 耗时: {result['elapsed']}s")

    return result


def run_backtest(run_name, alphas, max_workers=MAX_WORKERS, skip_tested=True):
    """
    多线程执行一轮回测
    alphas: list of (label, expression, settings)
    max_workers: 并发线程数，Pre-Consultant 建议 ≤ 5
    skip_tested: 是否跳过已成功回测过的因子（默认 True）
    超时任务自动延后到队列末尾重试
    所有结果自动写入 SQLite 数据库
    """
    log_file, timestamp = setup_logging(run_name)
    sess_ref = [login()]  # 共享 session 容器，支持自动刷新
    total_start = time.time()

    logging.info(f"{'='*70}")
    logging.info(f"回测任务: {run_name}, 共 {len(alphas)} 个变体, 并发数={max_workers}")
    logging.info(f"{'='*70}")

    # === 去重: 过滤已成功回测的因子 ===
    skipped_count = 0
    new_alphas = []
    for label, expr, settings in alphas:
        if skip_tested:
            cached = db_exists(expr, settings)
            if cached:
                logging.info(f"[{label}] 已回测过 (alpha_id={cached.get('alpha_id')}, "
                             f"sharpe={cached.get('sharpe')}), 跳过")
                skipped_count += 1
                continue
        new_alphas.append((label, expr, settings))

    if skipped_count > 0:
        logging.info(f"跳过 {skipped_count} 个已测试因子, 剩余 {len(new_alphas)} 个待回测")

    if not new_alphas:
        logging.info("所有因子均已回测过，无需提交")
        return [], []

    alphas = new_alphas
    results_map = {}  # label -> result，保持顺序
    cached_results = []  # 从DB恢复的已跳过结果
    timed_out_queue = []  # 超时待重试队列
    total = len(alphas)
    completed = 0
    lock = threading.Lock()

    def run_batch(batch_alphas, batch_label=""):
        """执行一批回测任务，返回 (结果字典, 超时任务列表)
        每个结果自动写入 SQLite 数据库
        """
        nonlocal completed
        batch_results = {}
        batch_timed_out = []

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="backtest") as executor:
            future_to_label = {
                executor.submit(simulate, sess_ref, expr, settings, label): label
                for label, expr, settings in batch_alphas
            }
            for future in as_completed(future_to_label):
                label = future_to_label[future]
                # 从 batch_alphas 中找回对应的 expression 和 settings
                expr = None
                settings = None
                for l, e, s in batch_alphas:
                    if l == label:
                        expr = e
                        settings = s
                        break

                try:
                    result = future.result()
                except RateLimitExceeded:
                    logging.error("API 调用次数已用完，程序退出")
                    os._exit(0)
                except Exception as e:
                    logging.error(f"[{label}] 线程异常: {e}")
                    result = None

                # === 写入数据库 ===
                if expr and settings:
                    try:
                        is_new = db_save(label, expr, settings, result, run_name)
                    except Exception as e:
                        logging.error(f"[{label}] 数据库写入失败: {e}")

                if result and result.get('timed_out'):
                    batch_timed_out.append((label, result['expression'], result['settings']))
                    batch_results[label] = result
                    logging.warning(f"[{label}] 超时，已加入延迟回测队列")
                else:
                    batch_results[label] = result

                with lock:
                    completed += 1
                    logging.info(f"进度: {completed}/{total} 完成")
        return batch_results, batch_timed_out

    # === 第一轮: 回测所有因子 ===
    batch_results, timed_out_queue = run_batch(alphas)

    # 合并结果
    results_map.update(batch_results)

    # === 延迟回测: 超时任务放到最后重试 ===
    if timed_out_queue:
        logging.info(f"\n{'='*70}")
        logging.info(f"延迟回测: {len(timed_out_queue)} 个超时任务重新提交...")
        logging.info(f"{'='*70}")
        for label, expr, settings in timed_out_queue:
            logging.info(f"  待重试: [{label}]")

        # 重新计算 total (加上重试任务)
        total += len(timed_out_queue)
        retry_results, still_timed_out = run_batch(timed_out_queue, batch_label="retry")

        # 合并重试结果 (覆盖之前的超时标记)
        for label, result in retry_results.items():
            if result and not result.get('timed_out'):
                results_map[label] = result
                logging.info(f"[{label}] 延迟回测成功!")
            else:
                logging.warning(f"[{label}] 延迟回测仍超时，最终放弃")

    # 按原始顺序排列结果
    results = [results_map.get(label) for label, _, _ in alphas]

    # === 汇总 ===
    logging.info(f"\n{'='*70}")
    logging.info(f"回测结果汇总 - {run_name}")
    logging.info(f"{'='*70}")
    logging.info(f"{'变体':<25} {'Sharpe':>8} {'Fitness':>8} {'TO%':>8} {'Ret':>8} {'Checks':>12} {'耗时':>8} {'可提交':>6}")
    logging.info("-" * 88)

    submittable_list = []
    for r in results:
        if r and not r.get('timed_out'):
            to = f"{round(100*r['turnover'],1)}%" if isinstance(r['turnover'], (int, float)) else 'N/A'
            checks_str = f"{r['checks_passed']}P+{r['checks_pending']}D/{r['checks_total']}"
            sub_mark = "✓" if r['submittable'] else "✗"
            elapsed_str = f"{r.get('elapsed', 'N/A')}s"
            logging.info(f"{r['label']:<25} {str(r['sharpe']):>8} {str(r['fitness']):>8} {to:>8} "
                         f"{str(r['returns']):>8} {checks_str:>12} {elapsed_str:>8} {sub_mark:>6}")
            if r['submittable']:
                submittable_list.append(r)
        elif r and r.get('timed_out'):
            logging.info(f"{r['label']:<25} {'TIMEOUT':>8}")
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
            if r and not r.get('timed_out'):
                writer.writerow(r)

    # === 数据库统计 ===
    try:
        from alpha_db import get_stats
        stats = get_stats()
        logging.info(f"\n数据库: {stats['database']}")
        logging.info(f"  总记录: {stats['total']} | 成功: {stats['success']} | 可提交: {stats['submittable']}")
    except Exception:
        pass

    logging.info(f"\nCSV 结果已保存: {csv_file}")
    logging.info(f"日志已保存: {log_file}")
    total_elapsed = time.time() - total_start
    logging.info(f"总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")

    return results, submittable_list
