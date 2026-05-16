"""
backtest_results 表数据库比较工具
- 比较本地 MySQL 与同一局域网内远程 MySQL 中 backtest_results 表的差异
- 双向比较：本地独有 / 远程独有 / md5 相同但字段不同
- 仅生成差异报告，不实际写入（safe-by-default）
- 用法示例：
    python sync_backtest_db.py \\
        --remote-host 192.168.1.100 --remote-user root --remote-password 123456 \\
        --remote-database alpha_simulate \\
        --output ./file/db_diff_report.csv
依赖：pip install pymysql
"""
import argparse
import csv
import logging
import sys
from datetime import datetime

import pymysql

from alpha_db import MYSQL_CONFIG as LOCAL_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

# ===== 比较时关注的关键字段（md5 相同但内容不同时，逐字段 diff）=====
COMPARE_FIELDS = [
    'status', 'alpha_id',
    'sharpe', 'fitness', 'turnover', 'returns', 'drawdown', 'margin',
    'checks_passed', 'checks_pending', 'checks_total', 'submittable',
    'run_name', 'label',
]

# ===== 索引字段（汇总报告时显示）=====
INDEX_FIELDS = ['md5_hash', 'expression', 'status', 'sharpe', 'alpha_id', 'updated_at']

# ===== 全量同步时迁移的字段（不含自增 id 与 created_at/updated_at 由数据库默认生成）=====
SYNC_COLUMNS = [
    'label', 'expression', 'settings_json', 'md5_hash', 'alpha_id', 'status',
    'sharpe', 'fitness', 'turnover', 'returns', 'drawdown', 'margin',
    'checks_passed', 'checks_pending', 'checks_total', 'submittable',
    'elapsed', 'decay', 'neutralization', 'truncation', 'universe', 'link',
    'run_name', 'created_at', 'updated_at',
]


def _connect(cfg, label):
    """建立 MySQL 连接，失败立即退出"""
    try:
        conn = pymysql.connect(
            host=cfg['host'],
            port=cfg['port'],
            user=cfg['user'],
            password=cfg['password'],
            database=cfg['database'],
            charset=cfg.get('charset', 'utf8mb4'),
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
            read_timeout=60,
        )
        logging.info(f"[{label}] 连接成功 → {cfg['host']}:{cfg['port']}/{cfg['database']}")
        return conn
    except pymysql.err.OperationalError as e:
        logging.error(f"[{label}] 连接失败: {e}")
        sys.exit(1)


def _fetch_all_rows(conn, label):
    """一次性拉取整张表的关键字段，按 md5_hash 索引"""
    sql = (
        "SELECT md5_hash, expression, label, status, alpha_id, "
        "sharpe, fitness, turnover, returns, drawdown, margin, "
        "checks_passed, checks_pending, checks_total, submittable, "
        "run_name, updated_at "
        "FROM backtest_results"
    )
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    logging.info(f"[{label}] 加载记录数: {len(rows)}")
    return {row['md5_hash']: row for row in rows}


def _normalize(val):
    """归一化字段值，便于比较（None/空串/数字精度）"""
    if val is None or val == '':
        return None
    if isinstance(val, float):
        return round(val, 6)
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d %H:%M:%S')
    return val


def _diff_fields(local_row, remote_row):
    """逐字段对比，返回 [(field, local_value, remote_value), ...]"""
    diffs = []
    for f in COMPARE_FIELDS:
        l = _normalize(local_row.get(f))
        r = _normalize(remote_row.get(f))
        if l != r:
            diffs.append((f, l, r))
    return diffs


def compare(local_map, remote_map):
    """三向分类：local_only / remote_only / both_diff"""
    local_keys = set(local_map.keys())
    remote_keys = set(remote_map.keys())

    local_only = local_keys - remote_keys
    remote_only = remote_keys - local_keys
    common = local_keys & remote_keys

    both_diff = []
    for md5 in common:
        diffs = _diff_fields(local_map[md5], remote_map[md5])
        if diffs:
            both_diff.append((md5, diffs))

    return {
        'local_only': local_only,
        'remote_only': remote_only,
        'both_diff': both_diff,
        'common_total': len(common),
        'common_same': len(common) - len(both_diff),
    }


def print_summary(result, local_map, remote_map):
    """控制台打印汇总报告"""
    print()
    print("=" * 70)
    print(" backtest_results 表数据比较报告 ".center(70, "="))
    print("=" * 70)
    print(f"  本地总记录数  : {len(local_map)}")
    print(f"  远程总记录数  : {len(remote_map)}")
    print(f"  共同 md5 数   : {result['common_total']}")
    print(f"    └─ 完全一致 : {result['common_same']}")
    print(f"    └─ 内容不同 : {len(result['both_diff'])}")
    print(f"  本地独有     : {len(result['local_only'])}")
    print(f"  远程独有     : {len(result['remote_only'])}")
    print("=" * 70)

    # 抽样展示
    _print_samples("【本地独有】(local_only)", result['local_only'], local_map, limit=10)
    _print_samples("【远程独有】(remote_only)", result['remote_only'], remote_map, limit=10)
    _print_diffs(result['both_diff'], local_map, remote_map, limit=10)


def _print_samples(title, md5_set, row_map, limit=10):
    if not md5_set:
        return
    print(f"\n{title}  共 {len(md5_set)} 条，展示前 {min(limit, len(md5_set))} 条：")
    print("-" * 70)
    for i, md5 in enumerate(list(md5_set)[:limit], 1):
        row = row_map[md5]
        expr = (row.get('expression') or '')[:60]
        print(f"  {i:>2}. md5={md5[:12]}.. status={row.get('status')} "
              f"sharpe={row.get('sharpe')} expr={expr}...")


def _print_diffs(diff_list, local_map, remote_map, limit=10):
    if not diff_list:
        return
    print(f"\n【共同 md5 但内容不同】 共 {len(diff_list)} 条，展示前 {min(limit, len(diff_list))} 条：")
    print("-" * 70)
    for i, (md5, diffs) in enumerate(diff_list[:limit], 1):
        expr = (local_map[md5].get('expression') or '')[:50]
        print(f"  {i:>2}. md5={md5[:12]}..  expr={expr}...")
        for field, lv, rv in diffs:
            print(f"        - {field:<16} 本地={lv}  |  远程={rv}")


def write_csv(result, local_map, remote_map, path):
    """将完整差异写入 CSV，便于后续处理"""
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([
            'diff_type', 'md5_hash', 'field', 'local_value', 'remote_value',
            'expression', 'status_local', 'status_remote', 'sharpe_local', 'sharpe_remote',
        ])

        for md5 in result['local_only']:
            row = local_map[md5]
            writer.writerow([
                'local_only', md5, '', '', '',
                row.get('expression'), row.get('status'), '',
                row.get('sharpe'), '',
            ])
        for md5 in result['remote_only']:
            row = remote_map[md5]
            writer.writerow([
                'remote_only', md5, '', '', '',
                row.get('expression'), '', row.get('status'),
                '', row.get('sharpe'),
            ])
        for md5, diffs in result['both_diff']:
            lrow, rrow = local_map[md5], remote_map[md5]
            for field, lv, rv in diffs:
                writer.writerow([
                    'field_diff', md5, field, lv, rv,
                    lrow.get('expression'), lrow.get('status'), rrow.get('status'),
                    lrow.get('sharpe'), rrow.get('sharpe'),
                ])
    logging.info(f"差异报告已写入: {path}")


def parse_args():
    p = argparse.ArgumentParser(description="本地与远程 backtest_results 表数据比较工具")
    p.add_argument('--remote-host', required=True, help='远程 MySQL 主机 (局域网 IP)')
    p.add_argument('--remote-port', type=int, default=3306, help='远程端口，默认 3306')
    p.add_argument('--remote-user', required=True, help='远程 MySQL 用户名')
    p.add_argument('--remote-password', required=True, help='远程 MySQL 密码')
    p.add_argument('--remote-database', required=True, help='远程库名')
    p.add_argument('--output', default='', help='差异报告 CSV 输出路径（不传则只打印）')
    p.add_argument('--apply', default='', choices=['', 'push', 'pull', 'both'],
                   help='同步模式：push=本地→远程, pull=远程→本地, both=双向, 不传=仅比较')
    p.add_argument('--batch-size', type=int, default=500, help='批量插入每批大小')
    return p.parse_args()


def _full_sync(src_conn, dst_conn, md5_set, src_label, dst_label, batch_size=500):
    """将 src 中 md5_set 内的记录用 INSERT IGNORE 推到 dst（按 md5_hash 去重）"""
    if not md5_set:
        logging.info(f"[{src_label}→{dst_label}] 无需要同步的记录，跳过")
        return 0

    cols_select = ', '.join(SYNC_COLUMNS)
    placeholders = ', '.join(['%s'] * len(SYNC_COLUMNS))
    insert_sql = (
        f"INSERT IGNORE INTO backtest_results ({cols_select}) VALUES ({placeholders})"
    )

    # 分批从源库读 → 写到目标库
    md5_list = list(md5_set)
    total_inserted = 0
    total = len(md5_list)
    logging.info(f"[{src_label}→{dst_label}] 准备同步 {total} 条记录 ...")

    with src_conn.cursor() as src_cur, dst_conn.cursor() as dst_cur:
        for i in range(0, total, batch_size):
            batch = md5_list[i:i + batch_size]
            in_clause = ', '.join(['%s'] * len(batch))
            select_sql = (
                f"SELECT {cols_select} FROM backtest_results WHERE md5_hash IN ({in_clause})"
            )
            src_cur.execute(select_sql, batch)
            rows = src_cur.fetchall()

            params = [tuple(row[c] for c in SYNC_COLUMNS) for row in rows]
            if params:
                dst_cur.executemany(insert_sql, params)
                total_inserted += dst_cur.rowcount
            dst_conn.commit()
            logging.info(f"  已处理 {min(i + batch_size, total)}/{total}，"
                         f"实际新增 {total_inserted} 条")

    logging.info(f"[{src_label}→{dst_label}] 同步完成，共新增 {total_inserted} 条")
    return total_inserted


def main():
    args = parse_args()

    remote_cfg = {
        'host': args.remote_host,
        'port': args.remote_port,
        'user': args.remote_user,
        'password': args.remote_password,
        'database': args.remote_database,
        'charset': 'utf8mb4',
    }

    logging.info("开始比较本地 vs 远程 backtest_results 表 ...")

    local_conn = _connect(LOCAL_CONFIG, 'LOCAL')
    remote_conn = _connect(remote_cfg, 'REMOTE')

    try:
        local_map = _fetch_all_rows(local_conn, 'LOCAL')
        remote_map = _fetch_all_rows(remote_conn, 'REMOTE')

        result = compare(local_map, remote_map)
        print_summary(result, local_map, remote_map)

        if args.output:
            write_csv(result, local_map, remote_map, args.output)

        # ===== 同步执行（按 --apply 模式）=====
        if args.apply in ('push', 'both'):
            print("\n" + "=" * 70)
            print(" 执行同步: LOCAL → REMOTE ".center(70, "="))
            print("=" * 70)
            _full_sync(local_conn, remote_conn,
                       result['local_only'], 'LOCAL', 'REMOTE', args.batch_size)

        if args.apply in ('pull', 'both'):
            print("\n" + "=" * 70)
            print(" 执行同步: REMOTE → LOCAL ".center(70, "="))
            print("=" * 70)
            _full_sync(remote_conn, local_conn,
                       result['remote_only'], 'REMOTE', 'LOCAL', args.batch_size)
    finally:
        local_conn.close()
        remote_conn.close()

    # 退出码：0 = 完全一致或同步完成，1 = 仅比较模式且有差异
    if args.apply:
        sys.exit(0)
    has_diff = (
        bool(result['local_only']) or
        bool(result['remote_only']) or
        bool(result['both_diff'])
    )
    sys.exit(1 if has_diff else 0)


if __name__ == '__main__':
    main()
